import copy
from biothings.web.settings.default import QUERY_KWARGS

PFOCR_FLAVOR_ALL = "pending-pfocr-all"
PFOCR_FLAVOR_SYNONYMS = "pending-pfocr-synonyms"
PFOCR_FLAVOR_STRICT = "pending-pfocr-strict"

ES_HOST = "localhost:9200"
ES_INDEX = [PFOCR_FLAVOR_ALL, PFOCR_FLAVOR_SYNONYMS, PFOCR_FLAVOR_STRICT]
ES_DOC_TYPE = "geneset"

API_PREFIX = "pfocr"
API_VERSION = ""

QUERY_KWARGS = copy.deepcopy(QUERY_KWARGS)
QUERY_KWARGS["POST"].update({"minimum_should_match": {"type": int}, "operator": {"type": str}})

ES_QUERY_BUILDER = "web.query_builders.PfocrQueryBuilder"
# from biothings.api web/settings/default.py we have
# ES_QUERY_PIPELINE = 'biothings.web.query.AsyncESQueryPipeline'
# ES_QUERY_BUILDER = 'biothings.web.query.ESQueryBuilder'
# ES_QUERY_BACKEND = 'biothings.web.query.AsyncESQueryBackend'
# ES_RESULT_TRANSFORM = 'biothings.web.query.ESResultFormatter'

APP_LIST = [
    (r"/pfocr/{flavor}", "web.handlers.pfocr.PFOCR_Handler")
]
