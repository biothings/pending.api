import re

from biothings.web.query import ESQueryBuilder
from elasticsearch_dsl import Q, Search
from elasticsearch_dsl.query import MultiMatch


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
        _params = {"fields": scopes, "operator": "AND", "lenient": True}

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

class OntologyQueryBuilder(ESQueryBuilder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ontology = self._extract_ontology(args)

    def _extract_ontology(self, args):
            metadata = args[6]
            indices = metadata.indices
            if indices:
                for index in indices.values():
                    match = re.search(r'pending-(\w+)', index)
                    if match:
                        return match.group(1).lower()

    def apply_extras(self, search, options):
        if options.ignore_obsolete:
            search = search.filter(~Q("term", **{f"{self.ontology}.is_obsolete": True}))
        return super().apply_extras(search, options)
