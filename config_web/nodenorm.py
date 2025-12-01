from biothings.web.settings.default import APP_LIST

from web.handlers.nodenorm import (
    NodeNormStatusHandler,
    NormalizedNodesHandler,
    SemanticTypeHandler,
    SetIdentifierHandler,
)

ES_HOST = "http://localhost:9200"
ES_INDEX = "pending-nodenorm"
ES_DOC_TYPE = "node"

APP_LIST = [
    (r"/{pre}/{ver}/get_normalized_nodes?", NormalizedNodesHandler),
    (r"/{pre}/{ver}/get_semantic_types?", SemanticTypeHandler),
    (r"/{pre}/{ver}/get_setid?", SetIdentifierHandler),
    (r"/{pre}/{ver}/status?", NodeNormStatusHandler),
    *APP_LIST,
]

API_PREFIX = "nodenorm"
API_VERSION = ""
API_DEPRECATED = False
