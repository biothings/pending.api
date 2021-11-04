from biothings.web.settings.default import APP_LIST

ES_HOST = 'localhost:9200'
ES_INDEX = 'pending-semmeddb'
ES_DOC_TYPE = 'association'

API_PREFIX = 'semmeddb'
API_VERSION = ''
APP_LIST = [
    (r"/{pre}/{ver}/query/ngd?", 'web.handlers.SemmedNGDHandler'),
    *APP_LIST
]
