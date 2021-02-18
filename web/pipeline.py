from biothings.utils.common import dotdict, traverse
from biothings.utils.web.es_dsl import AsyncSearch, AsyncMultiSearch
from biothings.web.pipeline import ESQueryBuilder

from web.graph import GraphObject, GraphQuery, GraphQueries


class PendingQueryBuilder(ESQueryBuilder):

    def build(self, q, options):

        # NOTE
        # GRAPH QUERY CUSTOMIZATION

        # ONE
        if isinstance(q, GraphQuery):
            return self.build_graph_query(q, options)

        # MULTI
        elif isinstance(q, GraphQueries):
            search = AsyncMultiSearch()
            for _q in q:
                search = search.add(self.build_graph_query(_q, options))
            return search

        else:  # NOT GRAPH
            return super().build(q, options)

    def build_graph_query(self, q, options):

        query = self._build_graph_query(q)

        if options.reverse and q.reversible():
            q.reverse()
            query = query | self._build_graph_query(q)

        return AsyncSearch().query(query)

    def _build_graph_query(self, graph_query):
        """
        Takes a GraphQuery object and return an ES Query object.
        """
        assert isinstance(graph_query, GraphQuery)
        q = graph_query.to_dict()

        _q = []
        _scopes = []

        for k, v in traverse(q, True):
            if isinstance(v, list):
                for _v in v:
                    _q.append(_v)
                    _scopes.append(k)
            else:
                _q.append(v)
                _scopes.append(k)

        return self.default_match_query(_q, _scopes, dotdict()).query._proxied
