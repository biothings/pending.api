from biothings.web.settings.default import APP_LIST
from web.handlers.service.umls_service import UMLSResourceManager, UMLSJsonFileClient

JSON_RESOURCE_MAP = {
    "narrower_relationships": "/data/pending/dataupload/mysrc/semmeddb/UMLS_narrower_relationships/umls-parsed.json"
}

umls_resource_manager = UMLSResourceManager()
for resource_name, filepath in JSON_RESOURCE_MAP.items():
    umls_resource_manager.register(resource_name=resource_name,
                                   resource_client=UMLSJsonFileClient(filepath=filepath))
umls_resource_manager.open_resources()

ES_HOST = 'localhost:9200'
ES_INDEX = 'pending-semmeddb'
ES_DOC_TYPE = 'association'

API_PREFIX = 'semmeddb'
API_VERSION = ''
APP_LIST = [
    (r"/{pre}/{ver}/query/ngd?", 'web.handlers.SemmedNGDHandler', dict(umls_resouce_manager=umls_resource_manager)),
    *APP_LIST
]
