from abc import ABC, abstractmethod
from typing import Union

from elasticsearch import AsyncElasticsearch
from elasticsearch_dsl import Search, Q
from elasticsearch_dsl.query import Match

from ..utils import LRUCache
from ..utils import normalized_google_distance, INFINITY_STR, NGDZeroCountException, NGDInfinityException, NGDUndefinedException


class CacheKeyable(ABC):
    @property
    @abstractmethod
    def cache_key(self):
        return NotImplementedError


class Expandable:
    def __init__(self, expanded=False):
        self.expanded = expanded

    def mark_as_expanded(self):
        self.expanded = True

    @property
    def has_expanded(self):
        return self.expanded


class Term(Expandable, CacheKeyable):
    def __init__(self, root: str):
        # call Expandable.__init__(self)
        # Assuming self.mro() is Term -> Expandable -> CacheKeyable
        super(Term, self).__init__()

        self.root = root
        self.leaves = None

    def expand(self, leaves):
        """
        Add leaf terms to the root term, making a star graph of terms.
        """
        self.leaves = leaves
        self.mark_as_expanded()

    def all_string_terms_within(self):
        yield self.root

        if self.leaves is not None:
            yield from self.leaves

    @property
    def cache_key(self) -> str:
        if not self.has_expanded:
            return self.root

        return f"{self.root}*"


class TermPair(CacheKeyable):
    cache_key_delimiter = ","

    def __init__(self, term_x: Term, term_y: Term):
        self.pair = tuple([term_x, term_y])

    @property
    def cache_key(self) -> str:
        keys = [self.pair[0].cache_key, self.pair[1].cache_key]
        keys.sort()  # in-place operation
        return self.cache_key_delimiter.join(keys)

    def __getitem__(self, index) -> Term:
        return self.pair[index]

    def __iter__(self):
        return iter(self.pair)


class DocStatsService:
    def __init__(self, es_async_client: AsyncElasticsearch, es_index_name: str,
                 subject_field_name: str, object_field_name: str, doc_total: int):
        self.es_async_client = es_async_client
        self.es_index_name = es_index_name  # e.g. "semmeddb_20210831_okplrch8" or "pending-semmeddb"

        # Note that only {"type": "keyword"} fields are supported for NGD calculation
        # (since we are going to use ES "terms" filter)
        self.subject_field_name = subject_field_name  # e.g. "subject.umls"
        self.object_field_name = object_field_name  # e.g. "object.umls"

        # Handler can access the total number of documents easily from the API"s metadata
        # so we choose to let the handler"s intance to initialize this value.
        self.doc_total = doc_total

    async def _count_in_es(self, search: Search) -> int:
        resp = await self.es_async_client.count(body=search.to_dict(), index=self.es_index_name)
        count = resp["count"]
        return count

    def _unary_search(self, term: Term) -> Search:
        """
        Make an unary Search object with `terms` filter. The returned Search object is equivalent to

        {
            "query": {
                "bool": {
                    "filter": [
                        {
                            "bool": {
                                "should": [
                                    {
                                        "terms": {
                                            "subject.umls": [ <all_terms> ]
                                        }
                                    },
                                    {
                                        "terms": {
                                            "object.umls": [ <all_terms> ]
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
        """
        all_terms = list(term.all_string_terms_within())
        _filter = Q("terms", **{self.subject_field_name: all_terms}) | Q("terms", **{self.object_field_name: all_terms})
        search = Search().query("bool", filter=_filter)
        return search

    async def unary_doc_freq(self, term: Term) -> int:
        """
        Get the document frequency of all terms within the `term` object (i.e. count of the union of the documents containing any of the term within).
        """
        search = self._unary_search(term)
        count = await self._count_in_es(search)
        return count

    def _bipartite_match(self, term_pair: TermPair) -> Match:
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
                                                {
                                                    "terms": {
                                                        "subject.umls": [ <all_terms_x> ]
                                                    }
                                                },
                                                {
                                                    "terms": {
                                                        "object.umls": [ <all_terms_y> ]
                                                    }
                                                }
                                            ]
                                        }
                                    },
                                    {
                                        "bool": {
                                            "must": [
                                                {
                                                    "terms": {
                                                        "subject.umls": [ <all_terms_y> ]
                                                    }
                                                },
                                                {
                                                    "terms": {
                                                        "object.umls": [ <all_terms_x> ]
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
        """
        all_terms_x = list(term_pair[0].all_string_terms_within())
        all_terms_y = list(term_pair[1].all_string_terms_within())

        filter_xy = Q("terms", **{self.subject_field_name: all_terms_x}) & Q("terms", **{self.object_field_name: all_terms_y})
        filter_yx = Q("terms", **{self.subject_field_name: all_terms_y}) & Q("terms", **{self.object_field_name: all_terms_x})

        search = Search().query("bool", filter=filter_xy | filter_yx)
        return search

    async def bipartite_doc_freq(self, term_pair: TermPair) -> int:
        """
        Get the document frequency of all the term combinations within the term_pair object
        (i.e. count of the union of the documents containing any pair of terms within).
        """
        search = self._bipartite_match(term_pair)
        count = await self._count_in_es(search)
        return count


class NGDCache:
    """
    A cache class to store the normalized google distance.
    """
    def __init__(self, capacity):
        self.distance_cache = LRUCache(capacity)

    def read_distance(self, key) -> Union[float, str]:  # could a float value or the INFINITY_STR string
        return self.distance_cache.get(key)

    def write_distance(self, key, distance: Union[float, str]):
        self.distance_cache.put(key, distance)


class DocStatsCache:
    """
    A cache class to store the document frequencies.
    Two LRU caches are used internally, one for unary, the other for bipartite
    """
    def __init__(self, unary_capacity, bipartite_capacity):
        self.unary_cache = LRUCache(unary_capacity)
        self.bipartite_cache = LRUCache(bipartite_capacity)

    def read_unary_doc_freq(self, key) -> int:
        return self.unary_cache.get(key)

    def read_bipartite_doc_freq(self, key) -> int:
        return self.bipartite_cache.get(key)

    def write_unary_doc_freq(self, key, doc_freq: int):
        self.unary_cache.put(key, doc_freq)

    def write_bipartite_doc_freq(self, key, doc_freq: int):
        self.bipartite_cache.put(key, doc_freq)


class NGDService:
    def __init__(self, doc_stats_service: DocStatsService, doc_stats_cache: DocStatsCache, ngd_cache: NGDCache):
        self.doc_stats_service = doc_stats_service

        self.doc_stats_cache = doc_stats_cache
        self.ngd_cache = ngd_cache

    async def unary_doc_freq(self, term: Term, read_cache=True):
        if read_cache:
            cached_doc_freq = self.doc_stats_cache.read_unary_doc_freq(term.cache_key)
            if cached_doc_freq is not None:
                return cached_doc_freq

        doc_freq = await self.doc_stats_service.unary_doc_freq(term)
        self.doc_stats_cache.write_unary_doc_freq(term.cache_key, doc_freq)

        return doc_freq

    async def bipartite_doc_freq(self, term_pair: TermPair, read_cache=True):
        cache_key = term_pair.cache_key

        if read_cache:
            cached_doc_freq = self.doc_stats_cache.read_bipartite_doc_freq(cache_key)
            if cached_doc_freq is not None:
                return cached_doc_freq

        doc_freq = await self.doc_stats_service.bipartite_doc_freq(term_pair)

        self.doc_stats_cache.write_bipartite_doc_freq(cache_key, doc_freq)

        return doc_freq

    async def doc_total(self):
        """
        Get the total number of documents in the index. This value will not be cached since it will be saved as an attribute of self.doc_stats_service.
        """
        return self.doc_stats_service.doc_total

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
            raise NGDZeroCountException(term=term_x)

        f_y = await self.unary_doc_freq(term_y)
        if f_y == 0:
            raise NGDZeroCountException(term=term_y)

        f_xy = await self.bipartite_doc_freq(term_pair)
        if f_xy == 0:
            raise NGDInfinityException()

        n = await self.doc_total()
        return f_x, f_y, f_xy, n

    async def calculate_ngd(self, term_pair: TermPair, read_cache=True):
        cache_key = term_pair.cache_key

        if read_cache:
            cached_distance = self.ngd_cache.read_distance(cache_key)
            if cached_distance is not None:
                return cached_distance

        try:
            f_x, f_y, f_xy, n = await self._prepare_stats(term_pair)
        except NGDZeroCountException as zce:
            raise NGDUndefinedException(cause=zce)
        except NGDInfinityException:
            distance = INFINITY_STR
        else:
            distance = normalized_google_distance(n=n, f_x=f_x, f_y=f_y, f_xy=f_xy)

        # Do not wrap the below 2 lines in `finally`,
        # otherwise they will execute even when an NGDUndefinedException is raised.
        self.ngd_cache.write_distance(cache_key, distance)
        return distance
