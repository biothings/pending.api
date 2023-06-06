import os
from pathlib import Path
import requests
import json
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, A
from biothings.web.settings.default import APP_LIST
from web.service.umls_service import UMLSJsonFileClient, NarrowerRelationshipService


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
_narrower_relationships_folder = os.path.join(Path.cwd(), "assets/UMLS_narrower_relationships")
_narrower_relationships_filepath = os.path.join(_narrower_relationships_folder, "umls-parsed.json")
_narrower_relationships_url = "https://raw.githubusercontent.com/biothings/node-expansion/main/data/umls-parsed.json"

if not os.path.exists(_narrower_relationships_folder):
    os.makedirs(_narrower_relationships_folder)

if not os.path.exists(_narrower_relationships_filepath):
    _response = requests.get(_narrower_relationships_url)
    _response.raise_for_status()
    with open(_narrower_relationships_filepath, "w") as _local_file:
        json.dump(_response.json(), _local_file)

_narrower_relationships_client = UMLSJsonFileClient(filepath=_narrower_relationships_filepath)
_narrower_relationships_client.open_resource()
_term_expansion_service = NarrowerRelationshipService(umls_resource_client=_narrower_relationships_client,
                                                      add_input_prefix=True, remove_output_prefix=True)

#########################
# URLSpec kwargs Part 2 #
#########################

# The target fields in semmeddb documents to match during document frequency calculation
# They are necessary to web.handlers.service.ngd_service.DocStatsService
_subject_field_name = "subject.umls"
_object_field_name = "object.umls"

#########################
# URLSpec kwargs Part 3 #
#########################

# The aggregation name attached to the `Search` object for querying document frequencies.
# It's also the key to the aggregation value in the query result (as a dict), e.g. `result.aggregations["sum_of_predication_counts"]`.
# You are free to name it anything, actually.
_doc_freq_agg_name = "sum_of_predication_counts"

#########################
# URLSpec kwargs Part 4 #
#########################

# Get the total number of predications (as the new "total number of documents")

_es_temp_client = Elasticsearch(hosts=[ES_HOST])

_doc_total_search = Search(using=_es_temp_client, index=ES_INDEX).extra(size=0)
_doc_total_search.aggs.metric(_doc_freq_agg_name, A("sum", field="predication_count"))
_doc_total_resp = _doc_total_search.execute()
_doc_total = int(_doc_total_resp["aggregations"][_doc_freq_agg_name]["value"])

_es_temp_client.close()

##############################
# URLSpec kwargs composition #
##############################

urlspec_kwargs = dict(subject_field_name=_subject_field_name,
                      object_field_name=_object_field_name,
                      doc_freq_agg_name=_doc_freq_agg_name,
                      doc_total=_doc_total,
                      term_expansion_service=_term_expansion_service)

APP_LIST = [
    (r"/{pre}/{ver}/query/ngd?", "web.handlers.SemmedNGDHandler", urlspec_kwargs),
    *APP_LIST
]
