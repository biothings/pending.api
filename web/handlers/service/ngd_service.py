from elasticsearch import AsyncElasticsearch
from elasticsearch_dsl import Search, Q
from ..utils import LRUCache


class UMLSDocumentService:
    def __init__(self, es_async_client: AsyncElasticsearch, es_index_name: str):
        self.es_async_client = es_async_client
        self.es_index_name = es_index_name  # e.g. "semmeddb_20210831_okplrch8" or "pending-semmeddb"

    @classmethod
    def _unary_search(cls, term: str) -> Search:
        """
        Construct a elasticsearch_dsl Match object from a single term.
        """

        """
        This is boolean OR match, as explained below

            match.to_dict() => {
                'bool': {
                    'should': [
                        {'match': {'subject.umls': <term>}},
                        {'match': {'object.umls': <term>}}
                    ]
                }
            }

        Then Search().query(match) can expand like:

            Search().query(match).to_dict() => {
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
        # The Q() function returns an instance of elasticsearch_dsl.query.Match
        match = Q("match", subject__umls=term) | Q("match", object__umls=term)
        return Search().query(match)

    # This is the two-term version of function `_unary_search`.
    # I have to avoid naming it `_binary_search`...
    @classmethod
    def _bipartite_search(cls, term_x: str, term_y: str) -> Search:
        """
        Construct a elasticsearch_dsl Match object from two terms.
        """

        """
        This Match object can be understood as:

            (subject.umls:<term_x> AND object.umls:<term_y>) OR
            (subject.umls:<term_y> AND object.umls:<term_x>)
        """
        # The Q() function returns an instance of elasticsearch_dsl.query.Match
        match = (Q("match", subject__umls=term_x) & Q("match", object__umls=term_y)) | \
                (Q("match", subject__umls=term_y) & Q("match", object__umls=term_x))
        return Search().query(match)

    async def _count_in_es(self, search: Search):
        # You might wonder why not `Search(using=client, index=index).query(match).count()` here?
        # Because elasticsearch-dsl is not compatible with async elasticsearch client yet.
        resp = await self.es_async_client.count(body=search.to_dict(), index=self.es_index_name)
        count = resp["count"]
        return count

    async def unary_doc_freq(self, term: str):
        """
        Get the document frequency of a single term (i.e. count of documents containing the term).
        """
        search = self._unary_search(term)
        count = await self._count_in_es(search)
        return count

    async def bipartite_doc_freq(self, term_x: str, term_y: str):
        """
        Get the document frequency of two terms together (i.e. count of documents containing both terms)
        """
        search = self._bipartite_search(term_x, term_y)
        count = await self._count_in_es(search)
        return count


class NGDCache:
    """
    A cache class to store the normalized google distance.
    The primary key is two term tuples.
    """
    def __init__(self, capacity):
        self.distance_cache = LRUCache(capacity)

    def read_distance(self, term_x: str, term_y: str):
        return self.distance_cache.get((term_x, term_y))

    def write_distance(self, term_x: str, term_y: str, distance: float):
        self.distance_cache.put((term_x, term_y), distance)


class UMLSDocumentCache:
    """
    A cache class to store the document frequencies.
    Two LRU caches are used internally, one for single-term document frequencies, the other for double-term ones
    """
    def __init__(self, unary_capacity, bipartite_capacity):
        self.unary_cache = LRUCache(unary_capacity)
        self.bipartite_cache = LRUCache(bipartite_capacity)

        # total number of documents, only one number to cache
        self.doc_total = None

    def read_unary_doc_freq(self, term: str):
        return self.unary_cache.get(term)

    def read_bipartite_doc_freq(self, term_x: str, term_y: str):
        return self.bipartite_cache.get((term_x, term_y))

    def write_unary_doc_freq(self, term: str, doc_freq: int):
        self.unary_cache.put(term, doc_freq)

    def write_bipartite_doc_freq(self, term_x: str, term_y: str, doc_freq: int):
        self.bipartite_cache.put((term_x, term_y), doc_freq)

    def read_doc_total(self):
        return self.doc_total

    def write_doc_total(self, doc_total):
        self.doc_total = doc_total
