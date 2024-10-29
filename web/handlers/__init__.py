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

# from config_web import opentelemetry
from .graph import GraphQueryHandler
from .ngd import SemmedNGDHandler
from .annotator import AnnotatorHandler
from .status import StatusDefaultHandler
from .version import VersionHandler

from config_web import (
    OPENTELEMETRY_ENABLED,
    OPENTELEMETRY_JAEGER_HOST,
    OPENTELEMETRY_JAEGER_PORT,
    OPENTELEMETRY_SERVICE_NAME,
)

OPENTELEMETRY_ENABLED = os.getenv("OPENTELEMETRY_ENABLED", OPENTELEMETRY_ENABLED).lower()

if OPENTELEMETRY_ENABLED == "true":
    OPENTELEMETRY_JAEGER_HOST = os.getenv("OPENTELEMETRY_JAEGER_HOST", OPENTELEMETRY_JAEGER_HOST)
    OPENTELEMETRY_JAEGER_PORT = int(os.getenv("OPENTELEMETRY_JAEGER_PORT", OPENTELEMETRY_JAEGER_PORT))
    OPENTELEMETRY_SERVICE_NAME = os.getenv("OPENTELEMETRY_SERVICE_NAME", OPENTELEMETRY_SERVICE_NAME)

    from opentelemetry.instrumentation.tornado import TornadoInstrumentor

    TornadoInstrumentor().instrument()

    # Configure the OpenTelemetry exporter
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry import trace

    trace_exporter = JaegerExporter(
        agent_host_name=OPENTELEMETRY_JAEGER_HOST,
        agent_port=OPENTELEMETRY_JAEGER_PORT,
        udp_split_oversized_batches=True,
    )

    trace_provider = TracerProvider(resource=Resource.create({SERVICE_NAME: OPENTELEMETRY_SERVICE_NAME}))
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))

    # Set the trace provider globally
    trace.set_tracer_provider(trace_provider)

log = logging.getLogger("pending")

templateLoader = FileSystemLoader(searchpath="web/templates/")
templateEnv = Environment(loader=templateLoader, cache_size=0)


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


class FrontPageHandler(BaseHandler):

    # Cache the template output
    cached_template_output = None

    async def _load_template(self) -> str:
        """
        Loads the front page template

        Extracts the API list contents from the biothings
        configuration

        Then loads the template and renders it with the populated
        API list
        """
        # Check if the template output is already cached
        if FrontPageHandler.cached_template_output:
            return FrontPageHandler.cached_template_output

        root = self.biothings.config._primary
        attrs = [getattr(root, attr) for attr in dir(root)]
        confs = [attr for attr in attrs if isinstance(attr, types.ModuleType)]
        apilist = [{"_id": conf.API_PREFIX, "status": "running"} for conf in confs]

        templateEnv.globals["site"] = hostname_to_site(self.request.host)
        template = templateEnv.get_template("index.html")
        output = template.render(Context=json.dumps({"List": apilist}))

        FrontPageHandler.cached_template_output = output
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


class ApiViewHandler(tornado.web.RequestHandler):
    def get(self):
        # templateEnv.globals['site'] = "pending"
        # if self.request.host == "biothings.ncats.io":
        #     templateEnv.globals['site'] = "ncats"

        templateEnv.globals["site"] = hostname_to_site(self.request.host)
        template = templateEnv.get_template("try.html")
        output = template.render()
        self.finish(output)


EXTRA_HANDLERS = [
    (r"/", FrontPageHandler),
    (r"/status", StatusDefaultHandler),
    (r"/version", VersionHandler),
    (r"/[^/]+", ApiViewHandler),
    (r"/annotator(?:/([^/]+))?/?", AnnotatorHandler),
]
