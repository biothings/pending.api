import os
import psutil
import threading
import time

from config_web import (
    OPENTELEMETRY_ENABLED,
    OPENTELEMETRY_JAEGER_HOST,
    OPENTELEMETRY_JAEGER_PORT,
    OPENTELEMETRY_SERVICE_NAME,
)


class Observability():

    def get_system_metrics(self, span):
        # Get system metrics
        cpu_usage = psutil.cpu_percent()

        memory_info = psutil.virtual_memory()
        memory_usage = memory_info.percent

        disk_io_counters = psutil.disk_io_counters()
        disk_io_read = disk_io_counters.read_bytes
        disk_io_write = disk_io_counters.write_bytes

        swap_info = psutil.swap_memory()
        swap_total = swap_info.total
        swap_used = swap_info.used
        swap_free = swap_info.free

        virtual_info = psutil.virtual_memory()
        virtual_total = virtual_info.total
        virtual_used = virtual_info.used
        virtual_free = virtual_info.free

        net_io_counters = psutil.net_io_counters()
        net_io_read = net_io_counters.bytes_recv
        net_io_write = net_io_counters.bytes_sent

        system_load = psutil.getloadavg()

        # pid = os.getpid()
        # psutil.Process(pid)

        # Set metrics as attributes on the span
        span.set_attributes({
            "cpu_usage": cpu_usage,
            "system_loadavg_1min": system_load[0],
            "system_loadavg_5min": system_load[1],
            "system_loadavg_15min": system_load[2],
            "memory_usage": memory_usage,
            "virtual_total": virtual_total,
            "virtual_used": virtual_used,
            "virtual_free": virtual_free,
            "disk_io_read": disk_io_read,
            "disk_io_write": disk_io_write,
            "swap_total": swap_total,
            "swap_used": swap_used,
            "swap_free": swap_free,
            "net_io_read": net_io_read,
            "net_io_write": net_io_write,
        })

    def metrics_collector(self, tracer, interval=5):
        while True:
            with tracer.start_as_current_span("Metrics:get") as span:
                self.get_system_metrics(span)
            time.sleep(interval)

    def start_metrics_thread(self, tracer, interval=15):
        # Start a background thread to collect metrics every `interval` seconds
        thread = threading.Thread(target=self.metrics_collector, args=(tracer, interval), daemon=True)
        thread.start()

    def __init__(self):
        self.OPENTELEMETRY_ENABLED = os.getenv("OPENTELEMETRY_ENABLED", OPENTELEMETRY_ENABLED).lower()

        if self.OPENTELEMETRY_ENABLED == "true":
            self.OPENTELEMETRY_JAEGER_HOST = os.getenv("OPENTELEMETRY_JAEGER_HOST", OPENTELEMETRY_JAEGER_HOST)
            self.OPENTELEMETRY_JAEGER_PORT = int(os.getenv("OPENTELEMETRY_JAEGER_PORT", OPENTELEMETRY_JAEGER_PORT))
            self.OPENTELEMETRY_SERVICE_NAME = os.getenv("OPENTELEMETRY_SERVICE_NAME", OPENTELEMETRY_SERVICE_NAME)

            from opentelemetry.instrumentation.tornado import TornadoInstrumentor

            TornadoInstrumentor().instrument()

            # Configure the OpenTelemetry exporter
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter
            from opentelemetry.sdk.resources import SERVICE_NAME, Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry import trace

            trace_exporter = JaegerExporter(
                agent_host_name=self.OPENTELEMETRY_JAEGER_HOST,
                agent_port=self.OPENTELEMETRY_JAEGER_PORT,
                udp_split_oversized_batches=True,
            )

            trace_provider = TracerProvider(resource=Resource.create({SERVICE_NAME: self.OPENTELEMETRY_SERVICE_NAME}))
            trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))

            # Set the trace provider globally
            trace.set_tracer_provider(trace_provider)

            # Get metrics and send to Jaeger
            tracer = trace.get_tracer(__name__)
            interval = 30
            self.start_metrics_thread(tracer, interval)
