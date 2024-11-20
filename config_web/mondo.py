import copy
import re

from biothings.web.settings.default import QUERY_KWARGS

ES_HOST = "http://localhost:9200"
ES_INDEX = "pending-mondo"  # the index name convention is like "pending-<ApiName>"
ES_DOC_TYPE = "disease"

API_PREFIX = "mondo"
API_VERSION = ""

_extra_kwargs = {"ignore_obsolete": {"type": bool, "default": True}}
QUERY_KWARGS = copy.deepcopy(QUERY_KWARGS)
QUERY_KWARGS["*"].update(_extra_kwargs)
ES_QUERY_BUILDER = "web.query_builders.OntologyQueryBuilder"

# id regex pattern
id_mondo_regex_pattern = (re.compile(r"MONDO\:[0-9]+", re.I), ["_id"])

ANNOTATION_ID_REGEX_LIST = [id_mondo_regex_pattern]

ANNOTATION_DEFAULT_SCOPES = ["_id"]
PENDING_API_DEPRECATION_STATUS = False
