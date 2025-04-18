"""
Dynamic Web Pages
"""

import json
import logging
import os
import types

from biothings.web.handlers import BaseHandler
from jinja2 import Environment, FileSystemLoader


from config_web import (
    OPENTELEMETRY_ENABLED,
    OPENTELEMETRY_JAEGER_HOST,
    OPENTELEMETRY_JAEGER_PORT,
    OPENTELEMETRY_SERVICE_NAME,
)

from .annotator import AnnotatorHandler
from .api import ApiListHandler
from .diseases import DiseasesHandler
from .status import StatusDefaultHandler
from .version import VersionHandler


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

    def get(self):
        """
        Loads the front page template

        Extracts the API list contents from the biothings
        configuration

        Then loads the template and renders it with the populated
        API list
        """

        apilist = self.get_api_list()  # Get the API list

        template = templateEnv.get_template("index.html")
        output = template.render(Context=json.dumps({"List": apilist}))
        self.finish(output)


class ApiViewHandler(WebBaseHandler):
    def get(self):
        apilist = self.get_api_list()  # Get the API list

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
