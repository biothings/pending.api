import re

# ES_HOST = "localhost:9200"
ES_HOST = "es8.biothings.io:9200"
ES_INDEX = "pending-hpo"
ES_DOC_TYPE = "phenotype"

API_PREFIX = "hpo"
API_VERSION = ""


# CURIE ID support based on BioLink Model
BIOLINK_MODEL_PREFIX_BIOTHINGS_GENE_MAPPING = {
    "HP": {"type": "phenotype", "field": "hp", "keep_prefix": True},
}
biolink_curie_regex_list = []
for (
    biolink_prefix,
    mapping,
) in BIOLINK_MODEL_PREFIX_BIOTHINGS_GENE_MAPPING.items():
    expression = re.compile(rf"({biolink_prefix}):(?P<term>[^:]+)", re.I)
    field_match = mapping["field"]
    pattern = (expression, field_match)
    biolink_curie_regex_list.append(pattern)


ANNOTATION_ID_REGEX_LIST = [
    *biolink_curie_regex_list,
]

ANNOTATION_DEFAULT_SCOPES = ["_id", "hp"]
