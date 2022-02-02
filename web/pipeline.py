import logging
from copy import deepcopy
from biothings.utils.common import dotdict, traverse
from biothings.web.query import ESQueryBuilder, ESResultFormatter, AsyncESQueryPipeline
from elasticsearch_dsl import MultiSearch, Search

from web.graph import GraphObject, GraphQueries, GraphQuery


class PendingQueryPipeline(AsyncESQueryPipeline):

    async def graph_search(self, q, **options):

        # result formatter will consume this
        options['_q'] = q

        # define multi-query response format
        if isinstance(q, GraphQueries):
            options['templates'] = (dict(query=_q.to_dict()) for _q in q)
            options['template_miss'] = dict(notfound=True)
            options['template_hit'] = dict()

        return await super().search(q, **options)


class PendingQueryBuilder(ESQueryBuilder):

    def build(self, q, **options):

        # NOTE
        # GRAPH QUERY CUSTOMIZATION

        # ONE
        if isinstance(q, GraphQuery):
            return self.build_graph_query(q, **options)

        # MULTI
        elif isinstance(q, GraphQueries):
            search = MultiSearch()
            for _q in q:
                search = search.add(self.build_graph_query(_q, **options))
            return search

        else:  # NOT GRAPH
            return super().build(q, **options)

    def build_graph_query(self, q, reverse=False, **options):

        query = self._build_graph_query(q)

        if reverse and q.reversible():
            _q = deepcopy(q)
            _q.reverse()
            query = query | self._build_graph_query(_q)

        search = Search().query(query) if query else Search()
        search = self.apply_extras(search, dotdict(options))

        return search

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

        # query proxy object does not support OR operator, thus using _proxied
        return self._build_match_query(_q, _scopes, dotdict()).query._proxied


class GraphResultTransform(ESResultFormatter):

    def transform_hit(self, path, doc, options):

        if path == '':

            if options.reversed and all((  # is reversed query
                options._q.predicate, options.reverse,
                options._q.predicate in options._q.PREDICATE_MAPPING
            )):
                try:
                    obj = GraphObject.from_dict(doc)
                    _predicate = options._q.PREDICATE_MAPPING[options._q.predicate]
                    reversed = obj.predicate == _predicate
                    if obj.reversible() and reversed:
                        obj.reverse()
                    doc.update(obj.to_dict())
                except Exception as exc:
                    logging.error(exc)
