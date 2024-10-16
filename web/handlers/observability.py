import logging
import socket
import os
import psutil
import threading
import time
import pathlib
import git

from config_web import (
    OPENTELEMETRY_ENABLED,
    OPENTELEMETRY_JAEGER_HOST,
    OPENTELEMETRY_JAEGER_PORT,
    OPENTELEMETRY_SERVICE_NAME,
    OPENTELEMETRY_METRICS_INTERVAL,
)

logger = logging.getLogger(__name__)

class Observability():

    # Cache the GitHub commit hash
    cached_commit_hash = None

    def get_github_commit_hash(self):
        """Retrieve the current GitHub commit hash using gitpython."""
        try:
            # Check if the hash is already cached
            if Observability.cached_commit_hash:
                return Observability.cached_commit_hash

            # Resolve the absolute path to the current file
            file_path = pathlib.Path(__file__).resolve()

            # Use git.Repo to find the root of the repository
            repo = git.Repo(file_path, search_parent_directories=True)

            if repo.bare:
                # Get the absolute path to the repository root
                repo_dir = repo.working_tree_dir
                logger.error(f"Git repository not found in directory: {repo_dir}")
                return "Unknown"

            # Get the latest commit hash
            commit_hash = repo.head.commit.hexsha

            # Cache the commit hash
            Observability.cached_commit_hash = commit_hash
            return commit_hash
        except Exception as e:
            logger.error(f"Error getting GitHub commit hash: {e}")
            return "Unknown"


    def get_observability_metrics(self, span):
        # Collect application version
        application_version = self.get_github_commit_hash()

        # Retrieve host name and IP
        host_name = socket.gethostname()
        host_ip = socket.gethostbyname(host_name)

        # Collect CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_times = psutil.cpu_times()
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)

        # Collect memory metrics
        memory_info = psutil.virtual_memory()
        # swap_info = psutil.swap_memory()

        # Collect disk metrics
        # disk_usage = psutil.disk_usage('/')
        # disk_io = psutil.disk_io_counters()

        # Collect network metrics
        # net_io = psutil.net_io_counters()

        # Collect load average (Linux-specific)
        if hasattr(psutil, "getloadavg"):
            load_avg = psutil.getloadavg()
        else:
            load_avg = (0, 0, 0)

        # Set span attributes for application version
        span.set_attribute("application.version", application_version)

        # Set span attributes for host information
        span.set_attribute("net.host.name", host_name)
        span.set_attribute("net.host.ip", host_ip)

        # Set span attributes for CPU metrics
        span.set_attribute("system.cpu.percent", cpu_percent)
        span.set_attribute("system.cpu.count_logical", cpu_count_logical)
        span.set_attribute("system.cpu.count_physical", cpu_count_physical)
        span.set_attribute("system.cpu.times.user", cpu_times.user)
        span.set_attribute("system.cpu.times.system", cpu_times.system)
        span.set_attribute("system.cpu.times.idle", cpu_times.idle)

        # Set span attributes for memory metrics
        span.set_attribute("system.memory.total", memory_info.total)
        span.set_attribute("system.memory.available", memory_info.available)
        span.set_attribute("system.memory.used", memory_info.used)
        span.set_attribute("system.memory.percent", memory_info.percent)
        # span.set_attribute("system.swap.total", swap_info.total)
        # span.set_attribute("system.swap.used", swap_info.used)
        # span.set_attribute("system.swap.free", swap_info.free)
        # span.set_attribute("system.swap.percent", swap_info.percent)

        # Set span attributes for disk metrics
        # span.set_attribute("system.disk.total", disk_usage.total)
        # span.set_attribute("system.disk.used", disk_usage.used)
        # span.set_attribute("system.disk.free", disk_usage.free)
        # span.set_attribute("system.disk.percent", disk_usage.percent)
        # span.set_attribute("system.disk.read_count", disk_io.read_count)
        # span.set_attribute("system.disk.write_count", disk_io.write_count)
        # span.set_attribute("system.disk.read_bytes", disk_io.read_bytes)
        # span.set_attribute("system.disk.write_bytes", disk_io.write_bytes)

        # Set span attributes for network metrics
        # span.set_attribute("system.network.bytes_sent", net_io.bytes_sent)
        # span.set_attribute("system.network.bytes_recv", net_io.bytes_recv)
        # span.set_attribute("system.network.packets_sent", net_io.packets_sent)
        # span.set_attribute("system.network.packets_recv", net_io.packets_recv)

        # Set span attributes for load average
        span.set_attribute("system.loadavg.1min", load_avg[0])
        span.set_attribute("system.loadavg.5min", load_avg[1])
        span.set_attribute("system.loadavg.15min", load_avg[2])

        logger.info("Observability metrics collected.")


    def metrics_collector(self, tracer, interval):
        while True:
            with tracer.start_as_current_span("observability_metrics") as span:
                try:
                    self.get_observability_metrics(span)
                except Exception as e:
                    logger.error(f"Error collecting observability metrics: {e}")
            time.sleep(interval)

    def start_metrics_thread(self, tracer, interval):
        # Start a background thread to collect metrics every `interval` seconds
        thread = threading.Thread(target=self.metrics_collector, args=(tracer, interval), daemon=True)
        thread.start()

    def __init__(self):
        self.OPENTELEMETRY_ENABLED = os.getenv("OPENTELEMETRY_ENABLED", OPENTELEMETRY_ENABLED).lower()

        if self.OPENTELEMETRY_ENABLED == "true":
            self.OPENTELEMETRY_JAEGER_HOST = os.getenv("OPENTELEMETRY_JAEGER_HOST", OPENTELEMETRY_JAEGER_HOST)
            self.OPENTELEMETRY_JAEGER_PORT = int(os.getenv("OPENTELEMETRY_JAEGER_PORT", OPENTELEMETRY_JAEGER_PORT))
            self.OPENTELEMETRY_SERVICE_NAME = os.getenv("OPENTELEMETRY_SERVICE_NAME", OPENTELEMETRY_SERVICE_NAME)
            self.OPENTELEMETRY_METRICS_INTERVAL = os.getenv("OPENTELEMETRY_METRICS_INTERVAL", OPENTELEMETRY_METRICS_INTERVAL)

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
            interval = self.OPENTELEMETRY_METRICS_INTERVAL
            self.start_metrics_thread(tracer, interval)
