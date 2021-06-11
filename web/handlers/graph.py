"""

Biothings Enhanced Graph Query Support
https://github.com/biothings/pending.api/issues/20

"""

import copy
from collections import UserList

from biothings.utils.common import dotdict
from biothings.web.handlers import ESRequestHandler
from biothings.web.handlers.exceptions import BadRequest
from biothings.web.settings.default import COMMON_KWARGS, QUERY_KWARGS
from tornado.web import HTTPError
from web.graph import GraphObject, GraphQueries, GraphQuery


class GraphQueryHandler(ESRequestHandler):

    name = "graph"
    kwargs = {"*": copy.deepcopy(COMMON_KWARGS)}
    kwargs["*"]["reverse"] = {"type": bool, "default": False, "group": "esqb"}
    kwargs["*"]["reversed"] = {"type": bool, "default": True, "group": "transform"}

    def pre_query_builder_hook(self, options):

        options.es.biothing_type = self.biothing_type
        options.transform.biothing_type = self.biothing_type

        if isinstance(self.args_json, dict):
            q = GraphQuery.from_dict(self.args_json)
        elif isinstance(self.args_json, list):
            q = GraphQueries(GraphQuery.from_dict(_q) for _q in self.args_json)
        else:
            raise HTTPError(400)

        options.esqb.q = q
        options.transform.q = q
        options.transform.reverse = options.esqb.reverse

        # define multi-query response format
        if isinstance(options.esqb.q, (list, UserList)):
            queries = options.esqb.q
            options.transform.templates = (dict(query=q.to_dict()) for q in queries)
            options.transform.template_miss = dict(notfound=True)
            options.transform.template_hit = dict()

        return options
