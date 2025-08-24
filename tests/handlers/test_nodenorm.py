"""
Tests for mocking the nodenorm handling
"""

import json

import tornado
from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.httpclient import AsyncHTTPClient

from web.handlers import EXTRA_HANDLERS
from web.application import PendingAPI
from web.settings.configuration import load_configuration


class TestNodeNormalizationHandler(AsyncHTTPTestCase):

    def get_app(self) -> tornado.web.Application:
        configuration = load_configuration("config_web/nodenorm.py")
        configuration.ES_INDICES = {configuration.ES_DOC_TYPE: "nodenorm_20250507_4ibdxry7"}
        configuration.ES_HOST = "http://su10:9200"
        app_handlers = EXTRA_HANDLERS
        app_settings = {"static_path": "static"}
        application = PendingAPI.get_app(configuration, app_settings, app_handlers)
        return application

    @gen_test(timeout=0.50)
    def test_node_normalization(self):
        """
        Tests the plugin metadata responses

        Accumulates all of the API's found through the /api/list endpoint
        and then test each one to ensure that the metadata structure is consistent
        across all endpoints

        Also ensures that we correctly handle SMARTAPI identifier integration
        for plugins that have and don't have it when reporting the metadata
        """
        normalized_nodes_endpoint = r"/nodenorm/get_normalized_nodes"
        url = self.get_url(normalized_nodes_endpoint)
        body = json.dumps({"curie": ["MESH:D014867", "NCIT:C34373"]})
        headers = {"Content-Type": "application/json"}

        http_client = AsyncHTTPClient()
        response = yield http_client.fetch(url, self.stop, method="POST", headers=headers, body=body, request_timeout=0)
        body = json.loads(response.body.decode("utf-8"))

        expected_body = {
            "MESH:D014867": {
                "equivalent_identifiers": [
                    {
                        "identifier": "CHEBI:15377",
                        "label": "water",
                    },
                    {
                        "identifier": "UNII:059QF0KO0R",
                        "label": "WATER",
                    },
                    {
                        "identifier": "PUBCHEM.COMPOUND:962",
                        "label": "Water",
                    },
                    {
                        "identifier": "CHEMBL.COMPOUND:CHEMBL1098659",
                        "label": "WATER",
                    },
                    {
                        "identifier": "DRUGBANK:DB09145",
                        "label": "Water",
                    },
                    {
                        "identifier": "MESH:D014867",
                        "label": "Water",
                    },
                    {
                        "identifier": "CAS:231-791-2",
                    },
                    {
                        "identifier": "CAS:7732-18-5",
                    },
                    {
                        "identifier": "HMDB:HMDB0002111",
                        "label": "Water",
                    },
                    {
                        "identifier": "KEGG.COMPOUND:C00001",
                        "label": "H2O",
                    },
                    {
                        "identifier": "INCHIKEY:XLYOFNOQVPJJNP-UHFFFAOYSA-N",
                    },
                    {
                        "identifier": "UMLS:C0043047",
                        "label": "water",
                    },
                    {
                        "identifier": "RXCUI:11295",
                    },
                ],
                "id": {
                    "identifier": "CHEBI:15377",
                    "label": "Water",
                },
                "information_content": 47.7,
                "type": [
                    "biolink:SmallMolecule",
                    "biolink:MolecularEntity",
                    "biolink:ChemicalEntity",
                    "biolink:PhysicalEssence",
                    "biolink:ChemicalOrDrugOrTreatment",
                    "biolink:ChemicalEntityOrGeneOrGeneProduct",
                    "biolink:ChemicalEntityOrProteinOrPolypeptide",
                    "biolink:NamedThing",
                    "biolink:PhysicalEssenceOrOccurrent",
                ],
            },
            "NCIT:C34373": {
                "equivalent_identifiers": [
                    {
                        "identifier": "MONDO:0004976",
                        "label": "amyotrophic lateral sclerosis",
                    },
                    {
                        "identifier": "DOID:332",
                        "label": "amyotrophic lateral sclerosis",
                    },
                    {
                        "identifier": "orphanet:803",
                    },
                    {
                        "identifier": "UMLS:C0002736",
                        "label": "Amyotrophic Lateral Sclerosis",
                    },
                    {
                        "identifier": "MESH:D000690",
                        "label": "Amyotrophic Lateral Sclerosis",
                    },
                    {
                        "identifier": "MEDDRA:10002026",
                    },
                    {
                        "identifier": "MEDDRA:10052889",
                    },
                    {
                        "identifier": "NCIT:C34373",
                        "label": "Amyotrophic Lateral Sclerosis",
                    },
                    {
                        "identifier": "SNOMEDCT:86044005",
                    },
                    {
                        "identifier": "medgen:274",
                    },
                    {
                        "identifier": "icd11.foundation:1982355687",
                    },
                    {
                        "identifier": "ICD10:G12.21",
                    },
                    {
                        "identifier": "ICD9:335.20",
                    },
                    {
                        "identifier": "KEGG.DISEASE:05014",
                    },
                    {
                        "identifier": "HP:0007354",
                        "label": "Amyotrophic lateral sclerosis",
                    },
                ],
                "id": {
                    "identifier": "MONDO:0004976",
                    "label": "amyotrophic lateral sclerosis",
                },
                "information_content": 74.9,
                "type": [
                    "biolink:Disease",
                    "biolink:DiseaseOrPhenotypicFeature",
                    "biolink:BiologicalEntity",
                    "biolink:ThingWithTaxon",
                    "biolink:NamedThing",
                ],
            },
        }
        assert expected_body == body
