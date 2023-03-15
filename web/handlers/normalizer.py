"""
Translator Node Normalizer Service Handler
"""
import logging

import biothings_client
from biothings.utils.common import get_dotfield_value
from biothings.web.handlers import BaseAPIHandler
from tornado.web import HTTPError

logger = logging.getLogger(__name__)

BIOLINK_PREFIX_to_BioThings = {
    "NCBIGene": {"type": "gene", "field": "entrezgene"},
    "ENSEMBL": {"type": "gene", "field": "ensembl.gene"},
    "UniProtKB": {"type": "gene", "field": "uniprot.Swiss-Prot"},
    "CHEMBL.COMPOUND": {
        "type": "chem",
        "field": "chembl.molecule_chembl_id",
        "converter": lambda x: x.replace("CHEMBL.COMPOUND:", "CHEMBL"),
    },
    "PUBCHEM.COMPOUND": {"type": "chem", "field": "pubchem.cid"},
    "CHEBI": {"type": "chem", "field": "chebi.id"},
    "MONDO": {"type": "disease", "field": "mondo.mondo"},
    "DOID": {"type": "disease", "field": "doid.doid"},
}


class TRAPIInputError(ValueError):
    pass


class InvalidCurieError(ValueError):
    pass


def list2dict(li, key):
    out = {}
    for d in li:
        k = d[key]
        if k not in out:
            out[k] = [d]
        else:
            out[k].append(d)
    return out


class NormalizerHandler(BaseAPIHandler):
    name = "normalizer"
    normalizer_clients = {
        "gene": {
            "client": biothings_client.get_client("gene"),
            "fields": ["name", "symbol", "summary"],
            "scopes": ["entrezgene", "ensemblgene", "uniprot", "panther.uniprot_kb"],
        },
        "chem": {
            "client": biothings_client.get_client("chem"),
            "fields": [
                "drugbank.id",
                "chebi.id",
                "chebi.iupac",
                "chembl.first_approval",
                "chembl.first_in_class",
                "chembl.unii",
                "pubchem.molecular_weight",
                "pubchem.molecular_formula",
            ],
            "scopes": ["_id", "chebi.id", "chembl.molecule_chembl_id", "pubchem.cid", "drugbank.id", "unii.unii"],
        },
        "disease": {
            "client": biothings_client.get_client("disease"),
            "fields": ["mondo.mondo", "mondo.label", "mondo.definition", "umls.umls"],
            "scopes": ["_id", "mondo.mondo", "doid.doid", "umls.umls"],
        },
    }

    def parse_curie(self, curie, return_type=True, return_id=True):
        """return a both type and if (as a tuple) or either based on the input curie"""
        if ":" not in curie:
            raise InvalidCurieError(f"Invalid input curie id: {curie}")
        _prefix, _id = curie.split(":", 1)
        _type = BIOLINK_PREFIX_to_BioThings.get(_prefix, {}).get("type", None)
        if return_id:
            if not _type or BIOLINK_PREFIX_to_BioThings[_prefix].get("keep_prefix", False):
                _id = curie
            cvtr = BIOLINK_PREFIX_to_BioThings.get(_prefix, {}).get("converter", None)
            if cvtr:
                _id = cvtr(_id)
        if return_type and return_id:
            return _type, _id
        elif return_type:
            return _type
        elif return_id:
            return _id

    def _get_annotations(self, trapi_input):
        try:
            node_d = get_dotfield_value("message.knowledge_graph.nodes", trapi_input)
            assert isinstance(node_d, dict)
        except (KeyError, ValueError, AssertionError):
            raise TRAPIInputError("Invalid input format")

        node_list_by_type = {}
        for node_id in node_d:
            node_type = self.parse_curie(node_id, return_type=True, return_id=False)
            if not node_type:
                logger.info("%s - %s", node_type, node_id)
            if node_type:
                if node_type not in node_list_by_type:
                    node_list_by_type[node_type] = [node_id]
                else:
                    node_list_by_type[node_type].append(node_id)
        for node_type in node_list_by_type:
            if node_type not in self.normalizer_clients or not node_list_by_type[node_type]:
                # skip for now
                continue
            client = self.normalizer_clients[node_type]["client"]
            fields = self.normalizer_clients[node_type]["fields"]
            scopes = self.normalizer_clients[node_type]["scopes"]
            # this is the list of original node ids like NCBIGene:1017, should be a unique list
            node_list = node_list_by_type[node_type]
            # this is the list of query ids like 1017
            query_list = [
                self.parse_curie(_id, return_type=False, return_id=True) for _id in node_list_by_type[node_type]
            ]
            # query_id to original id mapping
            node_id_d = dict(zip(query_list, node_list))
            logger.info("Querying annotations for %s %ss...", len(query_list), node_type)
            res = client.querymany(query_list, scopes=scopes, fields=fields)
            logger.info("Done. %s annotation objects returned.", len(res))
            res_by_id = list2dict(res, "query")
            for node_id in res_by_id:
                orig_node_id = node_id_d[node_id]
                res = res_by_id[node_id]
                if isinstance(res, list):
                    # TODO: handle multiple results here
                    res = res[0]
                res.pop("query", None)
                res.pop("_score", None)
                res = {
                    "attribute_type_id": "biothings_annnotations",
                    "value": res,
                }
                # node_d[orig_node_id]["attributes"].append(res)
                node_d[orig_node_id]["attributes"] = [res]

        return node_d

    async def post(self, *args, **kwargs):
        try:
            annotated_node_d = self._get_annotations(self.args_json)
        except TRAPIInputError as e:
            raise HTTPError(400, str(e))
        self.finish(annotated_node_d)
