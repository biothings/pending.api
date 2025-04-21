from biothings.web.settings.default import APP_LIST

ES_HOST = "http://localhost:9200"
ES_INDEX = "pending-text_mining_targeted_association"
ES_DOC_TYPE = "association"

APP_LIST = [(r"/{pre}/{ver}/query/graph?", "web.handlers.GraphQueryHandler"), *APP_LIST]

API_PREFIX = "text_mining_targeted_association"
API_VERSION = ""
SMARTAPI_ID = "978fe380a147a8641caf72320862697b"

ES_QUERY_PIPELINE = "web.pipeline.PendingQueryPipeline"
ES_QUERY_BUILDER = "web.pipeline.PendingQueryBuilder"
ES_RESULT_TRANSFORM = "web.pipeline.GraphResultTransform"
