"""
Lookup endpoints for the name-resolution service

Converted from SOLR -> Elasticsearch
"""

import dataclasses
import logging
import re
from typing import Optional

from biothings.web.handlers import BaseAPIHandler
from biothings.web.services.namespace import BiothingsNamespace
from tornado.web import HTTPError


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class LookupArgumentException(Exception):
    pass


@dataclasses.dataclass()
class LookupQuery:
    string: str
    autocomplete: Optional[bool]
    highlighting: Optional[bool]
    offset: Optional[int]
    limit: Optional[int]


@dataclasses.dataclass()
class LookupResult:
    curie: str
    label: str
    highlighting: dict[str, list[str]]
    synonyms: list[str]
    taxa: list[str]
    types: list[str]
    score: float
    clique_identifier_count: int


class BaseNameResolutionLookupHandler(BaseAPIHandler):
    """
    Base class for both the lookup and bulklookup endpoints

    We share an inheritence structure between the two, as they
    both have the same argument handling besides some small differences.
    So we create a `prepare` method that extracts those arguments,
    along with some additional auxillary methods for formatting
    things in the way we expect for elasticsearch
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lookup_queries: list[LookupQuery] = None
        self.filters: dict = None

    def prepare(self) -> None:
        """Handles argument parsing any lookup requests.

        Argument Matrix:
        | argument_name    | type      | required | default |
        | string           | str       | True     | None    | < lookup GET|POST
        | strings          | list[str] | True     | None    | < bulklookup POST
        | autocomplete     | bool      | False    | False   |
        | highlighting     | bool      | False    | False   |
        | offset           | int       | False    | 0       |
        | limit            | int       | False    | 10      |
        | biolink_type     | list[str] | False    | []      |
        | only_prefixes    | str       | False    | None    |
        | exclude_prefixes | str       | False    | None    |
        | only_taxa        | str       | False    | None    |

        Descriptions

        string: The string to search for. Only required argument. Used

        autocomplete: Toggle autocomplete on the search term.
        If autocomplete is enabled, we assume the input string is an in-complete
        phrase, whereas autocomplete disabled assumes that the search term is a complete phrase

        highlighting: Toggle return information on which labels
        and synonyms matched the search query

        offset: The number of results to skip.
        Offset must be greater than or equal to 0 (cannot have a negative offset). Primarily
        used for result pagination

        limit: The number of results to return.
        Limit must be in the range [0, 1000]. Primarily used for result pagination

        biolink_types: The Biolink types to filter to (with or without the `biolink:` prefix).
        Examples: <["biolink:Disease", "biolink:PhenotypicFeature"]>, would apply
        filtering for the types `biolink:Disease` OR `biolink:PhenotypicFeature`.
        Results with either would result in a match

        only_prefixes: Pipe-separated, case-sensitive list of prefixes to filter.
        Examples: <"MONDO|EFO">, would apply filters for `MONDO` OR `EFO`

        exclude_prefixes: Pipe-separated, case-sensitive list of prefixes to exclude.
        Examples: <"UMLS|EFO"> would apply filters for `UMLS` or `EFO`

        only_taxa: Pipe-separated, case-sensitive list of taxa to filter.
        Examples: <"NCBITaxon:9606|NCBITaxon:10090|NCBITaxon:10116|NCBITaxon:7955">
        would apply taxa filters for each pipe separated entry
        """
        lookup_strings = self._parse_lookup_string_arguments()

        try:
            sanitized_lookup_strings = self._sanitize_lookup_query(lookup_strings)
        except Exception as lookup_arg_exc:
            logger.error("Unknown issue occured attempting to sanitize input query")
            logger.exception(lookup_arg_exc)
            raise LookupArgumentException from lookup_arg_exc

        self.filters = self._build_lookup_filters()

        def parse_boolean(argument: str | bool) -> bool:
            if isinstance(argument, bool):
                return argument
            if isinstance(argument, str):
                return not argument.lower() == "false"
            return False

        autocomplete_option = parse_boolean(self.get_argument("autocomplete", default=False, strip=True))
        highlighting_option = parse_boolean(self.get_argument("highlighting", default=False, strip=True))
        try:
            offset_option = int(self.get_argument("offset", default=0, strip=True))
            limit_option = int(self.get_argument("limit", default=10, strip=True))
            if offset_option < 0 or limit_option < 0:
                raise ValueError
        except ValueError:
            lookup_message = (
                "Invalid literal for `offset` or `limit` option | " "offset and limit must be non-negative integers "
            )
            raise LookupArgumentException(lookup_message)

        self.lookup_queries = []
        for search_string in sanitized_lookup_strings:
            lookup_query = LookupQuery(
                string=search_string,
                autocomplete=autocomplete_option,
                highlighting=highlighting_option,
                offset=offset_option,
                limit=limit_option,
            )
            self.lookup_queries.append(lookup_query)

    def _parse_lookup_string_arguments(self) -> list[str]:
        """Attempt to determine if this is a singular or bulk lookup."""
        search_string = self.get_argument("string", default=None)
        search_string_collection = self.get_argument("strings", default=None)

        if search_string is None and search_string_collection is None:
            raise LookupArgumentException("Either `string` or `strings` must be supplied for lookup")

        if search_string is not None and search_string_collection is not None:
            raise LookupArgumentException("Both `string` or `strings` cannot both be supplied for lookup")

        lookup_strings = []
        if search_string is not None and search_string_collection is None:
            lookup_strings.append(search_string)
        elif search_string is None and search_string_collection is not None:
            lookup_strings.extend(search_string_collection)
        return lookup_strings

    def _sanitize_lookup_query(self, lookup_strings: list[str]) -> list[tuple[str]]:
        r"""Performs input sanitization on the lookup query terms.

        Sanitization Operations:
        1) strip and lowercase the query (all indexes are case-insensitive)
        2) evaluate string encoding
            There is a possibility that the input text isn't in UTF-8.
            Python packages that try to determine what the encoding is:
            - https://pypi.org/project/charset-normalizer/
            - https://www.crummy.com/software/BeautifulSoup/bs4/doc/#unicode-dammit
            But the only issue we've run into so far has been the Windows smart
            quote (https://github.com/TranslatorSRI/NameResolution/issues/176), so
            let's detect and replace just those characters.
        3) prune any empty string searches
            If there's nothing to search don't perform any search
        4) escape special characters
            We need to use backslash to escape characters
               ( e.g. "\(" )
            to remove the special significance of characters
            inside round brackets, but not inside double-quotes.
            So we escape them separately:
            - For a full exact search, we only remove double-quotes
            and slashes, leaving other special characters as-is.
        5) escape special characters for tokenization
            we escape all special characters with backslashes as well as
            other characters that might mess up the search.
        """
        sanitized_lookup_strings = []
        for lookup_string in lookup_strings:
            lookup_string = lookup_string.strip().lower()

            windows_smart_single_quote_pattern = r"[‘’]"
            windows_smart_double_quote_pattern = r"[“”]"

            lookup_string = re.sub(windows_smart_single_quote_pattern, "'", lookup_string)
            lookup_string = re.sub(windows_smart_double_quote_pattern, '"', lookup_string)

            if lookup_string is not None and lookup_string != "":
                lookup_string_with_escaped_groups = lookup_string.replace("\\", "")
                lookup_string_with_escaped_groups = lookup_string_with_escaped_groups.replace('"', "")

                # Regex overview
                # r'[!(){}\[\]^"~*?:/+-\\]'
                # Match a single character present in the list below [!(){}\[\]^"~*?:/+-\\]
                # !(){}
                #  matches a single character in the list !(){} (case sensitive)
                # \[ matches the character [ with index 9110 (5B16 or 1338) literally (case sensitive)
                # \] matches the character ] with index 9310 (5D16 or 1358) literally (case sensitive)
                # ^"~*?:/
                #  matches a single character in the list ^"~*?:/ (case sensitive)
                # +-\\ matches a single character in the range between + (index 43) and \ (index 92) (case sensitive)
                special_characters_group = r'[!(){}\[\]^"~*?:/+-\\]'

                # \g<0> is a backreference which will insert the text most recently matched by
                # entire pattern. So in this case, because the entire pattern is the special
                # characters group we wish to escape, it will surrond the last matched special
                # character with quotes and backslash
                # Example: query_term? -> query_term"\?"
                substitution_escape_backreference = r"\\\g<0>"
                fully_escaped_lookup_string = re.sub(
                    special_characters_group, substitution_escape_backreference, lookup_string
                )

                fully_escaped_lookup_string = fully_escaped_lookup_string.replace("&&", " ")
                fully_escaped_lookup_string = fully_escaped_lookup_string.replace("||", " ")

                sanitized_lookup_strings.append(set([lookup_string_with_escaped_groups, fully_escaped_lookup_string]))

        return sanitized_lookup_strings

    def _build_lookup_filters(self) -> dict:
        """Handles the parsing and building of various elasticsearch boolean logic queries.

        We have two types of boolean logic queries we need to build for this endpoint

        1) should
        In this case we want to boolean OR specific different types of required
        fields we want in the results output

        2) must_not
        In this case we to boolean AND NOT specific different types of required
        fields we want to ensure `don't` exist in the results output
        """
        biolink_types = self.get_argument("biolink_types", default=[], strip=True)

        filter_delimiter = "|"

        only_prefixes = self.get_argument("only_prefixes", default="", strip=True)
        only_prefixes = only_prefixes.split(filter_delimiter)
        try:
            only_prefixes.remove("")
        except ValueError:
            pass

        exclude_prefixes = self.get_argument("exclude_prefixes", default="", strip=True)
        exclude_prefixes = exclude_prefixes.split(filter_delimiter)
        try:
            exclude_prefixes.remove("")
        except ValueError:
            pass

        only_taxa = self.get_argument("only_taxa", default="", strip=True)
        only_taxa = only_taxa.split(filter_delimiter)
        try:
            only_taxa.remove("")
        except ValueError:
            pass

        # Apply filters as needed.
        filters = {"should": [], "must_not": []}

        # Biolink type filter
        # Elasticsearch should
        for biolink_type in biolink_types:
            biolink_type = biolink_type.strip()
            if biolink_type is not None:
                should_filter = {"term": {"biolink_types": biolink_type.remove("biolink:")}}
                filters["should"].append(should_filter)

        # Prefix: only filter
        # Elasticsearch should + Match boolean prefix query
        for prefix in only_prefixes:
            prefix = prefix.strip()
            should_filter = {"prefix": {"curie": prefix}}
            filters["should"].append(should_filter)

        # Prefix: exclude filter
        # Elasticsearch must not
        for prefix in exclude_prefixes:
            prefix = prefix.strip()
            must_not_filter = {"prefix": {"curie": prefix}}
            filters["must_not"].append(must_not_filter)

        # Taxa filter.
        # only_taxa is like: 'NCBITaxon:9606|NCBITaxon:10090|NCBITaxon:10116|NCBITaxon:7955'
        # Elasticsearch should
        for taxon in only_taxa:
            taxon = taxon.strip()
            should_filter = {"term": {"taxa": taxon}}
            filters["should"].append(should_filter)

        # We also need to include entries that don't have taxa specified.
        # TODO Skipping for the moment as we need to update the index
        # filters["should"].append({ "term" : { "taxon_specific" : False } }

        return filters


class NameResolutionLookupHandler(BaseNameResolutionLookupHandler):
    """
    Mirror implementation to the renci implementation found at
    https://name-resolution-sri.renci.org/docs#/

    We intend to mirror the /lookup endpoint
    """

    name = "lookup"

    async def get(self):
        """Returns cliques with a name or synonym that contains a specified string."""
        try:
            lookup_result = await lookup(self.biothings, self.lookup_queries[0], self.filters)
        except Exception as gen_exc:
            raise HTTPError(detail="Error occurred during processing.", status_code=500) from gen_exc
        self.finish(lookup_result)

    async def post(self):
        """Returns cliques with a name or synonym that contains a specified string."""
        try:
            lookup_result = await lookup(self.biothings, self.lookup_queries[0], self.filters)
        except Exception as gen_exc:
            raise HTTPError(detail="Error occurred during processing.", status_code=500) from gen_exc
        self.finish(lookup_result)


class NameResolutionBulkLookupHandler(BaseAPIHandler):
    """
    Mirror implementation to the renci implementation found at
    https://name-resolution-sri.renci.org/docs#/

    We intend to mirror the /bulk-lookup endpoint
    """

    name = "bulk-lookup"

    async def post(self) -> dict[str, list[LookupResult]]:
        """Returns cliques with a name or synonym that contains a specified string sent via batch."""

        try:
            lookup_result = {}
            for lookup_query in self.lookup_queries:
                lookup_result[lookup_query.string] = await lookup(self.biothings, lookup_query, self.filters)
            return lookup_result
        except Exception as gen_exc:
            raise HTTPError(detail="Error occurred during processing.", status_code=500) from gen_exc
        self.finish(lookup_result)


async def lookup(
    biothings_metadata: BiothingsNamespace, lookup_query: list[LookupQuery], filters: dict
) -> list[LookupResult]:
    """Returns cliques with a name or synonym that contains a specified string."""
    elasticsearch_query = _build_elasticsearch_query(lookup_query, filters)

    # Turn on highlighting if requested.
    highlight_configuration = None
    if lookup_query.highlighting:
        highlight_configuration = {
            "type": "unified",
            "encoder": "html",
            "require_field_match": False,
            "fields": {
                "names": {"pre_tags": ["<strong>"], "post_tags": ["</strong>"]},
                "preferred_names": {"pre_tags": ["<strong>"], "post_tags": ["</strong>"]},
            },
        }

    search_result_ordering = [{"_score": "desc"}, {"clique_identifier_count": "desc"}]

    index = biothings_metadata.elasticsearch.metadata.indices["node"]
    search_parameters = {
        "query": elasticsearch_query,
        "index": index,
        "highlight": highlight_configuration,
        "size": lookup_query.limit,
        "sort": search_result_ordering,
        "from": lookup_query.offset,
    }
    lookup_response = await biothings_metadata.elasticsearch.async_client.search(**search_parameters)

    outputs = []
    for doc in lookup_response["hits"]["hits"]:
        preferred_matches = []
        synonym_matches = []

        highlighting_response = doc.get("highlight", None)
        if highlighting_response is not None and isinstance(highlighting_response, dict):
            synonym_matches.extend(highlighting_response.get("names", []))
            preferred_matches.extend(highlighting_response.get("preferred_name", []))

        source = doc["_source"]
        outputs.append(
            LookupResult(
                curie=source.get("curie", ""),
                label=source.get("preferred_name", ""),
                highlighting=(
                    {
                        "labels": preferred_matches,
                        "synonyms": synonym_matches,
                    }
                    if lookup_query.highlighting
                    else {}
                ),
                synonyms=source.get("names", []),
                score=doc.get("_score", ""),
                taxa=source.get("taxa", []),
                clique_identifier_count=source.get("clique_identifier_count", 0),
                types=[f"biolink:{d}" for d in source.get("biolink_types", [])],
            )
        )

    return outputs


def _build_elasticsearch_query(lookup_query: list[LookupQuery], filters: dict) -> dict:
    queries = []

    # Base Query
    for lookup_string in lookup_query.string:
        queries.append(
            {
                "multi_match": {
                    "query": lookup_string,
                    "type": "best_fields",
                    "fields": ["preferred_name^25", "name^10"],
                }
            }
        )

    # https://www.elastic.co/search-labs/blog/elasticsearch-autocomplete-search#2.-query-time
    if lookup_query.autocomplete:
        for lookup_string in lookup_query.string:
            queries.append(
                {
                    "multi_match": {
                        "query": lookup_string,
                        "type": "phrase",
                        "fields": ["preferred_name^30", "name^20"],
                    }
                }
            )

    compound_lookup_query = {
        "bool": {
            "must": [
                {
                    "dis_max": {
                        "queries": queries,
                    }
                }
            ]
        }
    }
    if len(filters["should"]) > 0:
        compound_lookup_query["bool"]["must"].append({"bool": {"should": [*filters["should"]]}})

    if len(filters["must_not"]) > 0:
        compound_lookup_query["bool"]["must_not"] = [*filters["must_not"]]

    return compound_lookup_query
