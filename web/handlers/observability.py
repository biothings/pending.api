import asyncio
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


    def get_observability_metrics(self, span, kubernetes_metrics):
        # Collect application version
        application_version = self.get_github_commit_hash()

        # Retrieve host name and IP
        host_name = socket.gethostname()
        host_ip = socket.gethostbyname(host_name)

        # Collect CPU metrics
        cpu_percent = psutil.cpu_percent()
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

        try:
            # # Set kubernetes metrics if they exists
            # kubernetes_metrics = CGroupMetrics()
            kubernetes_cpu_usage = kubernetes_metrics.get_cpu_usage_percent()
            logger.info(f"kubernetes_cpu_usage: {kubernetes_cpu_usage}")
            span.set_attribute("kubernetes.cpu_usage", kubernetes_cpu_usage)

            # kubernetes_memory_usage = kubernetes_metrics.get_memory_usage_percent()
            # logger.info(f"kubernetes_memory_usage: {kubernetes_memory_usage}")
            # span.set_attribute("kubernetes.memory_usage", kubernetes_memory_usage)
            kubernetes_memory_current, kubernetes_memory_max, kubernetes_memory_percent = kubernetes_metrics.get_memory_usage_percent()
            logger.info(f"kubernetes_memory_current: {kubernetes_memory_current}")
            logger.info(f"kubernetes_memory_max: {kubernetes_memory_max}")
            logger.info(f"kubernetes_memory_percent: {kubernetes_memory_percent}")
            span.set_attribute("kubernetes.memory_current", kubernetes_memory_current)
            span.set_attribute("kubernetes.memory_max", kubernetes_memory_max)
            span.set_attribute("kubernetes.memory_percent", kubernetes_memory_percent)
        except Exception as e:
            logger.error(e)

        logger.info("Observability metrics collected.")


    # def metrics_collector(self, tracer, interval):
    #     while True:
    #         with tracer.start_as_current_span("observability_metrics") as span:
    #             try:
    #                 self.get_observability_metrics(span)
    #             except Exception as e:
    #                 # logger.error(f"Error collecting observability metrics: {e}")
    #                 raise e
    #         time.sleep(interval)

    # def start_metrics_thread(self, tracer, interval):
    #     # Start a background thread to collect metrics every `interval` seconds
    #     thread = threading.Thread(target=self.metrics_collector, args=(tracer, interval), daemon=True)
    #     thread.start()

    def metrics_collector(self, span, kubernetes_metrics, interval):
        # Run an infinite loop to collect metrics asynchronously

        from opentelemetry.exporter.jaeger.thrift import JaegerExporter
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry import trace
        from opentelemetry.trace import use_span


        trace_exporter = JaegerExporter(
            agent_host_name=self.OPENTELEMETRY_JAEGER_HOST,
            agent_port=self.OPENTELEMETRY_JAEGER_PORT,
            udp_split_oversized_batches=True,
        )

        trace_provider = TracerProvider(resource=Resource.create({SERVICE_NAME: self.OPENTELEMETRY_SERVICE_NAME}))
        trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
        # tracer = trace_provider.get_tracer(__name__)
        tracer = trace.get_tracer(__name__)


        # while True:
        # Start a new span
        # with tracer.start_as_current_span(name="observability_metrics") as span:
        span = tracer.start_span(name="observability_metrics")
        with use_span(span, end_on_exit=True) as span:
            # with trace.get_current_span()(name="observability_metrics") as span:
            try:
                # Collect observability metrics
                self.get_observability_metrics(span, kubernetes_metrics)
            except Exception as e:
                # Handle exceptions gracefully
                logger.error(f"Error collecting metrics: {e}")
                raise e
            # finally:
            #     span.end()

        # # Asynchronously wait for the next collection interval
        # await asyncio.sleep(interval)


    def __init__(self):
        self.OPENTELEMETRY_ENABLED = os.getenv("OPENTELEMETRY_ENABLED", OPENTELEMETRY_ENABLED).lower()

        if self.OPENTELEMETRY_ENABLED == "true":
            self.OPENTELEMETRY_JAEGER_HOST = os.getenv("OPENTELEMETRY_JAEGER_HOST", OPENTELEMETRY_JAEGER_HOST)
            self.OPENTELEMETRY_JAEGER_PORT = int(os.getenv("OPENTELEMETRY_JAEGER_PORT", OPENTELEMETRY_JAEGER_PORT))
            self.OPENTELEMETRY_SERVICE_NAME = os.getenv("OPENTELEMETRY_SERVICE_NAME", OPENTELEMETRY_SERVICE_NAME)
            self.OPENTELEMETRY_METRICS_INTERVAL = os.getenv("OPENTELEMETRY_METRICS_INTERVAL", OPENTELEMETRY_METRICS_INTERVAL)

            import tornado.ioloop
            import tornado.web
            from opentelemetry.instrumentation.tornado import TornadoInstrumentor

            # TornadoInstrumentor().instrument()

            # Configure the OpenTelemetry exporter
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter
            from opentelemetry.sdk.resources import SERVICE_NAME, Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry import trace
            from opentelemetry.trace import get_current_span


            trace_exporter = JaegerExporter(
                agent_host_name=self.OPENTELEMETRY_JAEGER_HOST,
                agent_port=self.OPENTELEMETRY_JAEGER_PORT,
                udp_split_oversized_batches=True,
            )

            trace_provider = TracerProvider(resource=Resource.create({SERVICE_NAME: self.OPENTELEMETRY_SERVICE_NAME}))
            trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))

            # TornadoInstrumentor().instrument()

            # Set the trace provider globally
            trace.set_tracer_provider(trace_provider)

            # Get metrics and send to Jaeger
            tracer = trace.get_tracer(__name__)
            # span = get_current_span()
            interval = self.OPENTELEMETRY_METRICS_INTERVAL
            # self.start_metrics_thread(tracer, interval)
            kubernetes_metrics = CGroupMetrics()

            TornadoInstrumentor().instrument()

            # tornado.ioloop.IOLoop.current().spawn_callback(self.metrics_collector, tracer, kubernetes_metrics, interval)
            from tornado.ioloop import PeriodicCallback
            metrics_recorder = PeriodicCallback(lambda: self.metrics_collector(tracer, kubernetes_metrics, interval), 5000)  # 5 seconds
            metrics_recorder.start()


class CGroupMetrics:
    def __init__(self):
        # Detect if we are using cgroup v1 or v2
        self.cgroup_version = self.detect_cgroup_version()
        self.cpu_stat_file = None
        self.memory_current_file = None
        self.memory_max_file = None

        if self.cgroup_version == 1:
            # Set file paths for cgroup v1
            self.cpu_stat_file = "/sys/fs/cgroup/cpu/cpuacct.usage"
            self.cpu_quota_file = "/sys/fs/cgroup/cpu/cpu.cfs_quota_us"
            self.cpu_period_file = "/sys/fs/cgroup/cpu/cpu.cfs_period_us"
            self.memory_current_file = "/sys/fs/cgroup/memory/memory.usage_in_bytes"
            self.memory_max_file = "/sys/fs/cgroup/memory/memory.limit_in_bytes"
        else:
            # Set file paths for cgroup v2
            self.cpu_stat_file = "/sys/fs/cgroup/cpu.stat"
            self.cpu_max_file = "/sys/fs/cgroup/cpu.max"
            self.memory_current_file = "/sys/fs/cgroup/memory.current"
            self.memory_max_file = "/sys/fs/cgroup/memory.max"

    def detect_cgroup_version(self):
        """Detect whether the system is using cgroup v1 or v2."""
        if os.path.exists("/sys/fs/cgroup/cgroup.controllers"):
            return 2  # cgroup v2
        elif os.path.exists("/sys/fs/cgroup/cpu/cpu.stat"):
            return 1  # cgroup v1
        else:
            logger.warning("Observability: Unknown cgroup version or unsupported system.")
            return 0

    def read_cgroup_value(self, file_path):
        try:
            with open(file_path, 'r') as file:
                value = file.read().strip()
                if value == "max":
                    return 0  # Return 0 if the value is 'max' (unlimited)
                return int(value)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error reading {file_path}: {e}")
            return 0

    def get_cpu_usage_percent(self):
        if self.cgroup_version == 1:
            # Read CPU usage for cgroup v1
            cpu_usage_1 = self.read_cgroup_value(self.cpu_stat_file)
            cpu_quota = self.read_cgroup_value(self.cpu_quota_file)
            cpu_period = self.read_cgroup_value(self.cpu_period_file)

            # Wait and get the CPU usage again
            time.sleep(1)
            cpu_usage_2 = self.read_cgroup_value(self.cpu_stat_file)
            cpu_usage_delta = cpu_usage_2 - cpu_usage_1

            # If there's no quota, return 0 (unlimited)
            if cpu_quota == "max":
                return 0

            # Calculate CPU usage percent
            num_cores = cpu_quota / cpu_period
            cpu_percent = (cpu_usage_delta / (cpu_period * num_cores * 1e9)) * 100
            cpu_percent = round(cpu_percent, 1)
            return cpu_percent

        elif self.cgroup_version == 2:
            # Read CPU usage for cgroup v2
            cpu_stat_1 = self.read_cpu_stat_v2()
            time.sleep(1)
            cpu_stat_2 = self.read_cpu_stat_v2()
            cpu_usage_delta = cpu_stat_2['usage_usec'] - cpu_stat_1['usage_usec']

            # Read CPU quota and period
            cpu_quota_ns, cpu_period_ns = self.parse_cpu_max_v2()

            # If no quota is set, return 0 (unlimited)
            if cpu_quota_ns == "max":
                return 0

            num_cores = cpu_quota_ns / cpu_period_ns
            cpu_percent = (cpu_usage_delta * 1000000 / (cpu_period_ns * num_cores * 1e9)) * 100
            cpu_percent = round(cpu_percent, 1)
            return cpu_percent
        else:
            return 0

    def read_cpu_stat_v2(self):
        cpu_stat = {}
        try:
            with open(self.cpu_stat_file, 'r') as file:
                for line in file:
                    key, value = line.split()
                    cpu_stat[key] = int(value)
        except FileNotFoundError as e:
            logger.error(f"Error reading {self.cpu_stat_file}: {e}")
        return cpu_stat

    def parse_cpu_max_v2(self):
        try:
            with open(self.cpu_max_file, 'r') as file:
                value = file.read().strip()
                if value == "max":
                    return 0, 100000000  # Default period is 100ms (100,000,000 ns)
                cpu_quota, cpu_period = value.split()
                return int(cpu_quota), int(cpu_period)
        except FileNotFoundError as e:
            logger.error(f"Error reading {self.cpu_max_file}: {e}")
            return 0, 100000000  # Default values if reading fails

    def get_memory_usage_percent(self):
        if self.cgroup_version == 1 or self.cgroup_version == 2:
            # Read memory usage
            memory_current = self.read_cgroup_value(self.memory_current_file)
            memory_max = self.read_cgroup_value(self.memory_max_file)

            # If memory max is unlimited, return 0
            if memory_max == "max":
                return 0, 0, 0

            # # Calculate memory usage percentage
            memory_percent = (memory_current / memory_max) * 100
            memory_percent = round(memory_percent, 1)

            return memory_current, memory_max, memory_percent
        else:
            return 0, 0, 0
