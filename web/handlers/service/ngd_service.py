from elasticsearch import AsyncElasticsearch
from elasticsearch_dsl import Search, Q


class NGDService:
    def __init__(self, es_async_client: AsyncElasticsearch, es_index_name: str):
        self.es_async_client = es_async_client
        self.es_index_name = es_index_name  # e.g. "semmeddb_20210831_okplrch8" or "pending-semmeddb"

    async def count_one_term(self, term: str):
        match = Q("match", subject__umls=term) | Q("match", object__umls=term)  # boolean OR match
        query = Search().query(match)

        """
        Here we use the ES DSL data structures.
        So the above `match` and `query` is equivalent to the following query conditions:

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

        Why did we choose not to use `Search(using=client, index=index).query(match).count()`?
        Because elasticsearch-dsl is not compatible with async elasticsearch client yet.
        """
        resp = await self.es_async_client.count(body=query.to_dict(), index=self.es_index_name)
        count = resp["count"]

        return count

    async def count_two_terms(self, term_x: str, term_y: str):
        match = (Q("match", subject__umls=term_x) & Q("match", object__umls=term_y)) | \
                (Q("match", subject__umls=term_y) & Q("match", object__umls=term_x))
        query = Search().query(match)

        """
        This `query` can be understood as:

            (subject.umls:<term_x> AND object.umls:<term_y>) OR
            (subject.umls:<term_y> AND object.umls:<term_x>)
        """
        resp = await self.es_async_client.count(body=query.to_dict(), index=self.es_index_name)
        count = resp["count"]

        return count

    