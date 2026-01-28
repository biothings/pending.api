import copy

from biothings.web.settings.default import APP_LIST

from web.handlers.nodenorm import (
    NodeNormHealthHandler,
    NormalizedNodesHandler,
    SemanticTypeHandler,
    SetIdentifierHandler,
    ValidConflationsHandler,
)

NODENORM_APP_LIST = copy.deepcopy(APP_LIST)

ES_HOST = "http://localhost:9200"
ES_INDEX = "pending-nodenorm"
ES_DOC_TYPE = "node"

# We want to override the default biothings StatusHandler
# The status endpoint will instead leveage the <NodeNormHealthHandler>
default_status_handler = (r"/{pre}/status", "biothings.web.handlers.StatusHandler")
try:
    NODENORM_APP_LIST.remove(default_status_handler)
except ValueError:
    pass

APP_LIST = [
    (r"/{pre}/{ver}/get_allowed_conflations?", ValidConflationsHandler),
    (r"/{pre}/{ver}/get_normalized_nodes?", NormalizedNodesHandler),
    (r"/{pre}/{ver}/get_semantic_types?", SemanticTypeHandler),
    (r"/{pre}/{ver}/get_setid?", SetIdentifierHandler),
    (r"/{pre}/{ver}/status?", NodeNormHealthHandler),
    *NODENORM_APP_LIST,
]

API_PREFIX = "nodenorm"
API_VERSION = ""
API_DEPRECATED = False
