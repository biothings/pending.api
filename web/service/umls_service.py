import abc
import json
from typing import List

from .ngd_service import TermExpansionService


class UMLSResourceClient(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def open_resource(self):
        raise NotImplementedError

    @abc.abstractmethod
    def close_resource(self):
        raise NotImplementedError

    @abc.abstractmethod
    def query(self, keyword: str):
        raise NotImplementedError


class UMLSJsonFileClient(UMLSResourceClient):
    def __init__(self, filepath):
        self.filepath = filepath
        self.handler = None
        self.data = None

    def open_resource(self):
        if self.handler is None:
            self.handler = open(self.filepath, "r")

        if self.data is None:
            self.data = json.load(self.handler)

    def close_resource(self):
        if self.handler is not None:
            self.handler.close()

        if self.data is not None:
            self.data = None

    def query(self, keyword: str):
        return self.data.get(keyword, None)

    # No need to implement a context manager
    # The handler would be open like a daemon
    # if RAM usage is high, we can consider sqlite, redis, or mongodb


class NarrowerRelationshipService(TermExpansionService):
    """
    This service class is tailored to read the "umls-parsed.json" from "node-expansion" project.
    (See https://github.com/biothings/node-expansion/blob/main/data/umls-parsed.json)

    Currently this "umls-parsed.json" has a fixed structure that:
    (1) each key is a prefixed UMLS term, like "UMLS:C0000052"
    (2) each value is a list of prefixed UMLS terms, like "['UMLS:C5150408', 'UMLS:C5150409']"

    If the structure of this file changed, we must change this service class accordingly
    """

    term_prefix = "UMLS:"

    def __init__(self, umls_resource_client: UMLSResourceClient, add_input_prefix: bool, remove_output_prefix: bool):
        self.umls_resource_client = umls_resource_client

        self.add_input_prefix = add_input_prefix  # if true, add prefix to the term before querying
        self.remove_output_prefix = remove_output_prefix  # if true, remove the prefix for each output

    def query_narrower_terms(self, term: str) -> List[str]:
        return self.umls_resource_client.query(term)

    def add_prefix(self, term: str) -> str:
        return self.term_prefix + term

    def remove_prefix(self, term: str) -> str:
        return term[len(self.term_prefix) :]

    def expand(self, term: str) -> List[str]:
        if self.add_input_prefix:
            term = self.add_prefix(term)

        narrower_terms = self.query_narrower_terms(term)

        if narrower_terms is None:
            return []

        if self.remove_output_prefix:
            narrower_terms = [self.remove_prefix(t) for t in narrower_terms]

        return narrower_terms
