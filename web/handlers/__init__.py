"""
    Dynamic Web Pages
"""

import json
import logging
import os
import types

import tornado.httpclient
import tornado.web

# from config_web import opentelemetry
from .annotator import AnnotatorHandler
from .api import ApiListHandler
from .diseases import DiseasesHandler
from .graph import GraphQueryHandler
from .ngd import SemmedNGDHandler
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


EXTRA_HANDLERS = [
    (r"/status", StatusDefaultHandler),
    (r"/version", VersionHandler),
    (r"/api/list", ApiListHandler),
    (r"/annotator(?:/([^/]+))?/?", AnnotatorHandler),
    (r"/DISEASES(?:/.*)?", DiseasesHandler),
]
