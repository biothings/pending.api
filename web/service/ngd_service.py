from typing import Union, List
from abc import ABC, abstractmethod

from elasticsearch import AsyncElasticsearch
from elasticsearch_dsl import Search, Q, A

from web.utils import LRUCache
from web.utils import normalized_google_distance, INFINITY_STR, NGDZeroDocFreqException, NGDInfinityException


class CacheKeyable:
    def __init__(self, cache_key):
        self._cache_key = cache_key

    @property
    def cache_key(self):
        return self._cache_key


class Term(CacheKeyable):
    def __init__(self, root: str, expandable: bool):
        self._root = root
        self._leaves = None
        self._expandable = expandable
        self._expanded = False

        cache_key = f"{self._root}*" if self._expandable else self._root
        super(Term, self).__init__(cache_key)  # call CacheKeyable.__init__(cache_key)

    @property
    def root(self):
        return self._root

    @property
    def leaves(self):
        if not self._expandable:
            raise ValueError(f"Term {self._root} has no leaves since it is not expandable.")

        if not self._expanded:
            raise ValueError(f"Term {self._root} has no leaves since it is not expanded yet.")

        return self._leaves

    @property
    def expandable(self):
        return self._expandable

    @property
    def expanded(self):
        return self._expanded

    def expand(self, leaves):
        """
        Expand the current term by adding associated leaf-terms
        """
        if not self._expandable:
            raise ValueError(f"Term {self._root} is not expandable.")

        self._leaves = leaves
        self._expanded = True

    def all_string_terms_within(self):
        yield self._root

        if self._expandable and self._expanded:
            if self._leaves:
                yield from self._leaves


class TermPair(CacheKeyable):
    cache_key_delimiter = ","

    def __init__(self, term_x: Term, term_y: Term):
        self.pair = tuple([term_x, term_y])

        term_keys = [self.pair[0].cache_key, self.pair[1].cache_key]
        term_keys.sort()  # in-place operation
        pair_key = self.cache_key_delimiter.join(term_keys)
        super(TermPair, self).__init__(pair_key)  # call CacheKeyable.__init__(cache_key)

    def __getitem__(self, index) -> Term:
        return self.pair[index]

    def __iter__(self):
        return iter(self.pair)


class TermExpansionService(ABC):
    @abstractmethod
    def expand(self, term: str) -> List[str]:
        """
        Expand from the input term, returning all associated terms in a list
        """
        raise NotImplementedError


class DocStatsService:
    def __init__(
        self,
        es_async_client: AsyncElasticsearch,
        es_index_name: str,
        subject_field_name: str,
        object_field_name: str,
        doc_freq_agg_name: str,
    ):
        # SemmedNGDHandler will receive configuration values from config_web/xxx.py, and initialize DocStatsService accordingly
        self.es_async_client = es_async_client
        self.es_index_name = es_index_name  # e.g. "semmeddb_20210831_okplrch8" or "pending-semmeddb" (from `ES_INDEX` in config_web/xxx.py)
        self.subject_field_name = subject_field_name  # e.g. "subject.umls"
        self.object_field_name = object_field_name  # e.g. "object.umls"
        self.doc_freq_agg_name = doc_freq_agg_name  # e.g. "sum_of_predication_counts"

    async def _query_doc_freq_in_es(self, search: Search) -> int:
        """
        Query the search object to ES and parse the aggregation value in the response as the document frequency.

        The response structure is like:

            {
                'took': 2,
                'timed_out': False,
                '_shards': {'total': 1, 'successful': 1, 'skipped': 0, 'failed': 0},
                'hits': {
                    'total': {'value': 10000, 'relation': 'gte'},
                    'max_score': None,
                    'hits': []
                },
                'aggregations': {
                    '<agg_name>': {'value': 89340012.0}
                }
            }
        """
        resp = await self.es_async_client.search(body=search.to_dict(), index=self.es_index_name)

        if "aggregations" not in resp:
            raise ValueError(
                f"No aggregation result in response. Got {search.to_dict()} to index {self.es_index_name}, response being {resp}"
            )
        doc_freq = resp["aggregations"][self.doc_freq_agg_name]["value"]
        return int(doc_freq)  # ES will return this aggregation value as a float; convert to int here

    def _unary_search(self, term: Term) -> Search:
        """
        Make a unary Search object with `terms` filter. The returned Search object is equivalent to

        {
            "query": {
                "bool": {
                    "filter": [
                        {
                            "bool": {
                                "should": [
                                    { "terms": { "subject.umls": [ <all_terms> ] } },
                                    { "terms": { "object.umls": [ <all_terms> ] } }
                                ]
                            }
                        }
                    ]
                }
            },
            "aggs": { <doc_freq_agg_name>: { "sum": { "field": "predication_count" } } },
            "size": 0
        }
        """
        all_terms = list(term.all_string_terms_within())
        _filter = Q("terms", **{self.subject_field_name: all_terms}) | Q("terms", **{self.object_field_name: all_terms})
        # size=0 means the query result will include 0 hits (so only the aggregation value will be returned)
        search = Search().query("bool", filter=_filter).extra(size=0)

        _agg = A("sum", field="predication_count")
        search.aggs.metric(self.doc_freq_agg_name, _agg)  # attach the aggregation with its name to the search object
        return search

    async def unary_doc_freq(self, term: Term) -> int:
        """
        Get the document frequency of all terms within the `term` object (i.e. count of the union of the documents containing any of the term within).
        """
        search = self._unary_search(term)
        doc_freq = await self._query_doc_freq_in_es(search)
        return doc_freq

    def _bipartite_search(self, term_pair: TermPair) -> Search:
        """
        Make a bipartite Search object with `terms` filter. The returned Search object is equivalent to

        {
            "query": {
                "bool": {
                    "filter": [
                        {
                            "bool": {
                                "should": [
                                    {
                                        "bool": {
                                            "must": [
                                                { "terms": { "subject.umls": [ <all_terms_x> ] } },
                                                { "terms": { "object.umls": [ <all_terms_y> ] } }
                                            ]
                                        }
                                    },
                                    {
                                        "bool": {
                                            "must": [
                                                { "terms": { "subject.umls": [ <all_terms_y> ] } },
                                                { "terms": { "object.umls": [ <all_terms_x> ] } }
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            },
            "aggs": { <doc_freq_agg_name>: { "sum": { "field": "predication_count" } } },
            "size": 0
        }
        """
        all_terms_x = list(term_pair[0].all_string_terms_within())
        all_terms_y = list(term_pair[1].all_string_terms_within())
        filter_xy = Q("terms", **{self.subject_field_name: all_terms_x}) & Q(
            "terms", **{self.object_field_name: all_terms_y}
        )
        filter_yx = Q("terms", **{self.subject_field_name: all_terms_y}) & Q(
            "terms", **{self.object_field_name: all_terms_x}
        )
        # size=0 means the query result will include 0 hits (so only the aggregation value will be returned)
        search = Search().query("bool", filter=filter_xy | filter_yx).extra(size=0)

        _agg = A("sum", field="predication_count")
        search.aggs.metric(self.doc_freq_agg_name, _agg)  # attach the aggregation with its name to the search object
        return search

    async def bipartite_doc_freq(self, term_pair: TermPair) -> int:
        """
        Get the document frequency of all the term combinations within the term_pair object
        (i.e. count of the union of the documents containing any pair of terms within).
        """
        search = self._bipartite_search(term_pair)
        doc_freq = await self._query_doc_freq_in_es(search)
        return doc_freq

    async def doc_total(self) -> int:
        # This search is essentially a doc_freq search without any filter on terms
        search = Search().extra(size=0)
        _agg = A("sum", field="predication_count")
        search.aggs.metric(self.doc_freq_agg_name, _agg)
        total = await self._query_doc_freq_in_es(search)
        return total


class NGDCache:
    """
    A cache class to store the normalized Google distance.
    """

    def __init__(self, capacity):
        self.distance_cache = LRUCache(capacity)

    def read_distance(self, key) -> Union[float, str]:  # could a float value or the INFINITY_STR string
        return self.distance_cache.get(key)

    def write_distance(self, key, distance: Union[float, str]):
        self.distance_cache.put(key, distance)


class DocStatsCache:
    """
    A cache class to store the document frequencies, which include:

    1. An integer cache for total number of docs.
    2. An LRU cache for unary doc frequencies.
    3. An LRU cache for bipartite doc frequencies.
    """

    def __init__(self, unary_capacity, bipartite_capacity):
        self.total_cache: int = None

        self.unary_cache = LRUCache(unary_capacity)
        self.bipartite_cache = LRUCache(bipartite_capacity)

    def read_doc_total(self):
        return self.total_cache

    def write_doc_total(self, total):
        self.total_cache = total

    def read_unary_doc_freq(self, key) -> int:
        return self.unary_cache.get(key)

    def read_bipartite_doc_freq(self, key) -> int:
        return self.bipartite_cache.get(key)

    def write_unary_doc_freq(self, key, doc_freq: int):
        self.unary_cache.put(key, doc_freq)

    def write_bipartite_doc_freq(self, key, doc_freq: int):
        self.bipartite_cache.put(key, doc_freq)


class NGDService:
    def __init__(
        self,
        doc_stats_service: DocStatsService,
        term_expansion_service: TermExpansionService,
        doc_stats_cache: DocStatsCache,
        ngd_cache: NGDCache,
    ):
        self.doc_stats_service = doc_stats_service
        self.term_expansion_service = term_expansion_service

        self.doc_stats_cache = doc_stats_cache
        self.ngd_cache = ngd_cache

    def expand_term(self, term: Term):
        if term.expandable and (not term.expanded):
            leaves = self.term_expansion_service.expand(term.root)
            term.expand(leaves)

    def expand_term_pair(self, term_pair: TermPair):
        for term in term_pair:
            self.expand_term(term)

    async def unary_doc_freq(self, term: Term, read_cache=True):
        if read_cache:
            cached_doc_freq = self.doc_stats_cache.read_unary_doc_freq(term.cache_key)
            if cached_doc_freq is not None:
                return cached_doc_freq

        self.expand_term(term)
        doc_freq = await self.doc_stats_service.unary_doc_freq(term)
        self.doc_stats_cache.write_unary_doc_freq(term.cache_key, doc_freq)

        return doc_freq

    async def bipartite_doc_freq(self, term_pair: TermPair, read_cache=True):
        if read_cache:
            cached_doc_freq = self.doc_stats_cache.read_bipartite_doc_freq(term_pair.cache_key)
            if cached_doc_freq is not None:
                return cached_doc_freq

        self.expand_term_pair(term_pair)
        doc_freq = await self.doc_stats_service.bipartite_doc_freq(term_pair)
        self.doc_stats_cache.write_bipartite_doc_freq(term_pair.cache_key, doc_freq)

        return doc_freq

    async def doc_total(self, read_cache=True):
        """
        Get the total number of documents in the index. This value will be cached, otherwise a query to self.doc_stats_service will be made to init this value.
        """
        if read_cache:
            cached_total = self.doc_stats_cache.read_doc_total()
            if cached_total is not None:
                return cached_total

        total = await self.doc_stats_service.doc_total()
        self.doc_stats_cache.write_doc_total(total)

        return total

    async def _prepare_stats(self, term_pair: TermPair):
        """
        Return the following 4 values for Normalized Google Distance calculation.

        1. unary document frequency of term_x
        2. unary document frequency of term_y
        3. bipartite document frequency of term_x and term_y together
        4. total number of documents
        """

        term_x, term_y = term_pair[0], term_pair[1]

        f_x = await self.unary_doc_freq(term_x)
        if f_x == 0:
            raise NGDZeroDocFreqException(term=term_x)

        f_y = await self.unary_doc_freq(term_y)
        if f_y == 0:
            raise NGDZeroDocFreqException(term=term_y)

        f_xy = await self.bipartite_doc_freq(term_pair)
        if f_xy == 0:
            raise NGDInfinityException()

        n = await self.doc_total()
        return f_x, f_y, f_xy, n

    async def calculate_ngd(self, term_pair: TermPair, read_cache=True):
        if read_cache:
            cached_distance = self.ngd_cache.read_distance(term_pair.cache_key)
            if cached_distance is not None:
                return cached_distance

        try:
            f_x, f_y, f_xy, n = await self._prepare_stats(term_pair)
        except NGDZeroDocFreqException as e:
            raise e
        except NGDInfinityException:
            distance = INFINITY_STR
        else:
            distance = normalized_google_distance(n=n, f_x=f_x, f_y=f_y, f_xy=f_xy)

        # Do not wrap the below 2 lines in `finally`,
        # otherwise they will execute even when an NGDUndefinedException is raised.
        self.ngd_cache.write_distance(term_pair.cache_key, distance)
        return distance
