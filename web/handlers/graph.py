"""

Biothings Enhanced Graph Query Support
https://github.com/biothings/pending.api/issues/20

"""

import copy

from biothings.web.handlers import BaseAPIHandler
from biothings.web.settings.default import COMMON_KWARGS
from tornado.web import HTTPError
from web.graph import GraphQueries, GraphQuery


class GraphQueryHandler(BaseAPIHandler):

    name = "graph"
    kwargs = {"*": copy.deepcopy(COMMON_KWARGS)}
    kwargs["*"].update(BaseAPIHandler.kwargs["*"])
    kwargs["*"]["reverse"] = {"type": bool, "default": False}
    kwargs["*"]["reversed"] = {"type": bool, "default": True}

    async def post(self, *args, **kwargs):

        if isinstance(self.args_json, dict):
            q = GraphQuery.from_dict(self.args_json)
        elif isinstance(self.args_json, list):
            q = GraphQueries(GraphQuery.from_dict(_q) for _q in self.args_json)
        else:
            raise HTTPError(400)

        result = await self.biothings.pipeline.graph_search(q, **self.args)
        self.finish(result)
