"""
WIP

Biothings Enhanced Graph Query Support
https://github.com/biothings/pending.api/issues/20

"""

import json
import logging
from collections import defaultdict

from biothings.utils.common import dotdict
from biothings.utils.web.es_dsl import AsyncMultiSearch, AsyncSearch
from biothings.web.handlers import ESRequestHandler
from biothings.web.handlers.exceptions import BadRequest
from tornado.web import HTTPError

from biothings.web.settings.default import COMMON_KWARGS

class GraphObjectError(Exception):
    pass


class GraphQueryError(GraphObjectError):
    pass


class GraphObject:

    try:  # the mapping is already expanded to both ways
        with open('predicate_mapping.json') as file:
            PREDICATE_MAPPING = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        PREDICATE_MAPPING = {}

    def __init__(self, subject, object, association):

        self.subject = subject
        self.object = object
        self.associ = association

    @classmethod
    def from_dict(cls, dic):
        return cls(**dic)

    def reverse(self):

        self.subject, self.object = self.object, self.subject
        self.associ["predicate"] = self.PREDICATE_MAPPING[self.associ["predicate"]]

    def to_dict(self):
        return {
            "subject": self.subject,
            "object": self.object,
            "association": self.associ
        }


class GraphQuery(GraphObject):
    """

    dotdict serializable, which means no containers under lists.
    """

    def __init__(self, subject=None, object=None, association=None):
        # no guarantee which or any field is provided
        subject = subject or {}
        object = object or {}
        association = association or {}
        self._validate_subject(subject)
        self._validate_object(object)
        self._validate_associ(association)
        super().__init__(subject, object, association)

    def _validate(self, key, val, allow=(int, float, str, dict, list)):

        if not isinstance(val, allow):
            raise GraphQueryError(f"Unsupported type for key '{key}'.")
        if isinstance(val, dict):
            for _key in val:
                self._validate('.'.join((key, _key)), val[_key], allow)
        if isinstance(val, list):
            for item in val:  # no containers under lists
                self._validate(key, item, (int, float, str))

    def _validate_subject(self, val):
        self._validate('subject', val)

    def _validate_object(self, val):
        self._validate('object', val)

    def _validate_associ(self, val):
        self._validate('association', val)
        if val.get('predicate') is not None:
            # predicate, if provided, must be a string or a list of strings.
            self._validate('association.predicate', val.get('predicate'), (str, list))

    @property
    def predicate(self):
        return self.associ.get('predicate')

    @classmethod
    def from_dict(cls, dic):
        # support dot dict notation
        if not isinstance(dic, dict):
            raise TypeError("expecting 'dict' type.")
        # expand first level keywords
        _dic = cls._collapse_dotdict(dic, ('subject', 'object', 'association'))
        return cls(**_dic)

    @staticmethod
    def _collapse_dotdict(dic, first_level_keys):
        """
        Collapse dic by one level allowing only specified keys.
        One level is enough for elasticsearch query purpose.

        Example:

        Turning
        {
            "subject.id.a": "x",
            "subject.id.b.c": "x",
            "object.id": "x",
            "object.id.d": "x",
            "association": {}
        }
        into
        {
            "subject": {'id.a': 'x', 'id.b.c': 'x'},
            "object": {'id': 'x', 'id.d': 'x'},
            "association": {}
        }

        Note this ignores if the dotdict can actually
        be turned into a valid dictionary recursively.

        """
        _dic = defaultdict(dict)
        for key in dic:
            entry_valid = False
            for first_level_key in first_level_keys:
                if key.startswith(first_level_key):
                    if key == first_level_key:
                        _dic[first_level_key].update(dic[key])
                        entry_valid = True
                    elif key.startswith(first_level_key + '.'):
                        if key[len(first_level_key) + 1:]:
                            _dic[first_level_key][key[len(first_level_key) + 1:]] = dic[key]
                            entry_valid = True
            if not entry_valid:
                raise GraphQueryError(f"Invalid key for graph query: '{key}'.")
        return _dic

    def can_reverse(self):
        return self.predicate in self.PREDICATE_MAPPING


class GraphQueryHandler(ESRequestHandler):
    '''
    https://github.com/biothings/pending.api/issues/20
    '''
    name = 'graph'
    # kwargs = {'*': COMMON_KWARGS.copy() }
    # kwargs['*']['from'] = {'type': int, 'max': 10000, 'group': 'esqb', 'alias': 'skip'}

    # currently only supports json queries

    async def execute_pipeline(self, *args, **kwargs):

        try:

            graph_query = GraphQuery.from_dict(self.args_json)
            es_query = self._to_es_query(graph_query)
            
            if graph_query.can_reverse():
                graph_query.reverse()
                es_query_rev = self._to_es_query(graph_query)
                es_query = es_query | es_query_rev

            # it's sent in one query so that parameters like size is still meaningful
            _query = AsyncSearch().query(es_query)
            _res = await self.pipeline.execute(_query, dotdict())
            res = self.pipeline.transform(_res, dotdict())

            # TODO additional transformation, like double reversal in result.

        except GraphObjectError as exc:
            raise BadRequest(reason=str(exc))

        except Exception as exc:
            raise HTTPError(str(exc))

        self.finish(res)

    def _to_es_query(self, graph_query):
        """
        Takes a GraphQuery object and return an ES query.
        """
        assert isinstance(graph_query, GraphQuery)
        q = graph_query.to_dict()
        self.pipeline.result_transform.option_dotfield(q, dotdict())

        _q = []
        _scopes = []

        for k, v in q.items():
            if isinstance(v, list):
                for _v in v:
                    _q.append(_v)
                    _scopes.append(k)
            else:
                _q.append(v)
                _scopes.append(k)

        return self.pipeline.query_builder.default_match_query(_q, _scopes, dotdict()).query._proxied


def test1():
    q1 = GraphQuery.from_dict({
        "subject": {
            "id": "NCBIGene:1017",
            "type": "Gene",
            "taxid": "9606"
        },
        "object": {
            "id": "MONDO:000123",
            "type": "Disease"
        },
        "association": {
            "predicate": "negatively_regulated_by",
            "publications": ["PMID:123", "PMID:124"]
        }
    })
    q2 = GraphQuery.from_dict({
        "subject.id": "NCBIGene:1017",
        "subject.type": "Gene",
        "subject.taxid": "9606",
        "object.id": "MONDO:000123",
        "object.type": "Disease",
        "association.predicate": "negatively_regulated_by",
        "association.publications": ["PMID:123", "PMID:124"]
    })
    assert str(q1.to_dict()) == str(q2.to_dict())

def test2():

    q = GraphQuery.from_dict({
        "subject.id.a": "x",
        "subject.id.b.c": "x",
        "object.id": "x",
        "object.id.d": "x",
        "association": {}
    }).to_dict()
    assert 'subject' in q
    assert 'object' in q
    assert 'association' in q


if __name__ == '__main__':
    test1()
    test2()
