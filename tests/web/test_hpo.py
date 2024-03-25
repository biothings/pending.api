import logging

import pytest
import requests

from biothings.tests.web import BiothingsDataTest
from biothings.web.query.builder import ESQueryBuilder, QStringParser, Query

from config_web.hpo import ANNOTATION_ID_REGEX_LIST


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class TestHPOCurieQuery:
    @classmethod
    def setup_class(cls):
        cls.parser = QStringParser(
            default_scopes=("_id",),
            patterns=ANNOTATION_ID_REGEX_LIST,
            gpnames=("term", "scope"),
        )

    @pytest.mark.parametrize(
        "query, expected_result",
        [
            ("HP:0006990", Query(term="HP:0006990", scopes=["_id"])),
            ("hp:HP:0006990", Query(term="HP:0006990", scopes=["hp"])),
            ("HP:HP:0006990", Query(term="HP:0006990", scopes=["hp"])),
            ("Hp:HP:0006990", Query(term="HP:0006990", scopes=["hp"])),
        ],
    )
    def test_curie_id_queries(self, query: str, expected_result: Query):
        """
        Tests various CURIE ID based queries targetting the types of queries we'd expect
        to see with the mygene instance

        curie_id_testing_collection = ["HP:0006990", "hp:HP:0006990", "HP:HP:0006990", "Hp:HP:0006990"]
        """
        parser_result = self.parser.parse(query)
        assert isinstance(parser_result, Query)
        assert parser_result == expected_result
        assert parser_result.term == expected_result.term
        assert parser_result.scopes == expected_result.scopes
