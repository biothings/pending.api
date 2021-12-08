from elasticsearch_dsl import Search, Q

from biothings.web.handlers.query import BaseAPIHandler

from .utils import normalized_google_distance, LRUCache, INFINITY_STR, \
    NGDZeroCountException, NGDInfinityException, NGDUndefinedException


class SemmedNGDHandler(BaseAPIHandler):
    name = "ngd"

    kwargs = {
        **BaseAPIHandler.kwargs,

        'GET': {
            'umls': {
                'type': list,
                # 'max': 2,  # exactly 2 umls are required. Will check the cardinality in get()
                'required': True
            }
        },
        'POST': {
            'umls': {
                'type': list,
                'max': 1000,
                'required': True
            }
        }
    }

    one_term_count_cache = LRUCache(capacity=10240)
    two_terms_count_cache = LRUCache(capacity=10240)
    total_count_cache = None  # There is only 1 number to cache, and `LRUCache` is an overkill
    ngd_cache = LRUCache(capacity=10240)

    async def get(self, *args, **kwargs):
        terms = self.args['umls']
        if len(terms) != 2:
            reason = f"Exact 2 umls are required. Got {len(terms)}."
            self.write_error(status_code=400, reason=reason)
            return

        try:
            ngd = await self.calculate_ngd(term_x=terms[0], term_y=terms[1])
            result = {
                "umls": terms,
                "ngd": ngd
            }
            self.finish(result)
        except NGDUndefinedException as ue:
            # Here we assume that `ue.cause` is an NGDZeroCountException, which is the only possibility so far.
            # If in the future there are other types of `ue.cause`, should check `type(ne.cause)` first in this clause.
            causative_term = ue.cause.term
            reason = f"the count of term '{causative_term}' is 0 in SemMedDB API."
            result = {
                "umls": terms,
                "ngd": "undefined",
                "reason": reason
            }
            self.finish(result)

    async def post(self, *args, **kwargs):
        async def yield_results():
            terms_list = self.args['umls']  # should be a list of 2-termed sublist, e.g. [['a', 'b'], ['c', 'd']]
            for terms in terms_list:
                if not isinstance(terms, list):
                    yield {
                        "umls": terms,
                        "ngd": "undefined",
                        "reason": f"A list of 2 umls are required. Got a {type(terms).__name__}"
                    }
                    continue

                if len(terms) != 2:
                    yield {
                        "umls": terms,
                        "ngd": "undefined",
                        "reason": f"Exact 2 umls are required. Got {len(terms)}."
                    }
                    continue

                try:
                    ngd = await self.calculate_ngd(term_x=terms[0], term_y=terms[1])
                    yield {
                        "umls": terms,
                        "ngd": ngd
                    }
                except NGDUndefinedException as ue:
                    causative_term = ue.cause.term
                    reason = f"the count of term '{causative_term}' is 0 in SemMedDB API."
                    yield {
                        "umls": terms,
                        "ngd": "undefined",
                        "reason": reason
                    }

        results = [res async for res in yield_results()]
        self.finish(results)

    async def count_one_term(self, term: str):
        cached_count = self.one_term_count_cache.get(term)
        if cached_count is not None:
            return cached_count

        """
        `match.to_dict()` => 
            {
                'bool': {
                    'should': [
                        {'match': {'subject.umls': <term>}},
                        {'match': {'object.umls': <term>}}
                    ]
                }
            }
            
        `query.to_dict()` => 
            {
                'query':
                    'bool': {
                        'should': [
                            {'match': {'subject.umls': <term>}},
                            {'match': {'object.umls': <term>}}
                        ]
                    }
                }
            }
        """
        match = Q("match", subject__umls=term) | Q("match", object__umls=term)  # boolean OR match
        query = Search().query(match)

        client = self.biothings.elasticsearch.async_client
        index = self.biothings.config.ES_INDEX  # e.g. "semmeddb_20210831_okplrch8" or "pending-semmeddb"
        # Why did we choose not to use `Search(using=client, index=index).query(match).count()`?
        # Because elasticsearch-dsl is not compatible with async elasticsearch client yet.
        resp = await client.count(body=query.to_dict(), index=index)
        count = resp["count"]

        self.one_term_count_cache.put(term, count)

        return count

    async def count_two_terms(self, term_x: str, term_y: str):
        cached_count = self.two_terms_count_cache.get((term_x, term_y))
        if cached_count is not None:
            return cached_count

        # (subject.umls:<term_x> AND object.umls:<term_y>) OR (subject.umls:<term_y> AND object.umls:<term_x>)
        match = (Q("match", subject__umls=term_x) & Q("match", object__umls=term_y)) | \
                (Q("match", subject__umls=term_y) & Q("match", object__umls=term_x))
        query = Search().query(match)

        client = self.biothings.elasticsearch.async_client
        index = self.biothings.config.ES_INDEX  # e.g. "semmeddb_20210831_okplrch8" or "pending-semmeddb"
        resp = await client.count(body=query.to_dict(), index=index)
        count = resp["count"]

        self.two_terms_count_cache.put((term_x, term_y), count)

        return count

    async def count_total(self):
        """
        Get the total number of documents in the index
        """
        if self.total_count_cache is not None:
            return self.total_count_cache

        # Read from metadata
        count = self.biothings.metadata.biothing_metadata[self.biothings.config.ES_DOC_TYPE]["stats"]["total"]

        # Read from cat.count()
        # client = self.biothings.elasticsearch.async_client
        # index = self.biothings.config.ES_INDEX  # e.g. "semmeddb_20210831_okplrch8" or "pending-semmeddb"
        # resp = await client.cat.count(index=index, params={"format": "json"})
        # count = int(resp[0]["count"])  # I cannot understand why resp[0]["count"] somehow is a string...

        self.total_count_cache = count

        return count

    async def prepare_counts_for_ngd(self, term_x: str, term_y: str):
        """
        To find the Normalized Google Distance between term x and term y, 4 queries are going to be performed:

        1. Query for the total number of `x`, which translates to `subject.umls:x OR object.umls:x`
        2. Query for the total number of `y`, which translates to `subject.umls:y OR object.umls:y`
        3. Query for the total number of `x and y`, which translates to
            `(subject.umls:x AND object.umls:y) OR (subject.umls:y AND object.umls:x)`
        4. Query for the total number of documents
        """
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
            ngd = INFINITY_STR
        else:
            ngd = normalized_google_distance(n=count_n, fx=count_x, fy=count_y, fxy=count_xy)

        # Do not wrap the below 2 lines in `finally`,
        # otherwise they will execute even when an NGDUndefinedException is raised.
        self.ngd_cache.put((term_x, term_y), ngd)
        return ngd
