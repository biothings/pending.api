from biothings.web.settings.default import APP_LIST

ES_HOST = "http://localhost:9200"
ES_INDEX = "pending-nodenorm"
ES_DOC_TYPE = "node"

APP_LIST = [
    (r"/{pre}/{ver}/get_normalized_nodes?", "web.handlers.nodenorm.normalized_nodes.NormalizedNodesHandler"), *APP_LIST,
    (r"/{pre}/{ver}/get_setid?", "web.handlers.nodenorm.set_identifiers"), *APP_LIST
]

API_PREFIX = "nodenorm"
API_VERSION = ""
API_DEPRECATED = False
