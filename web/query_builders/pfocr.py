from biothings.web.query import ESQueryBuilder
from elasticsearch_dsl.query import MultiMatch
from elasticsearch_dsl import Search


class PfocrQueryBuilder(ESQueryBuilder):
    def default_match_query(self, q, scopes, options):
        # E.g. q = "5601 5595 10189 10333"
        # E.g. scopes = "associatedWith.mentions.genes.ncbigene"
        assert isinstance(q, str)
        assert isinstance(scopes, (str, list)) and scopes

        operator = "OR"  # defaults to "OR"; should be "OR" here
        lenient = True  # defaults to False; should be True here
        analyzer = options.analyzer  # should be "whitespace"
        minimum_should_match = options.minimum_should_match  # should be a positive integer

        multi_match = MultiMatch(query=q, fields=scopes, operator=operator, lenient=lenient, analyzer=analyzer,
                                 minimum_should_match=minimum_should_match)
        search = Search().query(multi_match)
        return search
