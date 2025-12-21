import copy

from biothings.web.settings.default import APP_LIST

from web.handlers.nameres import NameResolutionHealthHandler, NameResolutionSynonymsHandler

NAMERES_APP_LIST = copy.deepcopy(APP_LIST)

ES_HOST = "http://localhost:9200"
ES_INDEX = "pending-nameres"
ES_DOC_TYPE = "node"

# We want to override the default biothings StatusHandler
# The status endpoint will instead leveage the <NameResolutionmHealthHandler>
default_status_handler = (r"/{pre}/status", "biothings.web.handlers.StatusHandler")
try:
    NAMERES_APP_LIST.remove(default_status_handler)
except ValueError:
    pass

APP_LIST = [
    (r"/{pre}/{ver}/synonyms?", NameResolutionSynonymsHandler),
    (r"/{pre}/{ver}/status?", NameResolutionHealthHandler),
    *NAMERES_APP_LIST,
]

API_PREFIX = "nameres"
API_VERSION = ""
API_DEPRECATED = False
