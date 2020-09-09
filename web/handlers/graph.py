import json

from biothings.web.handlers import ESRequestHandler
from biothings.utils.common import dotdict
from biothings.utils.web.es_dsl import AsyncMultiSearch, AsyncSearch
import logging


class GraphQueryHandler(ESRequestHandler):
    '''
    https://github.com/biothings/pending.api/issues/20
    '''
    name = 'graph'
    # kwargs defined in biothing.web.settings.default
    # kwarg_groups = ('control', 'esqb', 'es', 'transform')
    # kwarg_methods = ('get', 'post')
    # kwargs = {
    #     'POST': {
    #         'schema': {'type': str, 'default': 'ctsa::bts:CTSADataset'},
    #         'private': {'type': bool, 'default': False},
    #     },
    #     'GET': {
    #         'user': {'type': str},
    #         'private': {'type': bool},
    #     }
    # }

    # currently only supports json queries

    def _get_mapping(self):

        if hasattr(self, '_predicate_mapping'):
            return self._predicate_mapping

        try:
            with open('predicate_mapping.json') as file:
                mapping = json.load(file)
            self._predicate_mapping = mapping
        except (FileNotFoundError, json.JSONDecodeError):
            self._predicate_mapping = {}

        return self._predicate_mapping

    async def execute_pipeline(self, *args, **kwargs):

        q = dict(self.args_json)
        q_reversed = dict(self.args_json)

        try:
            predicate = q['association']['predicate']
            q_reversed['association']['predicate'] = self._get_mapping()[predicate]
        except KeyError:
            pass

        subject = q_reversed.pop('subject', None)
        object = q_reversed.pop('object', None)
        if subject:
            q_reversed['object'] = subject
        if object:
            q_reversed['subject'] = object
            
        self.pipeline.result_transform.option_dotfield(q, dotdict())
        self.pipeline.result_transform.option_dotfield(q_reversed, dotdict())

        search_1 = self._query_graph(q)
        search_2 = self._query_graph(q_reversed)

        self._query = AsyncSearch().query(search_1.query._proxied | search_2.query._proxied)
        self._res = await self.pipeline.execute(self._query, dotdict())
        res = self.pipeline.transform(self._res, dotdict())

        self.finish(res)

    def _query_graph(self, q):

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

        return self.pipeline.query_builder.default_match_query(_q, _scopes, dotdict())
