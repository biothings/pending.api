from biothings.web.handlers.query import QueryHandler, ensure_awaitable, capture_exceptions
from biothings.web.options import ReqResult

from .utils import normalized_google_distance, LRUCache, NGDZeroCountException, NGDInfinityException, NGDUndefinedException

import re  # to parse query strings


class SemmedNGDQueryStringParser:
    entity_pattern = re.compile(r"(?P<scope>[\w|.]+):(?P<term>[^:]+)")
    acceptable_scopes = set(['subject.umls', 'object.umls'])

    class ParserException(Exception):
        def __init__(self, message):
            self.message = message

    @classmethod
    def parse_query_string(cls, q_string):
        """
        `get()` is supposed to accept "query string queries", as specified in
        https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html.

        Example: http://localhost:8000/semmeddb/query/ngd?q=subject.umls:C0684074%20AND%20object.umls:C0003063.
        The decoded "query string" is "subject.umls:C0684074 AND object.umls:C0003063".

        For this handler, we specify that ONLY "AND" can be used in the query string, and TWO entity strings with the
        "<scope>:<term>" pattern must be provided. I.e. a solid query string for this hanlder is like:

            <scope>:<term> AND <scope>:<term>

        The regexp used to parse `<scope>:<term>` pattern is borrowed from
        https://github.com/biothings/biothings.api/blob/master/biothings/web/query/builder.py#L53

        The parsed result is a dict like:

            {
                operator: "AND"
                entities: [{'scope': 'subject.umls', 'term': 'C0684074'}, {'scope': 'object.umls', 'term': 'C0003063'}]
            }
        """

        def match_entity(entity_string):
            entity_match = re.fullmatch(cls.entity_pattern, entity_string)
            if entity_match is None:
                raise cls.ParserException(message=f"An entity in input query string must have pattern <scope>:<term>. "
                                                  f"Got '{entity_string}' as an entity.")
            if entity_match["scope"] not in cls.acceptable_scopes:
                raise cls.ParserException(message=f"An entity in input query string must have a scope in "
                                                  f"{cls.acceptable_scopes}. Got '{entity_string}' with "
                                                  f"'{entity_match['scope']}' as a scope.")
            return entity_match

        q_string_group = q_string.split()  # by default it will split by whitespaces

        if len(q_string_group) != 3:
            raise cls.ParserException(message=f"Input query string must have 3 components, 'ENTITY1 AND ENTITY2'. "
                                              f"Got '{q_string}' with only {len(q_string_group)} component(s).")

        operator_str = q_string_group[1]
        if operator_str != "AND":
            raise cls.ParserException(message=f"Input query string must use AND operator. "
                                              f"Got '{q_string}' with {operator_str} operator.")

        entity_1_match = match_entity(q_string_group[0])
        entity_2_match = match_entity(q_string_group[2])
        return {
            "operator": operator_str,
            "entities": [entity_1_match, entity_2_match]
        }


class SemmedNGDHandler(QueryHandler):
    name = "query"

    one_term_count_cache = LRUCache(capacity=10240)
    two_terms_count_cache = LRUCache(capacity=10240)
    total_count_cache = None  # There is only 1 number to cache, and `LRUCache` is an overkill
    ngd_cache = LRUCache(capacity=10240)

    @capture_exceptions
    async def get(self, *args, **kwargs):
        """
        To find the Normalized Google Distance between term x and term y, 3 queries are going to be performed:

        1. Query for the total number of `x and y`, which translates to
            `(subject.umls:x AND object.umls:y) OR (subject.umls:y AND object.umls:x)`
        2. Query for the total number of `x`, which translates to `subject.umls:x OR object.umls:x`
        3. Query for the total number of `y`, which translates to `subject.umls:y OR object.umls:y`
        """
        self.event['value'] = 1

        q_string = self.args.q
        if not q_string:
            self.write_error(status_code=400, reason="Must input a query string, e.g. "
                                                     "'q=subject.umls:C0684074 AND object.umls:C0003063'.")

        try:
            q_dict = SemmedNGDQueryStringParser.parse_query_string(q_string)
            terms = [entity["term"] for entity in q_dict["entities"]]

            ngd = await self.calculate_ngd(term_x=terms[0], term_y=terms[1])

            result = {entity["scope"]: entity["term"] for entity in q_dict["entities"]}
            result["ngd"] = ngd

            self.finish(result)
        except SemmedNGDQueryStringParser.ParserException as pe:
            self.write_error(status_code=400, reason=pe.message)
        except NGDUndefinedException as ue:
            # Here we assume that `ue.cause` is an NGDZeroCountException, which is the only possibility so far.
            # If in the future there are other types of `ue.cause`, should check `type(ne.cause)` first in this clause.
            causative_term = ue.cause.term
            reason = f"NGD is undefined because the count of term '{causative_term}' is 0 in SemMedDB API."

            # Nevertheless, we still use status code 200 for this type of error
            self.write_error(status_code=200, reason=reason)

    async def count_q(self, q: str):
        """
        Run a query containing the query string `q` and return the "total" field of the response.

        self.args is a `biothings.web.options.manager.ReqResult` object (which inherits from dotdict) like:

            ReqResult({'_sorted': True,
                       'biothing_type': None,
                       'dotfield': False,
                       'facet_size': 10,
                       'format': 'json',
                       'q': 'subject.umls:C0684074 OR object.umls:C0003063',
                       'raw': False,
                       'rawquery': False})

        It can be used as an query, as in `response = await ensure_awaitable(self.pipeline.search(**self.args))`

        Here we will modify the `q` field inside to create new queries
        """
        query = ReqResult(**self.args)
        query.q = q
        query.size = 0  # set size=0 to avoid retrieving the content of documents; we only need the counts of documents
        resp = await ensure_awaitable(self.pipeline.search(**query))
        return resp["total"]

    async def count_one_term(self, term: str):
        cached_count = self.one_term_count_cache.get(term)
        if cached_count is not None:
            return cached_count

        q = "subject.umls:{x} OR object.umls:{x}".format(x=term)
        count = await self.count_q(q)

        self.one_term_count_cache.put(term, count)

        return count

    async def count_two_terms(self, term_x: str, term_y: str):
        cached_count = self.two_terms_count_cache.get((term_x, term_y))
        if cached_count is not None:
            return cached_count

        q = "(subject.umls:{x} AND object.umls:{y}) OR " \
            "(subject.umls:{y} AND object.umls:{x})".format(x=term_x, y=term_y)
        count = await self.count_q(q)

        self.two_terms_count_cache.put((term_x, term_y), count)

        return count

    async def count_total(self):
        """
        Get the total number of documents in the index
        """
        if self.total_count_cache is not None:
            return self.total_count_cache

        client = self.biothings.elasticsearch.async_client
        index = self.biothings.config.ES_INDEX  # e.g. "semmeddb_20210831_okplrch8" or "pending-semmeddb"
        resp = await client.cat.count(index=index, params={"format": "json"})
        count = int(resp[0]["count"])  # I cannot understand why resp[0]["count"] somehow is a string...

        self.total_count_cache = count

        return count

    async def prepare_counts_for_ngd(self, term_x: str, term_y: str):
        count_x = await self.count_one_term(term_x)
        if count_x == 0:
            raise NGDZeroCountException(term=term_x)

        count_y = await self.count_one_term(term_y)
        if count_y == 0:
            raise NGDZeroCountException(term=term_y)

        count_xy = await self.count_two_terms(term_x, term_y)
        if count_xy == 0:
            raise NGDInfinityException()

        count_n = await self.count_total()
        return count_x, count_y, count_xy, count_n

    async def calculate_ngd(self, term_x: str, term_y: str):
        cached_ngd = self.ngd_cache.get((term_x, term_y))
        if cached_ngd is not None:
            return cached_ngd

        try:
            count_x, count_y, count_xy, count_n = await self.prepare_counts_for_ngd(term_x, term_y)
        except NGDZeroCountException as zce:
            raise NGDUndefinedException(cause=zce)
        except NGDInfinityException:
            ngd = float('inf')
        else:
            ngd = normalized_google_distance(n=count_n, fx=count_x, fy=count_y, fxy=count_xy)

        # Do not wrap the below 2 lines in `finally`,
        # otherwise they will execute even when an NGDUndefinedException is raised.
        self.ngd_cache.put((term_x, term_y), ngd)
        return ngd
