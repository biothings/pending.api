import os
from pathlib import Path
import urllib.request
import shutil
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

# since this module is dynamically imported by the `python index.py --conf=xxx` process,
# `Path.cwd()` is actually the cwd of `index.py`, i.e. the "pending.api" folder
# Also note the plugin's name is "semmed_parser", diffferent from the API name "semmeddb"
narrower_relationships_folder = os.path.join(Path.cwd(), "plugins/semmed_parser/UMLS_narrower_relationships")
narrower_relationships_filename = "umls-parsed.json"
narrower_relationships_filepath = os.path.join(narrower_relationships_folder, narrower_relationships_filename)
narrower_relationships_url = "https://raw.githubusercontent.com/biothings/node-expansion/main/data/umls-parsed.json"

if not os.path.exists(narrower_relationships_folder):
    os.makedirs(narrower_relationships_folder)
if not os.path.exists(narrower_relationships_filepath):
    with urllib.request.urlopen(narrower_relationships_url) as response, open(narrower_relationships_filepath, 'wb') as local_file:
        shutil.copyfileobj(response, local_file)

JSON_RESOURCE_MAP = {
    "narrower_relationships": narrower_relationships_filepath
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
