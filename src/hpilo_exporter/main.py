"""
Entrypoint for the exporter
"""

import argparse

from hpilo_exporter.exporter import ILOMetricsExporter


def main():
    parser = argparse.ArgumentParser(description='Serves captured health metrics from the system iLO to Prometheus.')

    parser.add_argument('--metrics-file', type=str, default='hpiloMetrics.prom', help='file to read metrics from')
    parser.add_argument('--refresh-interval', type=int, default=180)
    parser.add_argument('--web-listen-port', default=9416, type=int)

    args = parser.parse_args()

    exporter = ILOMetricsExporter(**vars(args))
    exporter.run()


if __name__ == '__main__':
    main()
