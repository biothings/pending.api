from biothings.utils.web.es_dsl import AsyncSearch
from biothings.web.pipeline import ESQueryBuilder


class PendingQueryBuilder(ESQueryBuilder):
    '''
    Allow direct search with class name or partial match
    '''

    # currently not in use
    pass