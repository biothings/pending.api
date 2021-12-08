from biothings.web.settings.default import APP_LIST

ES_HOST = 'localhost:9200'
ES_INDEX = 'pending-biggim'
ES_DOC_TYPE = 'association'

API_PREFIX = 'biggim'
API_VERSION = ''
APP_LIST = [
    (r"/{pre}/{ver}/query/graph?", 'web.handlers.GraphQueryHandler'),
    *APP_LIST
]

API_PREFIX = 'biggim'
API_VERSION = ''

ES_QUERY_PIPELINE = "web.pipeline.PendingQueryPipeline"
ES_QUERY_BUILDER = "web.pipeline.PendingQueryBuilder"
ES_RESULT_TRANSFORM = "web.pipeline.GraphResultTransform"
