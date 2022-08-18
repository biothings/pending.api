from biothings.web.handlers.query import BaseAPIHandler

from .utils import normalized_google_distance, INFINITY_STR, \
    NGDZeroCountException, NGDInfinityException, NGDUndefinedException
from .service.ngd_service import UMLSDocumentService, NGDCache, UMLSDocumentCache


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

    document_cache = UMLSDocumentCache(unary_capacity=10240, bipartite_capacity=10240)
    distance_cache = NGDCache(capacity=10240)

    def prepare(self):
        super().prepare()

        self.doc_service = UMLSDocumentService(
            es_async_client=self.biothings.elasticsearch.async_client,
            es_index_name=self.biothings.config.ES_INDEX
        )

    async def get(self, *args, **kwargs):
        terms = self.args['umls']
        if len(terms) != 2:
            reason = f"Exact 2 UMLS terms are required. Got {terms}, {len(terms)} term(s)."
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
            reason = f"the document frequency of term '{causative_term}' is 0 in SemMedDB API."
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
                        "reason": f"A list of 2 UMLS terms are required. Got {terms}, a {type(terms).__name__}"
                    }
                    continue

                if len(terms) != 2:
                    yield {
                        "umls": terms,
                        "ngd": "undefined",
                        "reason": f"Exact 2 UMLS terms are required. Got {terms}, {len(terms)} term(s)."
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
                    reason = f"the document frequency of term '{causative_term}' is 0 in SemMedDB API."
                    yield {
                        "umls": terms,
                        "ngd": "undefined",
                        "reason": reason
                    }

        results = [res async for res in yield_results()]
        self.finish(results)

    async def unary_doc_freq(self, term: str):
        cached_doc_freq = self.document_cache.read_unary_doc_freq(term)
        if cached_doc_freq is not None:
            return cached_doc_freq

        doc_freq = await self.doc_service.unary_doc_freq(term)
        self.document_cache.write_unary_doc_freq(term, doc_freq)

        return doc_freq

    async def bipartite_doc_freq(self, term_x: str, term_y: str):
        cached_doc_freq = self.document_cache.read_bipartite_doc_freq(term_x, term_y)
        if cached_doc_freq is not None:
            return cached_doc_freq

        doc_freq = await self.doc_service.bipartite_doc_freq(term_x, term_y)
        self.document_cache.write_bipartite_doc_freq(term_x, term_y, doc_freq)

        return doc_freq

    async def doc_total(self):
        """
        Get the total number of documents in the index
        """
        cached_doc_total = self.document_cache.read_doc_total()
        if cached_doc_total is not None:
            return cached_doc_total

        # Read from metadata
        doc_total = self.biothings.metadata.biothing_metadata[self.biothings.config.ES_DOC_TYPE]["stats"]["total"]

        # Read from cat.count()
        # client = self.biothings.elasticsearch.async_client
        # index = self.biothings.config.ES_INDEX  # e.g. "semmeddb_20210831_okplrch8" or "pending-semmeddb"
        # resp = await client.cat.count(index=index, params={"format": "json"})
        # count = int(resp[0]["count"])  # I cannot understand why resp[0]["count"] somehow is a string...

        self.document_cache.write_doc_total(doc_total)

        return doc_total

    async def _prepare_stats(self, term_x: str, term_y: str):
        """
        To find the Normalized Google Distance between term_x and term_y, 4 queries are going to be performed:

        1. Query for the document frequency of term_x, which translates to counting       `subject.umls:<term_x> OR object.umls:<term_x>`
        2. Query for the document frequency of term_y, which translates to counting `subject.umls:<term_y> OR object.umls:<term_y>`
        3. Query for the document frequency of term_x and term_y together, which translates to counting `(subject.umls:<term_x> AND object.umls:<term_y>) OR (subject.umls:<term_y> AND object.umls:<term_x>)`
        4. Query for the total number of documents
        """
        f_x = await self.unary_doc_freq(term_x)
        if f_x == 0:
            raise NGDZeroCountException(term=term_x)

        f_y = await self.unary_doc_freq(term_y)
        if f_y == 0:
            raise NGDZeroCountException(term=term_y)

        f_xy = await self.bipartite_doc_freq(term_x, term_y)
        if f_xy == 0:
            raise NGDInfinityException()

        n = await self.doc_total()
        return f_x, f_y, f_xy, n

    async def calculate_ngd(self, term_x: str, term_y: str):
        cached_distance = self.distance_cache.read_distance(term_x, term_y)
        if cached_distance is not None:
            return cached_distance

        try:
            f_x, f_y, f_xy, n = await self._prepare_stats(term_x, term_y)
        except NGDZeroCountException as zce:
            raise NGDUndefinedException(cause=zce)
        except NGDInfinityException:
            distance = INFINITY_STR
        else:
            distance = normalized_google_distance(n=n, f_x=f_x, f_y=f_y, f_xy=f_xy)

        # Do not wrap the below 2 lines in `finally`,
        # otherwise they will execute even when an NGDUndefinedException is raised.
        self.distance_cache.write_distance(term_x, term_y, distance)
        return distance
