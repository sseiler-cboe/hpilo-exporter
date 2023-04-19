"""
Pulls data from specified iLO and presents as Prometheus metrics
"""
from __future__ import absolute_import
from prometheus_client import start_http_server, GC_COLLECTOR, PLATFORM_COLLECTOR, PROCESS_COLLECTOR
from prometheus_client.core import REGISTRY, GaugeMetricFamily
from prometheus_client.parser import text_fd_to_metric_families
import io
import json
import time

from site_syseng.lib import logging
from site_syseng.lib.logger import syseng_debug_logger

REGISTRY.unregister(GC_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(PROCESS_COLLECTOR)

log = logging.get_syseng_logger("syseng_default_logger")


class ILOMetricsExporter(object):
    @syseng_debug_logger(log)
    def __init__(self, web_listen_port, refresh_interval, metrics_file):
        self.port = web_listen_port
        self.refresh_interval = refresh_interval
        self.metrics_file = metrics_file

    @syseng_debug_logger(log)
    def run(self):
        REGISTRY.register(ILOMetricsRetriever(self.metrics_file))
        start_http_server(self.port)
        while True:
            time.sleep(self.refresh_interval)

class ILOMetricsRetriever(object):
    @syseng_debug_logger(log)
    def __init__(self, metrics_file):
        self.metrics_file = metrics_file

    @syseng_debug_logger(log)
    def collect(self):
        with io.open(self.metrics_file, 'r', encoding='utf-8') as metrics:
            for metric in text_fd_to_metric_families(metrics):
                yield metric
