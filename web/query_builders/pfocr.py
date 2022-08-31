from biothings.web.query import ESQueryBuilder
from elasticsearch_dsl.query import MultiMatch
from elasticsearch_dsl import Search


class PfocrQueryBuilder(ESQueryBuilder):
    def default_match_query(self, q, scopes, options):
        """
        Override the default match query.

        Original behavior in ESQueryBuilder is:

        assert isinstance(q, (str, int, float, bool))
        assert isinstance(scopes, (list, tuple, str)) and scopes
        return Search().query(
            'multi_match', query=q, fields=scopes,
            operator="and", lenient=True
        )
        """
        # For `minimum_should_match` queries, both should be strings
        # E.g. q = "5601 5595 10189 10333"
        # E.g. scopes = "associatedWith.mentions.genes.ncbigene"
        assert isinstance(q, (str, int, float, bool))
        assert isinstance(scopes, (list, tuple, str)) and scopes

        # 3 default params
        _params = {
            "fields": scopes,
            "operator": "AND",
            "lenient": True
        }

        # preserve the default params if no option is passed in
        if options.operator:
            _params["operator"] = options.operator
        if options.analyzer:
            _params["analyzer"] = options.analyzer
        if options.minimum_should_match:
            _params["minimum_should_match"] = options.minimum_should_match

        multi_match = MultiMatch(query=q, **_params)
        search = Search().query(multi_match)
        return search
