import copy
from biothings.web.settings.default import QUERY_KWARGS, ES_INDICES

PFOCR_FLAVOR_ALL = "pending-pfocr_all"
# PFOCR_FLAVOR_ALL = "pfocr_all_20231213_sdmo8dfz"
PFOCR_FLAVOR_SYNONYMS = "pending-pfocr_synonyms"
# PFOCR_FLAVOR_SYNONYMS = "pfocr_synonyms_20231213_sdmiqsdl"
PFOCR_FLAVOR_STRICT = "pending-pfocr_strict"
# PFOCR_FLAVOR_STRICT = "pfocr_strict_20231213_nfejmsas"

ES_HOST = "su12:9200"
ES_INDEX = [PFOCR_FLAVOR_ALL, PFOCR_FLAVOR_SYNONYMS, PFOCR_FLAVOR_STRICT]
ES_DOC_TYPE = "geneset"

API_PREFIX = "pfocr"
API_VERSION = ""

ES_INDICES = copy.deepcopy(ES_INDICES)

PFOCR_FLAVOR_INDICES = {
    "strict": PFOCR_FLAVOR_STRICT,
    "synonyms": PFOCR_FLAVOR_SYNONYMS,
    "all": PFOCR_FLAVOR_ALL,
}
ES_INDICES.update(PFOCR_FLAVOR_INDICES)

QUERY_KWARGS = copy.deepcopy(QUERY_KWARGS)

FLAVOR_FILTERS = {
    "strict": {"type": bool, "default": False},
    "synonyms": {"type": bool, "default": False},
    "all": {"type": bool, "default": False},
}
QUERY_KWARGS["*"].update(FLAVOR_FILTERS)
QUERY_KWARGS["POST"].update({"minimum_should_match": {"type": int}, "operator": {"type": str}})

# Default implementations: <from biothings.api web/settings/default.py>
ES_QUERY_PIPELINE = "biothings.web.query.AsyncESQueryPipeline"
ES_RESULT_TRANSFORM = "biothings.web.query.ESResultFormatter"
ES_QUERY_BACKEND = "web.engine.pfocr.PFOCRBackend"

# Default: ES_QUERY_BUILDER = 'biothings.web.query.ESQueryBuilder'
ES_QUERY_BUILDER = "web.query_builders.PfocrQueryBuilder"
