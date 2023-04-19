"""
Entrypoint for the application
"""

import argparse

from hpilo_collector.collector import ILOMetricsCollector


def main():
    parser = argparse.ArgumentParser(description='Exports ilo heath_at_a_glance state to a file in prometheus metrics format.')

    parser.add_argument('--metrics-file', type=str, dest='metricsFile', default='hpiloMetrics.prom', help='file to write metrics to')

    args = parser.parse_args()

    collector = ILOMetricsCollector(**vars(args))
    collector.run()


if __name__ == '__main__':
    main()
