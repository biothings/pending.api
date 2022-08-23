from abc import ABCMeta, abstractmethod
from typing import Iterable, Union
from functools import reduce  # to concat multiple elasticsearch_dsl.query.Match objects into one
from operator import or_  # for OR operation on elasticsearch_dsl.query.Match objects
from itertools import product

from elasticsearch import AsyncElasticsearch
from elasticsearch_dsl import Search, Q
from elasticsearch_dsl.query import Match

from ..utils import LRUCache
from ..utils import normalized_google_distance, INFINITY_STR, NGDZeroCountException, NGDInfinityException, NGDUndefinedException


class CacheKeyable(metaclass=ABCMeta):
    @property
    @abstractmethod
    def cache_key(self):
        return NotImplementedError

class Term(CacheKeyable):
    def __init__(self, root: str):
        self.root = root
        self.leaves = None

        """
        A root term with leaf terms scattered around makes a star graph of terms. 
        See https://en.wikipedia.org/wiki/Star_(graph_theory).

        By setting star_graph_mark, we indicate this object is not a single string term but a potential star graph of terms.
        """
        self.star_graph_mark = False

    def make_star_graph(self, leaves):
        """
        Add leaf terms to the root term, making a star graph of terms.
        """
        self.leaves = leaves
        self.star_graph_mark = True

    def all_string_terms_within(self):
        yield self.root

        if self.leaves is not None:
            yield from self.leaves

    @property
    def cache_key(self) -> str:
        if not self.star_graph_mark:
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

    def all_string_term_pairs_within(self) -> Iterable[tuple]:
        yield from product(self.pair[0].all_string_terms_within(), self.pair[1].all_string_terms_within())


class _BasicDocStatsService:
    def __init__(self, es_async_client: AsyncElasticsearch, es_index_name: str,
                 subject_field_name: str, object_field_name: str):
        self.es_async_client = es_async_client
        self.es_index_name = es_index_name  # e.g. "semmeddb_20210831_okplrch8" or "pending-semmeddb"

        self.subject_field_name = subject_field_name  # e.g. "subject.umls"
        self.object_field_name = object_field_name  # e.g. "object.umls"

    def _unary_match(self, term: str) -> Match:
        """
        Construct a elasticsearch_dsl Match object from a single term.
        """

        """
        This is boolean OR match, as explained below

            match.to_dict() => {
                'bool': {
                    'should': [
                        {'match': {<subject_field_name>: <term>}},
                        {'match': {<object_field_name>: <term>}}
                    ]
                }
            }

        Then Search().query(match) can expand like:

            Search().query(match).to_dict() => {
                'query': {
                    'bool': {
                        'should': [
                            {'match': {<subject_field_name>: <term>}},
                            {'match': {<object_field_name>: <term>}}
                        ]
                    }
                }
            }
        """
        # The Q() function returns an instance of elasticsearch_dsl.query.Match
        match = Q("match", **{self.subject_field_name: term}) | Q("match", **{self.object_field_name: term})
        return match

    # This is the two-term version of function `_unary_match`.
    # Could have be named `_binary_match` but I think it's kind of ambiguous (may relate to "binary search")
    def _bipartite_match(self, term_x: str, term_y: str) -> Match:
        """
        Construct a elasticsearch_dsl Match object from two terms.
        """

        """
        This Match object can be understood as:

            (subject.umls:<term_x> AND object.umls:<term_y>) OR
            (subject.umls:<term_y> AND object.umls:<term_x>)
        """
        # The Q() function returns an instance of elasticsearch_dsl.query.Match
        match = (Q("match", **{self.subject_field_name: term_x}) & Q("match", **{self.object_field_name: term_y})) | \
                (Q("match", **{self.subject_field_name: term_y}) & Q("match", **{self.object_field_name: term_x}))
        return match

    async def _count_in_es(self, match: Match) -> int:
        # You might wonder why not `Search(using=client, index=index).query(match).count()` here?
        # Because elasticsearch-dsl is not compatible with async elasticsearch client yet.
        search = Search().query(match)
        resp = await self.es_async_client.count(body=search.to_dict(), index=self.es_index_name)
        count = resp["count"]
        return count

    # # CAUTION: `search()` will return the TOP 10 records by default. Add scroll_id to return all records
    # async def _search_id_in_es(self, match: Match) -> Set:
    #     search = Search().query(match).source(False)
    #     resp = await self.es_async_client.search(body=search.to_dict(), index=self.es_index_name)
    #     id_set = set(hit["_id"] for hit in resp["hits"]["hits"])
    #     return id_set

    async def unary_doc_freq(self, term: str) -> int:
        """
        Get the document frequency of a single term (i.e. count of documents containing the term).
        """
        match = self._unary_match(term)
        count = await self._count_in_es(match)
        return count

    async def bipartite_doc_freq(self, term_x: str, term_y: str):
        """
        Get the document frequency of paried terms (i.e. count of documents containing both terms)
        """
        match = self._bipartite_match(term_x, term_y)
        count = await self._count_in_es(match)
        return count


class DocStatsService:
    def __init__(self, es_async_client: AsyncElasticsearch, es_index_name: str,
                 subject_field_name: str, object_field_name: str, doc_total: int):
        self.es_async_client = es_async_client
        self.es_index_name = es_index_name  # e.g. "semmeddb_20210831_okplrch8" or "pending-semmeddb"
        self.subject_field_name = subject_field_name  # e.g. "subject.umls"
        self.object_field_name = object_field_name  # e.g. "object.umls"
        self.agent = _BasicDocStatsService(es_async_client, es_index_name, subject_field_name, object_field_name)

        # Handler can access the total number of documents easily from the API's metadata
        # so we choose to let the handler's intance to initialize this value.
        self.doc_total = doc_total

    async def _count_in_es(self, match: Match) -> int:
        count = await self.agent._count_in_es(match)
        return count

    def _unary_match(self, term: Term) -> Match:
        """
        For each single term within the `term` object, make a unary Match object. Then chain them up with logical OR operators.
        """
        # `or_` is the bitwise OR opeartor in python (as in `True or False`)
        # but it works as a logical OR operator for Match objects
        matches = (self.agent._unary_match(term) for term in term.all_string_terms_within())
        chained_match = reduce(or_, matches)
        return chained_match

    async def unary_doc_freq(self, term: Term) -> int:
        """
        Get the document frequency of all terms within the `term` object (i.e. count of the union of the documents containing any of the term within).

        I.e. given D(t) the set of documents containing term t, the group document frequency of {t1,t2,t3,...,tn} is the size of union{D(t1),D(t2),...,D(tn)}
        """
        match = self._unary_match(term)
        count = await self._count_in_es(match)
        return count

    def _bipartite_match(self, term_pair: TermPair) -> Match:
        str_term_pairs = term_pair.all_string_term_pairs_within()
        matches = (self.agent._bipartite_match(term_x, term_y) for (term_x, term_y) in str_term_pairs)
        chained_match = reduce(or_, matches)
        return chained_match

    async def bipartite_doc_freq(self, term_pair: TermPair) -> int:
        """
        Get the document frequency of all the term combinations within the term_pair object (i.e. count of the union of the documents containing any pair of terms within).
        """
        match = self._bipartite_match(term_pair)
        count = await self._count_in_es(match)
        return count


class NGDCache:
    """
    A cache class to store the normalized google distance.
    The primary key is two term tuples.
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
    Two LRU caches are used internally, one for single-term document frequencies, the other for double-term ones
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
        term_x, term_y = term_pair[0], term_pair[1]

        """
        To find the Normalized Google Distance between term_x and term_y, 4 queries are going to be performed:

        1. Query for the document frequency of term_x, which translates to counting `subject.umls:<term_x> OR object.umls:<term_x>`
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
