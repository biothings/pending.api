"""
Translator Node Annotator Service Handler
"""

import inspect
import logging
import os.path
import shelve

import biothings_client
from biothings.utils.common import get_dotfield_value
from biothings.web.handlers import BaseAPIHandler
from tornado.web import HTTPError

logger = logging.getLogger(__name__)

BIOLINK_PREFIX_to_BioThings = {
    "NCBIGene": {"type": "gene", "field": "entrezgene"},
    # "HGNC": {"type": "gene", "field": "HGNC"},
    "ENSEMBL": {"type": "gene", "field": "ensembl.gene"},
    "UniProtKB": {"type": "gene", "field": "uniprot.Swiss-Prot"},
    "INCHIKEY": {"type": "chem"},
    "CHEMBL.COMPOUND": {
        "type": "chem",
        "field": "chembl.molecule_chembl_id",
        # "converter": lambda x: x.replace("CHEMBL.COMPOUND:", "CHEMBL"),
    },
    "PUBCHEM.COMPOUND": {"type": "chem", "field": "pubchem.cid"},
    "CHEBI": {"type": "chem", "field": "chebi.id", "keep_prefix": True},
    "UNII": {"type": "chem", "field": "unii.unii"},
    "DRUGBANK": {"type": "chem", "field": "drugbank.id"},
    "MONDO": {"type": "disease", "field": "mondo.mondo", "keep_prefix": True},
    "DOID": {"type": "disease", "field": "disease_ontology.doid", "keep_prefix": True},
    "HP": {"type": "phenotype", "field": "hp", "keep_prefix": True},
}

# ANNOTAION_FIELD_TRANSFORMATION = {
#     "chembl.drug_indications.mesh_id": lambda x: append_prefix(x, "MESH"),
# }


def save_atc_cache():
    """save WHO atc cache to a file, which will be used in ResponseTransformer._transform_atc_classifications method"""
    import pandas as pd

    url = "https://raw.githubusercontent.com/fabkury/atcd/master/WHO%20ATC-DDD%202021-12-03.csv"
    db_file = "atc_cache.db"

    data = pd.read_csv(url, index_col="atc_code", usecols=[0, 1])
    with shelve.open(db_file) as db:
        for atc_code in data.index:
            db[atc_code] = data.loc[atc_code, "atc_name"]


class ResponseTransformer:
    def __init__(self, res_by_id, node_type):
        self.res_by_id = res_by_id
        self.node_type = node_type

        self.data_cache = {}  # used to cached required mapping data used for individual transformation
        # typically those data coming from other biothings APIs, we will do a batch
        # query to get them all, and cache them here for later use, to avoid slow
        # one by one queries.
        self.atc_cache = {}  # cache for WHO ATC codes
        if os.path.exists("atc_cache.db"):
            self.atc_cache = shelve.open("atc_cache.db", "r")

    def _transform_chembl_drug_indications(self, doc):
        if self.node_type != "chem":
            return doc

        def _append_mesh_prefix(chembl):
            xli = chembl.get("drug_indications", [])
            for _doc in xli:
                if "mesh_id" in _doc:
                    # Add MESH prefix to chembl.drug_indications.mesh_id field
                    _doc["mesh_id"] = append_prefix(_doc["mesh_id"], "MESH")

        chembl = doc.get("chembl", {})
        if chembl:
            if isinstance(chembl, list):
                # in case returned chembl is a list, rare but still possible
                for c in chembl:
                    _append_mesh_prefix(c)
            else:
                _append_mesh_prefix(chembl)

        return doc

    def _transform_atc_classifications(self, doc):
        """add atc_classifications field to chem object based on chembl.atc_classifications and pharmgkb.xrefs.atc fields"""
        if not self.atc_cache:
            return doc

        if self.node_type != "chem":
            return doc

        def _get_atc_from_chembl(chembl):
            atc_from_chembl = chembl.get("atc_classifications", [])
            if isinstance(atc_from_chembl, str):
                atc_from_chembl = [atc_from_chembl]
            return atc_from_chembl

        chembl = doc.get("chembl", {})
        atc_from_chembl = []
        if chembl:
            if isinstance(chembl, list):
                # in case returned chembl is a list, rare but still possible
                for c in chembl:
                    atc_from_chembl.extend(_get_atc_from_chembl(c))
            else:
                atc_from_chembl.extend(_get_atc_from_chembl(chembl))

        def _get_atc_from_pharmgkb(pharmgkb):
            atc_from_pharmgkb = pharmgkb.get("xrefs", {}).get("atc", [])
            if isinstance(atc_from_pharmgkb, str):
                atc_from_pharmgkb = [atc_from_pharmgkb]
            return atc_from_pharmgkb

        pharmgkb = doc.get("pharmgkb", {})
        atc_from_pharmgkb = []
        if pharmgkb:
            if isinstance(pharmgkb, list):
                # in case returned pharmgkb is a list, rare but still possible
                for p in pharmgkb:
                    atc_from_pharmgkb.extend(_get_atc_from_pharmgkb(p))
            else:
                atc_from_pharmgkb.extend(_get_atc_from_pharmgkb(pharmgkb))

        atc = []
        for atc_code in set(atc_from_chembl + atc_from_pharmgkb):
            if len(atc_code) == 7:
                # example: L04AB02
                level_d = {}
                for i, code in enumerate([atc_code[0], atc_code[:3], atc_code[:4], atc_code[:5], atc_code]):
                    level_d[f"level{i+1}"] = {
                        "code": code,
                        "name": self.atc_cache.get(code, ""),
                    }
                atc.append(level_d)
        if atc:
            doc["atc_classifications"] = atc

        return doc

    def caching_ncit_descriptions(self):
        """cache ncit descriptions for all unii.ncit IDs from self.res_by_id
        deprecated along with _transform_add_ncit_description method.
        """
        ncit_id_list = []
        for res in self.res_by_id.values():
            if isinstance(res, list):
                # in case returned res is a list, rare but still possible
                for r in res:
                    unii = r.get("unii", {})
                    if isinstance(unii, list):
                        for u in unii:
                            ncit = u.get("ncit")
                            if ncit:
                                ncit_id_list.append(ncit)
                    else:
                        ncit = unii.get("ncit")
                        if ncit:
                            ncit_id_list.append(ncit)
            else:
                ncit = res.get("unii", {}).get("ncit")
                if ncit:
                    ncit_id_list.append(ncit)
        if ncit_id_list:
            ncit_api = biothings_client.get_client(url="https://biothings.ncats.io/ncit")
            ncit_id_list = [f"NCIT:{ncit}" for ncit in ncit_id_list]
            ncit_res = ncit_api.getnodes(ncit_id_list, fields="def")
            ncit_def_d = {}
            for hit in ncit_res:
                if hit.get("def"):
                    ncit_def = hit["def"]
                    # remove the trailing " []" if present
                    # delete after data is fixed
                    if ncit_def.startswith('"') and ncit_def.endswith('" []'):
                        ncit_def = ncit_def[1:-4]
                    ncit_def_d[hit["_id"]] = ncit_def
            if ncit_def_d:
                self.data_cache["ncit"] = ncit_def_d

    def deprecated_transform_add_ncit_description(self, doc):
        """add ncit_description field to unii object based on unii.ncit field
        deprecated now, as ncit_description is now returned directly from mychem.info
        """
        if self.node_type != "chem":
            return doc

        if "ncit" not in self.data_cache:
            self.caching_ncit_descriptions()

        ncit_def_d = self.data_cache.get("ncit", {})

        def _add_ncit_description(unii):
            ncit = unii.get("ncit")
            ncit = f"NCIT:{ncit}"
            if ncit:
                ncit_def = ncit_def_d.get(ncit)
                if ncit_def:
                    unii["ncit_description"] = ncit_def

        unii = doc.get("unii", {})
        if unii:
            if isinstance(unii, list):
                # in case returned chembl is a list, rare but still possible
                for u in unii:
                    _add_ncit_description(u)
            else:
                _add_ncit_description(unii)
        return doc

    def transform_one_doc(self, doc):
        """transform the response from biothings client"""
        for fn_name, fn in inspect.getmembers(self, predicate=inspect.ismethod):
            if fn_name.startswith("_transform_"):
                if isinstance(doc, list):
                    doc = [fn(r) for r in doc]
                else:
                    doc = fn(doc)
        return doc

    def transform(self):
        for node_id in self.res_by_id:
            res = self.res_by_id[node_id]
            if isinstance(res, list):
                # TODO: handle multiple results here
                res = [self.transform_one_doc(r) for r in res]
            else:
                res = self.transform_one_doc(res)


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


def append_prefix(id, prefix):
    """append prefix to id if not already present to make it a valid Curie ID
    Note that prefix parameter should not include the trailing colon
    """
    return f"{prefix}:{id}" if not id.startswith(prefix) else id


class Annotator:
    annotator_clients = {
        "gene": {
            "client": {"biothing_type": "gene"},  # the kwargs passed to biothings_client.get_client
            "fields": [
                "name",
                "symbol",
                "summary",
                "type_of_gene",
                "MIM",
                "HGNC",
                "MGI",
                "RGD",
                "alias",
                "interpro",
            ],
            "scopes": ["entrezgene", "ensemblgene", "uniprot", "accession", "retired"],
        },
        "chem": {
            "client": {"biothing_type": "chem"},
            "fields": [
                # IDs
                "pubchem.cid",
                "pubchem.inchikey",
                "chembl.molecule_chembl_id",
                "drugbank.id",
                "chebi.id",
                "unii.unii",
                # "chembl.unii",
                # Names
                "chebi.name",
                "chembl.pref_name",
                # Descriptions
                "chebi.definition",
                "unii.ncit",
                "unii.ncit_description",
                # Structure
                "chebi.iupac",
                "chembl.smiles",
                "pubchem.inchi",
                "pubchem.molecular_formula",
                "pubchem.molecular_weight",
                # chemical types
                "chembl.molecule_type",
                "chembl.structure_type",
                # chebi roles etc
                "chebi.relationship",
                # drug info
                "unichem.rxnorm",  # drug name
                "pharmgkb.trade_names",  # drug name
                "pharmgkb.xrefs.atc",  # atc code
                "chembl.drug_indications",
                "aeolus.indications",
                "chembl.drug_mechanisms",
                "chembl.atc_classifications",  # atc code
                "chembl.max_phase",
                "chembl.first_approval",
                "drugcentral.approval",
                "chembl.first_in_class",
                "chembl.inorganic_flag",
                "chembl.prodrug",
                "chembl.therapeutic_flag",
                "cheml.withdrawn_flag",
                "drugcentral.drug_dosage",
                "ndc.routename",
                "ndc.producttypename",
                "ndc.pharm_classes",
                "ndc.proprietaryname",
                "ndc.nonproprietaryname",
            ],
            "scopes": [
                "_id",
                "chebi.id",
                "chembl.molecule_chembl_id",
                "pubchem.cid",
                "drugbank.id",
                "unii.unii",
            ],
        },
        "disease": {
            "client": {"biothing_type": "disease"},
            "fields": [
                # IDs
                "disease_ontology.doid",
                "mondo.mondo",
                "umls.umls",
                # Names
                "disease_ontology.name",
                "mondo.label"
                # Description
                "mondo.definition",
                "disease_ontology.def",
                # Xrefs
                "mondo.xrefs",
                "disease_ontology.xrefs",
                # Synonyms
                "mondo.synonym",
                "disease_ontology.synonyms",
            ],
            "scopes": ["mondo.mondo", "disease_ontology.doid", "umls.umls"],
        },
        "phenotype": {
            "client": {"url": "https://biothings.ncats.io/hpo"},
            "fields": [
                "hp",
                "name",
                "annotations",
                "comment",
                "def",
                "subset",
                "synonym",
                "xrefs",
            ],
            "scopes": ["hp"],
        },
    }

    def get_client(self, node_type: str) -> tuple[biothings_client.BiothingClient, None]:
        """lazy load the biothings client for the given node_type, return the client or None if failed."""
        client_or_kwargs = self.annotator_clients[node_type]["client"]
        if isinstance(client_or_kwargs, biothings_client.BiothingClient):
            client = client_or_kwargs
        elif isinstance(client_or_kwargs, dict):
            try:
                client = biothings_client.get_client(**client_or_kwargs)
            except RuntimeError as e:
                logger.error("%s [%s]", e, client_or_kwargs)
                client = None
            if isinstance(client, biothings_client.BiothingClient):
                # cache the client
                self.annotator_clients[node_type]["client"] = client
        else:
            raise ValueError("Invalid input client_or_kwargs")
        return client

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
                _id = cvtr(curie)
        if return_type and return_id:
            return _type, _id
        elif return_type:
            return _type
        elif return_id:
            return _id

    def query_biothings(self, node_type: str, query_list, fields=None) -> dict:
        """Query biothings client based on node_type for a list of ids"""
        client = self.get_client(node_type)
        if not client:
            logger.warning(
                "Failed to get the biothings client for %s type. This type is skipped.",
                node_type,
            )
            return {}
        fields = fields or self.annotator_clients[node_type]["fields"]
        scopes = self.annotator_clients[node_type]["scopes"]
        logger.info("Querying annotations for %s %ss...", len(query_list), node_type)
        res = client.querymany(query_list, scopes=scopes, fields=fields)
        logger.info("Done. %s annotation objects returned.", len(res))
        res = list2dict(res, "query")
        return res

    def annotate_curie(self, curie, raw=False, fields=None):
        """Annotate a single curie id"""
        node_type, _id = self.parse_curie(curie)
        if not node_type:
            raise InvalidCurieError(f"Unsupported Curie prefix: {curie}")
        res = self.query_biothings(node_type, [_id], fields=fields)
        if not raw:
            res = self.transform(res, node_type)
            # res = [self.transform(r) for r in res[_id]]
        return {curie: res.get(_id, {})}

    def transform(self, res_by_id, node_type):
        """perform any transformation on the annotation object, but in-place also returned object
        res_by_id is the output of query_biothings, node_type is the same passed to query_biothings
        """
        logger.info("Transforming output annotations for %s %ss...", len(res_by_id), node_type)
        transformer = ResponseTransformer(res_by_id, node_type)
        transformer.transform()
        logger.info("Done.")
        ####
        # if isinstance(res, list):
        #     # TODO: handle multiple results here
        #     res = [transformer.transform(r) for r in res]
        # else:
        #     res.pop("query", None)
        #     res.pop("_score", None)
        #     res = transformer.transform(res)
        ####
        return res_by_id

    def annotate_trapi(self, trapi_input, append=False, raw=False, fields=None, limit=None):
        """Annotate a TRAPI input message with node annotator annotations"""
        try:
            node_d = get_dotfield_value("message.knowledge_graph.nodes", trapi_input)
            assert isinstance(node_d, dict)
        except (KeyError, ValueError, AssertionError):
            raise TRAPIInputError("Invalid input format")

        # if limit is set, we truncate the node_d to that size
        if limit:
            _node_d = {}
            i = 0
            for node_id in node_d:
                i += 1
                if i > limit:
                    break
                _node_d[node_id] = node_d[node_id]
            node_d = _node_d
            del i, _node_d

        node_list_by_type = {}
        for node_id in node_d:
            node_type = self.parse_curie(node_id, return_type=True, return_id=False)
            if not node_type:
                logger.warning(" Unsupported Curie prefix: %s. Skipped!", node_id)
            if node_type:
                if node_type not in node_list_by_type:
                    node_list_by_type[node_type] = [node_id]
                else:
                    node_list_by_type[node_type].append(node_id)
        for node_type in node_list_by_type:
            if node_type not in self.annotator_clients or not node_list_by_type[node_type]:
                # skip for now
                continue
            # this is the list of original node ids like NCBIGene:1017, should be a unique list
            node_list = node_list_by_type[node_type]
            # this is the list of query ids like 1017
            query_list = [
                self.parse_curie(_id, return_type=False, return_id=True) for _id in node_list_by_type[node_type]
            ]
            # query_id to original id mapping
            node_id_d = dict(zip(query_list, node_list))
            res_by_id = self.query_biothings(node_type, query_list, fields=fields)
            if not raw:
                res_by_id = self.transform(res_by_id, node_type)
            for node_id in res_by_id:
                orig_node_id = node_id_d[node_id]
                res = res_by_id[node_id]
                # if not raw:
                #     if isinstance(res, list):
                #         # TODO: handle multiple results here
                #         res = [self.transform(r) for r in res]
                #     else:
                #         res = self.transform(res)
                res = {
                    "attribute_type_id": "biothings_annotations",
                    "value": res,
                }
                if append:
                    # append annotations to existing "attributes" field
                    node_d[orig_node_id]["attributes"].append(res)
                else:
                    # return annotations only
                    node_d[orig_node_id]["attributes"] = [res]

        return node_d


class AnnotatorHandler(BaseAPIHandler):
    name = "annotator"
    kwargs = {
        "*": {
            "raw": {"type": bool, "default": False},
            "fields": {"type": str, "default": None},
        },
        "POST": {
            # If True, append annotations to existing "attributes" field
            "append": {"type": bool, "default": False},
            # If set, limit the number of nodes to annotate
            "limit": {"type": int, "default": None},
        },
    }

    async def get(self, *args, **kwargs):
        annotator = Annotator()
        curie = args[0] if args else None
        if curie:
            try:
                annotated_node = annotator.annotate_curie(curie, raw=self.args.raw, fields=self.args.fields)
            except ValueError as e:
                raise HTTPError(400, reason=repr(e))
            self.finish(annotated_node)
        else:
            raise HTTPError(404, reason="missing required input curie id")

    async def post(self, *args, **kwargs):
        annotator = Annotator()
        try:
            annotated_node_d = annotator.annotate_trapi(
                self.args_json,
                append=self.args.append,
                raw=self.args.raw,
                fields=self.args.fields,
                limit=self.args.limit,
            )
        except ValueError as e:
            raise HTTPError(400, reason=repr(e))
        self.finish(annotated_node_d)
