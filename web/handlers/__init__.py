"""
    Dynamic Web Pages
"""

import json
import logging
import os
import types

import tornado.httpclient
import tornado.web
from biothings.web.handlers import BaseHandler
from jinja2 import Environment, FileSystemLoader
from config_web import (OPENTELEMETRY_ENABLED)

# from config_web import opentelemetry
from .annotator import AnnotatorHandler
from .api import ApiListHandler
from .diseases import DiseasesHandler
from .graph import GraphQueryHandler
from .ngd import SemmedNGDHandler
from .status import StatusDefaultHandler
from .version import VersionHandler

log = logging.getLogger("pending")

templateLoader = FileSystemLoader(searchpath="web/templates/")
templateEnv = Environment(loader=templateLoader, cache_size=0)

OPENTELEMETRY_ENABLED = os.getenv("OPENTELEMETRY_ENABLED", OPENTELEMETRY_ENABLED).lower()
if OPENTELEMETRY_ENABLED == "true":
    Observability()


def hostname_to_site(hostname: str) -> str:
    """
    Determine which site to render given the hostname.

    Currently we have 2 renderings of sites, "pending" and "ncats". They differs in aesthetics, yet sharing the
    same backend.

    Hostname "biothings.ncats.io" and "biothings[|.ci|.test].transltr.io" use "ncats" rendering, while "pending.biothings.io"
    uses "pending".
    """
    if hostname == "biothings.ncats.io" or hostname.endswith("transltr.io"):
        return "ncats"

    return "pending"

class WebBaseHandler(BaseHandler):
    def get_api_list(self):
        """
        Generate the API list from the biothings configuration.
        """
        root = self.biothings.config._primary
        attrs = [getattr(root, attr) for attr in dir(root)]
        confs = [attr for attr in attrs if isinstance(attr, types.ModuleType)]
        return [{"_id": conf.API_PREFIX, "status": "running"} for conf in confs]


class FrontPageHandler(WebBaseHandler):

    # Cache the template output
    cached_template_output = {}

    async def _load_template(self) -> str:
        """
        Loads the front page template

        Extracts the API list contents from the biothings
        configuration

        Then loads the template and renders it with the populated
        API list
        """
        site = hostname_to_site(self.request.host)

        # Check if the template output is already cached
        if FrontPageHandler.cached_template_output.get(site, False):
            return FrontPageHandler.cached_template_output[site]

        apilist = self.get_api_list()  # Get the API list

        templateEnv.globals["site"] = site
        template = templateEnv.get_template("index.html")
        output = template.render(Context=json.dumps({"List": apilist}))

        FrontPageHandler.cached_template_output[site] = output
        return output

    async def get(self):
        """
        GET method for rendering the frontpage template
        """
        rendered_template = await self._load_template()
        self.finish(rendered_template)

    async def head(self):
        """
        HEAD method for rendering the frontpage template
        """
        await self._load_template()
        self.finish()


class ApiViewHandler(WebBaseHandler):
    def get(self):
        # templateEnv.globals['site'] = "pending"
        # if self.request.host == "biothings.ncats.io":
        #     templateEnv.globals['site'] = "ncats"
        apilist = self.get_api_list()  # Get the API list

        templateEnv.globals["site"] = hostname_to_site(self.request.host)
        template = templateEnv.get_template("try.html")
        output = template.render(Context=json.dumps({"List": apilist}))
        self.finish(output)


EXTRA_HANDLERS = [
    (r"/", FrontPageHandler),
    (r"/status", StatusDefaultHandler),
    (r"/version", VersionHandler),
    (r"/api/list", ApiListHandler),
    (r"/[^/]+", ApiViewHandler),
    (r"/annotator(?:/([^/]+))?/?", AnnotatorHandler),
    (r"/DISEASES(?:/.*)?", DiseasesHandler),
]
