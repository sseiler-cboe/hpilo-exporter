"""
Collects data from specified iLO and converts it to Prometheus metrics
"""
import hpilo
import re

from . import metrics

import sys
import time
from prometheus_client import generate_latest, Summary
import logging

from prometheus_client import Gauge
from prometheus_client import REGISTRY

registry = REGISTRY

logging.basicConfig(level=logging.DEBUG, format=f'%(asctime)s %(levelname)s %(name)s: %(message)s')


class ILOMetrics(object):
    def __init__(self, ilo):
        self.ilo = ilo
        self._embedded_health = {}
        self.subsystems = {}

    @staticmethod
    def find_key(subDict, search_key):
        if search_key in subDict:
            return subDict

        for key, value in subDict.items():
            if isinstance(value, dict):
                item = ILOMetrics.find_key(value, search_key)
                if item is not None:
                    return item
            if isinstance(value, list):
                for v in value:
                    if isinstance(v, dict):
                        item = ILOMetrics.find_key(v, search_key)
                        if item is not None:
                            return item

    @property
    def product_name(self):
        return self.ilo.get_product_name()

    @property
    def server_name(self):
        return self.ilo.get_server_name()

    @property
    def ilo_fqdn(self):
        return self.ilo.get_server_fqdn()

    @property
    def ilo_url(self):
        return 'https://' + self.ilo_fqdn + '/'

    @property
    def embedded_health(self):
        if not self._embedded_health:
            self._embedded_health = self.ilo.get_embedded_health()

        return self._embedded_health

    def get_firmware_metrics(self):
        fwData = {}
        for k, v in self.embedded_health['firmware_information'].items():
            newK = re.sub('[^A-Za-z0-9]', '_', k)
            fwData[newK] = v

        fwMetrics = Gauge('hpilo_firmware_info', 'HP iLO Firmware Information', fwData.keys())
        fwMetrics.labels(**fwData).set(1)

    def get_metrics(self):
        redo_system_check = False

        iloFqdn = Gauge('hpilo_connection_data', 'Fully Qualified Domain Name and URL for iLO', ['fqdn', 'url'])
        iloFqdn.labels(fqdn=self.ilo_fqdn, url=self.ilo_url).set(1)
        self.subsystems['memory'] =  metrics.MemoryMetrics(self.embedded_health['memory']['memory_details'])
        self.subsystems['temperature'] = metrics.TemperatureMetrics(self.embedded_health['temperature'])
        self.subsystems['power'] = metrics.PowerMetrics(self.embedded_health['power_supply_summary'])
        self.subsystems['system'] = metrics.SystemMetrics(self.embedded_health['health_at_a_glance'])
        self.subsystems['network'] = metrics.NICMetrics(self.embedded_health['nic_information'])
        self.subsystems['fans'] = metrics.FanMetrics(self.embedded_health['fans'])
        self.subsystems['power_supplies'] = metrics.PowerSupplyMetrics(self.embedded_health['power_supplies'])
        self.subsystems['processors'] = metrics.CPUMetrics(self.embedded_health['processors'])
        if self.embedded_health['storage']:
            self.subsystems['storage'] = metrics.StorageMetrics(self.embedded_health['storage'])
            # See note below
            redo_system_check = True


        for subsys in self.subsystems.values():
            subsys.populate_sensors()

        """
        NOTE:
        This is to deal with the spurious storage errors that occur whenever a non-HPE drive is used
        in the system. The drive will not authenticate and show as being degraded. This is a workaround
        to cope with that circumstance. The storage metrics discard that issue, but we need the update
        to propagate up to the system check so that the storage subsystem does not show as being
        degraded
        """
        if redo_system_check:
            systemMetrics = self.subsystems['system']
            systemSensor = systemMetrics.sensors[0]

            storageStatus = 1
            for controller in self.subsystems['storage'].sensors:
                storageStatus = storageStatus * controller.value

            if storageStatus == 1:
                systemSensor.promData['storage'] = 'OK'
            else:
                systemSensor.promData['storage'] = 'Degraded'

            systemSensor.updateMetrics()

        self.get_firmware_metrics()
            

class ILOMetricsCollector(object):
    """
    Basic server implementation that exposes metrics to Prometheus
    """

    def __init__(self, metricsFile):
        self.metricsFile = metricsFile
        self.request_time = Summary('request_processing_seconds', 'Time spent processing request')

    def return_error(self):
        logging.error("Unknown error occurred. Exiting.")
        sys.exit(1)

    def write_metrics(self):
        try:
            with open(self.metricsFile, 'wb') as outFile:
                outFile.write(self.metrics)
        except Exception as e:
            logging.error("Unable to write metrics to {}".format(self.metricsFile))
            logging.error(e)
            sys.exit(1)

    def ilo_login(self):
        try:
            ilo = hpilo.Ilo(hostname='localhost')
            self.ilo = ilo
        except hpilo.IloLoginFailed:
            logging.error("ILO login failed")
            self.return_error()
        except hpilo.IloCommunicationError as e:
            logging.error(e)
        
        try:
            ilo.get_product_name()
        except Exception as e:
            logging.error(e)
            self.return_error()

    def run(self):
        start_time = time.time()
        logging.info("Starting collection of ilo metrics.")
        self.ilo_login()

        ilometrics = ILOMetrics(self.ilo)
        ilometrics.get_metrics()
        self.request_time.observe(time.time() - start_time)
        self.metrics = generate_latest(registry)
        self.write_metrics()
        sys.exit(0)

# vim: set ts=4 sts=4 sw=4 et:
