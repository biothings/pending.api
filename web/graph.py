import copy
import json
from collections import defaultdict
from collections import UserList

class GraphObject:
    """
        Representing a graph object stored in db.
        Does not perform in-depth validation,
        only use it with existing records.
    """

    try:  # the mapping is already expanded to both ways
        with open('predicate_mapping.json') as file:
            PREDICATE_MAPPING = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        PREDICATE_MAPPING = {}

    def __init__(self, subject, object_, associ):

        assert isinstance(subject, dict)
        assert isinstance(object_, dict)
        assert isinstance(associ, dict)

        self.subject = copy.deepcopy(subject)
        self.object = copy.deepcopy(object_)
        self.associ = copy.deepcopy(associ)

    @property
    def predicate(self):
        return self.associ.get('edge_label')

    @predicate.setter
    def predicate(self, val):
        self.associ['edge_label'] = val

    @classmethod
    def from_dict(cls, dic):
        """
        Import a dict representation to a graph object.
        Ignore non-essential fields, like _id, if provided.
        Assume required fields not provided have empty values.
        """
        return cls(
            subject=dic.get("subject", {}),
            object_=dic.get("object", {}),
            associ=dic.get("association", {})
        )

    def reversible(self):
        """
        Check if it's reversible basing on our mapping.
        Typically call this first before calling reverse().
        """
        return self.predicate in self.PREDICATE_MAPPING

    def reverse(self):
        """
        Reverse the subject and object, and their relationship.
        Raise error on non-reversible ones basing on the mapping file.
        """
        if self.reversible():
            self.subject, self.object = self.object, self.subject
            self.predicate = self.PREDICATE_MAPPING[self.predicate]
        else:  # reversed relationship is not defined
            raise TypeError("Not reversible.")

    def to_dict(self):
        return {
            "subject": copy.deepcopy(self.subject),
            "object": copy.deepcopy(self.object),
            "association": copy.deepcopy(self.associ)
        }


class GraphQuery(GraphObject):
    """
        A graph query request submitted by a user.
        Perform additional in-depth data validation.
        Dotdict serializable, no containers under lists.
    """

    def __init__(self, subject=None, object_=None, associ=None):
        # no guarantee which or any field is provided
        subject = subject or {}
        object_ = object_ or {}
        association = associ or {}
        self._validate_subject(subject)
        self._validate_object(object_)
        self._validate_associ(association)
        super().__init__(subject, object_, association)

    def _validate(self, key, val, allow=(int, float, str, dict, list)):

        if not isinstance(val, allow):
            raise TypeError(f"Unsupported type under '{key}'.")
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
        if val.get('edge_label') is not None:
            # predicate, if provided, must be a string or a list of strings.
            self._validate('association.edge_label', val.get('edge_label'), (str, list))

    @classmethod
    def from_dict(cls, dic):
        # support dot dict notation
        if not isinstance(dic, dict):
            raise TypeError("expecting 'dict' type.")
        # expand first level keywords
        _dic = cls._collapse_dotdict(dic, ('subject', 'object', 'association'))
        return super().from_dict(_dic)

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

        No error for key conflicts.
        Replace original value. TODO

        """
        _dic = defaultdict(dict)
        for key in dic:
            entry_processed = False
            for first_level_key in first_level_keys:
                if key.startswith(first_level_key):
                    if key == first_level_key:
                        # TypeError is raised if value not dict
                        _dic[first_level_key].update(dic[key])
                        entry_processed = True
                    elif key.startswith(first_level_key + '.'):
                        if key[len(first_level_key) + 1:]:
                            _key = key[len(first_level_key) + 1:]
                            _dic[first_level_key][_key] = dic[key]
                            entry_processed = True
            if not entry_processed:
                raise ValueError(f"Invalid entry for key '{key}'.")
        return _dic

class GraphQueries(UserList):
    pass