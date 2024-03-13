import re

# ES_HOST = "localhost:9200"
# ES_HOST = "es8.biothings.io:9200"
ES_HOST = "biothings.ci.transltr.io"
ES_INDEX = "pending-hpo"
ES_DOC_TYPE = "phenotype"

API_PREFIX = "hpo"
API_VERSION = ""


# CURIE ID support based on BioLink Model
BIOLINK_MODEL_PREFIX_BIOTHINGS_GENE_MAPPING = {
    "HP": {
        "type": "phenotype",
        "field": "hp",
        "regex_term_pattern": "(?P<term>HP:[0-9]+)",
    }
}
biolink_curie_regex_list = []
for (
    biolink_prefix,
    mapping,
) in BIOLINK_MODEL_PREFIX_BIOTHINGS_GENE_MAPPING.items():
    field_match = mapping.get("field", [])
    term_pattern = mapping.get("regex_term_pattern", None)
    if term_pattern is None:
        term_pattern = "(?P<term>[^:]+)"

    raw_expression = rf"({biolink_prefix}):{term_pattern}"
    compiled_expression = re.compile(raw_expression, re.I)

    pattern = (compiled_expression, field_match)
    biolink_curie_regex_list.append(pattern)


ANNOTATION_ID_REGEX_LIST = [
    *biolink_curie_regex_list,
]

ANNOTATION_DEFAULT_SCOPES = ["_id", "hp"]
