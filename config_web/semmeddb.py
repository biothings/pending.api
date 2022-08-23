import os
from pathlib import Path
from biothings.web.settings.default import APP_LIST
from web.handlers.service.umls_service import UMLSResourceManager, UMLSJsonFileClient


ES_HOST = 'localhost:9200'
ES_INDEX = 'pending-semmeddb'
ES_DOC_TYPE = 'association'

API_PREFIX = 'semmeddb'
API_VERSION = ''

#########################
# URLSpec kwargs Part 1 #
#########################

JSON_RESOURCE_MAP = {
    # since this module is dynamically imported by the `python index.py --conf=xxx` process,
    # `Path.cwd()` is actually the cwd of `index.py`, i.e. the "pending.api" folder
    "narrower_relationships": os.path.join(Path.cwd(), "plugins/semmed_parser/UMLS_narrower_relationships/umls-parsed.json")
}

umls_resource_manager = UMLSResourceManager()
for resource_name, filepath in JSON_RESOURCE_MAP.items():
    umls_resource_manager.register(resource_name=resource_name,
                                   resource_client=UMLSJsonFileClient(filepath=filepath))
umls_resource_manager.open_resources()

#########################
# URLSpec kwargs Part 2 #
#########################

# the target fields in semmeddb documents to match during document frequency calculation
# necessary to web.handlers.service.ngd_service.DocStatsService
subject_field_name = "subject.umls"
object_field_name = "object.umls"

##############################
# URLSpec kwargs composition #
##############################

urlspec_kwargs = dict(subject_field_name=subject_field_name, object_field_name=object_field_name, umls_resouce_manager=umls_resource_manager)

APP_LIST = [
    (r"/{pre}/{ver}/query/ngd?", 'web.handlers.SemmedNGDHandler', urlspec_kwargs),
    *APP_LIST
]
