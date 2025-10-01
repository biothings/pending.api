"""
Tests for mocking the set identifier generation handling
"""

import json

import pytest
import tornado
from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.httpclient import AsyncHTTPClient
from tornado.ioloop import IOLoop

from web.handlers import EXTRA_HANDLERS
from web.application import PendingAPI
from web.settings.configuration import load_configuration


class TestSetIdentifierHandlerGet(AsyncHTTPTestCase):

    def get_app(self) -> tornado.web.Application:
        configuration = load_configuration("config_web/nodenorm.py")
        configuration.ES_INDICES = {configuration.ES_DOC_TYPE: "nodenorm_20250929_wop2zrjn"}
        configuration.ES_HOST = "http://su10:9200"
        app_handlers = EXTRA_HANDLERS
        app_settings = {"static_path": "static"}
        application = PendingAPI.get_app(configuration, app_settings, app_handlers)
        return application

    @gen_test(timeout=1.50)
    def test_get_endpoint(self):
        """
        Tests the get_setid endpoint via GET request

        Example query used:
        CURIES:
        {
            MESH:D014867,
            NCIT:C34373,
            UNII:63M8RYN44N,
            RUBBISH:1234
        }
        CONFLATIONS
        {
            GeneProtein,
            DrugChemical
        }
        """
        normalized_nodes_endpoint = r"/nodenorm/get_setid"
        url = self.get_url(normalized_nodes_endpoint)
        full_url = f"{url}?curie=MESH%3AD014867&curie=NCIT%3AC34373&curie=UNII%3A63M8RYN44N&curie=RUBBISH%3A1234&conflation=GeneProtein&conflation=DrugChemical"

        http_client = AsyncHTTPClient()
        response = yield http_client.fetch(full_url, self.stop, method="GET", request_timeout=0)

        expected_body = {
            "curies": ["MESH:D014867", "NCIT:C34373", "UNII:63M8RYN44N", "RUBBISH:1234"],
            "conflations": ["GeneProtein", "DrugChemical"],
            "error": None,
            "normalized_curies": ["CHEBI:15377", "MONDO:0004976", "RUBBISH:1234"],
            "normalized_string": "CHEBI:15377||MONDO:0004976||RUBBISH:1234",
            "setid": "uuid:771d3c09-9a8c-5c46-8b85-97f481a90d40",
        }
        assert json.loads(response.body.decode("utf-8")) == expected_body


class TestSetIdentifierHandlerPost(AsyncHTTPTestCase):

    def get_app(self) -> tornado.web.Application:
        configuration = load_configuration("config_web/nodenorm.py")
        configuration.ES_INDICES = {configuration.ES_DOC_TYPE: "nodenorm_20250929_wop2zrjn"}
        configuration.ES_HOST = "http://su10:9200"
        app_handlers = EXTRA_HANDLERS
        app_settings = {"static_path": "static"}
        application = PendingAPI.get_app(configuration, app_settings, app_handlers)
        return application

    @gen_test(timeout=1.50)
    def test_post_endpoint(self):
        """
        Tests the get_setid endpoint via POST request
        """
        normalized_nodes_endpoint = r"/nodenorm/get_setid"
        url = self.get_url(normalized_nodes_endpoint)

        body = json.dumps(
            {
                "curies": ["MESH:D014867", "NCIT:C34373", "UNII:63M8RYN44N", "RUBBISH:1234"],
                "conflations": ["GeneProtein", "DrugChemical"],
            }
        )
        headers = {"Content-Type": "application/json"}

        http_client = AsyncHTTPClient()
        response = yield http_client.fetch(url, self.stop, method="POST", headers=headers, body=body, request_timeout=0)
        body = json.loads(response.body.decode("utf-8"))

        expected_body = {
            "curies": ["MESH:D014867", "NCIT:C34373", "UNII:63M8RYN44N", "RUBBISH:1234"],
            "conflations": ["GeneProtein", "DrugChemical"],
            "error": None,
            "normalized_curies": ["CHEBI:15377", "MONDO:0004976", "RUBBISH:1234"],
            "normalized_string": "CHEBI:15377||MONDO:0004976||RUBBISH:1234",
            "setid": "uuid:771d3c09-9a8c-5c46-8b85-97f481a90d40",
        }
        assert json.loads(response.body.decode("utf-8")) == expected_body
