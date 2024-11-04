"""
Tests for mocking the ApiList handling
"""
import json

import tornado
from tornado.testing import AsyncHTTPTestCase

from web.handlers import EXTRA_HANDLERS
from web.application import PendingAPI
from web.settings.configuration import load_configuration


class TestApiListHandler(AsyncHTTPTestCase):

    def get_app(self) -> tornado.web.Application:
        configuration = load_configuration("config_web")
        app_handlers = EXTRA_HANDLERS
        app_settings = {"static_path": "static"}
        application = PendingAPI.get_app(configuration, app_settings, app_handlers)
        return application

    def test_get_method(self):
        """
        Test the GET HTTP method handler for the front page

        Example Response Header Content
        [
            ('Connection', 'close')
            ('Content-Length', '39180'),
            ('Content-Type', 'text/html; charset=UTF-8'),
            ('Date', 'Tue, 12 Mar 2024 18:10:46 GMT'),
            ('Etag', '"59777fcfe54fb940e50d1c534e02ed8a8c59d52e"'),
            ('Server', 'TornadoServer/6.4'),
        ]
        Example Request Header Content
        [
            ('Accept-Encoding', 'gzip')
            ('Connection', 'close'),
            ('Host', '127.0.0.1:41599'),
            ('User-Agent', 'Tornado/6.4'),
        ]
        """
        api_list_endpoint = r"/api/list"
        http_method = "GET"
        expected_endpoints = [
            "/DISEASES/.*",
            "/agr/.*",
            "/annotator_extra/.*",
            "/biggim/.*",
            "/biggim_drugresponse_kp/.*",
            "/bindingdb/.*",
            "/biomuta/.*",
            "/bioplanet_pathway_disease/.*",
            "/bioplanet_pathway_gene/.*",
            "/ccle/.*",
            "/cell_ontology/.*",
            "/chebi/.*",
            "/clinicaltrials/.*",
            "/ddinter/.*",
            "/denovodb/.*",
            "/dgidb/.*",
            "/disbiome/.*",
            "/doid/.*",
            "/ebigene2phenotype/.*",
            "/fda_drugs/.*",
            "/foodb/.*",
            "/fooddata/.*",
            "/geneset/.*",
            "/gmmad2/.*",
            "/go/.*",
            "/go_bp/.*",
            "/go_cc/.*",
            "/go_mf/.*",
            "/gtrx/.*",
            "/gwascatalog/.*",
            "/hmdb/.*",
            "/hmdbv4/.*",
            "/hpo/.*",
            "/idisk/.*",
            "/innatedb/.*",
            "/kaviar/.*",
            "/mgigene2phenotype/.*",
            "/mondo/.*",
            "/mrcoc/.*",
            "/multiomics_clinicaltrials_kp/.*",
            "/multiomics_drug_approvals_kp/.*",
            "/multiomics_ehr_risk_kp/.*",
            "/multiomics_wellness_kp/.*",
            "/ncit/.*",
            "/node-expansion/.*",
            "/pfocr/.*",
            "/phewas/.*",
            "/pseudocap_go/.*",
            "/pubtator3/.*",
            "/rare_source/.*",
            "/repodb/.*",
            "/rhea/.*",
            "/semmeddb/.*",
            "/suppkg/.*",
            "/tcga_mut_freq_kp/.*",
            "/text_mining_targeted_association/.*",
            "/tissues/.*",
            "/ttd/.*",
            "/uberon/.*",
            "/umlschem/.*",
            "/upheno_ontology/.*",
        ]

        response = self.fetch(api_list_endpoint, method=http_method)

        decoded_body = json.loads(response.body.decode("utf-8"))
        self.assertEqual(response.code, 200)
        self.assertEqual(decoded_body, expected_endpoints)
        self.assertEqual(response.reason, "OK")
        self.assertFalse(response._error_is_response_code)

        response_headers = response.headers
        response_content_type = response_headers.get("Content-Type", None)
        response_content_length = response_headers.get("Content-Length", "-10")
        response_header_connection = response_headers.get("Connection", None)

        self.assertTrue(isinstance(response_headers, tornado.httputil.HTTPHeaders))
        self.assertEqual(response_content_type, "application/json; charset=UTF-8")
        self.assertTrue(int(response_content_length) > 0)
        self.assertEqual(response_header_connection, "close")

        get_request = response.request
        self.assertEqual(get_request.method, http_method)
        self.assertEqual(get_request.body, None)

        get_request_headers = get_request.headers
        request_connection = get_request_headers.get("Connection", None)
        response_user_agent = get_request_headers.get("User-Agent", None)
        request_user_agent = get_request_headers.get("User-Agent", None)

        self.assertEqual(request_connection, "close")
        self.assertTrue(response_user_agent)
        self.assertTrue(request_user_agent)
        self.assertEqual(response_user_agent, request_user_agent)

        response_time = response.start_time
        request_time = get_request.start_time
        self.assertTrue(response.request_time >= (response_time - request_time))
