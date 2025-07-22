from biothings.web.settings.default import APP_LIST

ES_HOST = "http://localhost:9200"
ES_INDEX = "pending-nodenorm"
ES_DOC_TYPE = "node"

API_PREFIX = "nodenorm"
API_VERSION = ""
API_DEPRECATED = False


APP_LIST = [(r"/{pre}/{ver}/query/graph?", "web.handlers.GraphQueryHandler"), *APP_LIST]

ES_QUERY_PIPELINE = "web.pipeline.PendingQueryPipeline"
ES_QUERY_BUILDER = "web.pipeline.PendingQueryBuilder"
ES_RESULT_TRANSFORM = "web.pipeline.GraphResultTransform"
