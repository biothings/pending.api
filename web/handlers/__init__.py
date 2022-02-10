"""
    Dynamic Web Pages
"""

import json
import logging
import types

import tornado.httpclient
import tornado.web
from jinja2 import Environment, FileSystemLoader

from biothings.web.handlers import BaseHandler

from .graph import GraphQueryHandler
from .ngd import SemmedNGDHandler

log = logging.getLogger("pending")

templateLoader = FileSystemLoader(searchpath='web/templates/')
templateEnv = Environment(loader=templateLoader, cache_size=0)


def hostname_to_site(hostname: str) -> str:
    """
    Determine which site to render given the hostname.

    Currently we have 2 renderings of sites, "pending" and "ncats". They differs in aesthetics, yet sharing the
    same backend.

    Hostname "biothings.ncats.io" and "biothings.ci.transltr.io" use "ncats" rendering, while "pending.biothings.io"
    uses "pending".
    """
    if hostname == "biothings.ncats.io" or hostname == "biothings.ci.transltr.io":
        return "ncats"

    return "pending"


class FrontPageHandler(BaseHandler):

    async def get(self):
        # TEMPORARY SOLUTION

        # http_client = tornado.httpclient.AsyncHTTPClient()
        # try:
        #     response = await http_client.fetch(
        #         "https://biothings.ncats.io/api/list")
        #     apilist = json.loads(response.body)['result']
        # except Exception as e:
        #     log.exception("Error retrieving app list.")
        #     # raise tornado.web.HTTPError(503, reason=str(e))
        #     apilist = [] # temporarily silence hub error

        root = self.biothings.config._primary
        attrs = [getattr(root, attr) for attr in dir(root)]
        confs = [attr for attr in attrs if isinstance(attr, types.ModuleType)]
        apilist = [{
            "_id": conf.API_PREFIX,
            "status": "running"
        } for conf in confs]

        # templateEnv.globals['site'] = "pending"
        # if self.request.host == "biothings.ncats.io":
        #     templateEnv.globals['site'] = "ncats"

        templateEnv.globals['site'] = hostname_to_site(self.request.host)
        template = templateEnv.get_template("index.html")
        output = template.render(Context=json.dumps({"List": apilist}))
        self.finish(output)


class ApiViewHandler(tornado.web.RequestHandler):

    def get(self):
        # templateEnv.globals['site'] = "pending"
        # if self.request.host == "biothings.ncats.io":
        #     templateEnv.globals['site'] = "ncats"

        templateEnv.globals['site'] = hostname_to_site(self.request.host)
        template = templateEnv.get_template("try.html")
        output = template.render()
        self.finish(output)


EXTRA_HANDLERS = [
    (r"/", FrontPageHandler),
    (r"/[^/]+", ApiViewHandler),
]
