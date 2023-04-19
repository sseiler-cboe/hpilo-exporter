"""
Classes used to convert raw iLO data into prometheus metrics.

Subsystems available:
  - Power
  - Memory
  - Processors
  - Network
  - Temperature
  - Fans
"""
from prometheus_client import Gauge


class Sensor(object):
    """
    Representation of a generic sensor.

    Subclasses should not need to override any methods/properties.

    Various status states are tracked in missingStatus to check to see
    if a particular sensor is not present on the system.

    Similarly, we track health by way of checking the status as being in
    the goodStatus strings.

    These could need to be amended based on the iLO version. HPE does not
    seem to have documentation to list all possible values.

    Subclasses need to define their own constructor as the promData dictionary
    is entirely dependent on each sensor. All sensor data must be put in the
    promData dictionary.

    Subclasses also need to define their own gauge class attribute. This defines
    the data that is presented out as prometheus metrics.
    """
    missingStatus = [ 'Not Installed', 'Not Present' ]
    goodStatus = [ 'OK', 'Good, In Use' ]

    @property
    def status(self):
        """
        Return the status of the sensor.
        """
        return self.promData['status']

    @property
    def healthy(self):
        """
        Check the status to see if it matches one of the healthy strings.
        """
        if self.status in self.goodStatus:
            return True

        return False

    @property
    def installed(self):
        """
        Check the status to see if it matches one of the missing strings.
        """
        if self.status in self.missingStatus:
            return False

        return True

    @property
    def promMetrics(self):
        """
        Generate the metrics that will go into the global registry.
        Use the contents of the promData dictionary to populate the labels
        and set the value to the object's value attribute.
        """
        return self.gauge.labels(**self.promData).set(self.value)


class SystemSensor(Sensor):
    """
    Sensor to monitor overall system health.

    This does not provide details about any of the subsystems but is an overview
    of their overall health. The battery may or may not be present, so allow for
    a missing value in the constructor and handle accordingly.

    As is typical in Prometheus, a status of 1 indicates everything is healthy
    and status of 0 is indicative of a problem.
    """
    gauge = Gauge('hpilo_system_health', 'HP iLO Overall System Health', ['battery', 'bios_hardware', 'fans', 'memory', 'network', 'power_supplies', 'processor', 'storage', 'temperature', 'ps_redundancy', 'fan_redundancy'])

    healthy_states = ['OK', 'Redundant']

    def __init__(self, bios_hardware, fans, memory, network, power_supplies, processor, storage, temperature, battery=None):
        self.promData = {}
        try:
          self.promData['battery'] = battery['status']
        except TypeError:
          self.promData['battery'] = 'Not Installed'

        self.promData['bios_hardware'] = bios_hardware['status']
        self.promData['fans'] = fans['status']
        self.promData['fan_redundancy'] = fans['redundancy']
        self.promData['memory'] = memory['status']
        self.promData['network'] = network['status']
        self.promData['power_supplies'] = power_supplies['status']
        self.promData['ps_redundancy'] = power_supplies['redundancy']
        self.promData['processor'] = processor['status']
        self.promData['storage'] = storage['status']
        self.promData['temperature'] = temperature['status']
    
        self.value = 1
        for status in self.promData.values():
            if status not in self.healthy_states and status not in self.missingStatus:
                self.value = self.value * 0
        

class PowerSensor(Sensor):
    """
    Sensor to monitor power usage.

    This is similar to the SystemSensor class in that it is an overview of the
    power subsystem. The sensor value is the current power consumption.
    """
    gauge = Gauge('hpilo_power_supplies_reading_gauge', 'HP iLO Power Usage', 
            ['high_efficiency_mode', 'hp_power_discovery_services_redundancy_status', 'power_management_controller_firmware_version', 'power_system_redundancy', 'unit'])

    def __init__(self, present_power_reading, high_efficiency_mode, hp_power_discovery_services_redundancy_status, power_management_controller_firmware_version, power_system_redundancy):
        self.promData = {}
        self.promData['unit'] = present_power_reading.split()[1]
        self.promData['high_efficiency_mode'] = high_efficiency_mode
        self.promData['hp_power_discovery_services_redundancy_status'] = hp_power_discovery_services_redundancy_status
        self.promData['power_management_controller_firmware_version'] = power_management_controller_firmware_version
        self.promData['power_system_redundancy'] = power_system_redundancy

        self.value = present_power_reading.split()[0]


class CPUSensor(Sensor):
    """
    This sensor monitors individual processors.

    The sensor value is the CPU health. Provide CPU details in the labels.
    """
    gauge = Gauge('hpilo_processor_detail_gauge', 'HP iLO CPU Detail', ['status', 'model', 'index', 'speed', 'l1_cache', 'l2_cache', 'l3_cache', 'execution_technology'])

    def __init__(self, status, name, label, speed, internal_l1_cache, internal_l2_cache, internal_l3_cache, execution_technology, **kwargs):
        self.promData = {}
        self.promData['status'] = status
        self.promData['model'] = name
        self.promData['index'] = label.split()[1]
        self.promData['speed'] = speed
        self.promData['l1_cache'] = internal_l1_cache
        self.promData['l2_cache'] = internal_l2_cache
        self.promData['l3_cache'] = internal_l3_cache
        self.promData['execution_technology'] = execution_technology

        self.value = 0
        if self.healthy:
            self.value = 1


class PowerSupplySensor(Sensor):
    """
    This sensor provides details for individual power supplies.

    The sensor value is its health status. Additional details are provided in the labels.
    """
    gauge = Gauge('hpilo_power_supplies_detail_gauge', 'HP iLO power supply details', ['capacity', 'firmware_version', 'hotplug_capable', 'name', 'model', 'serial_number', 'status', 'spare'])

    def __init__(self, label, capacity, firmware_version, model, serial_number, status, spare, present, hotplug_capable='No', pds=None):
        self.promData = {}
        self.promData['name'] = label
        self.promData['capacity'] = capacity
        self.promData['firmware_version'] = firmware_version
        self.promData['hotplug_capable'] = hotplug_capable
        self.promData['model'] = model
        self.promData['serial_number'] = serial_number
        self.promData['status'] = status
        self.promData['spare'] = spare

        self.value = 0
        if self.healthy:
            self.value = 1


class FanSensor(Sensor):
    """
    This sensor provides fan usage detail.

    The sensor value is the fan speed, expressed as a percentage.
    """
    gauge = Gauge('hpilo_fans_speed_percent_gauge', 'HP iLO fan speed', ['status', 'name', 'location', 'unit'])

    def __init__(self, label, speed, status, zone):
        self.promData = {}
        self.promData['unit'] = speed[1]
        self.promData['name'] = label
        self.promData['status'] = status
        self.promData['location'] = zone

        self.value = speed[0]


class NICSensor(Sensor):
    """
    This sensor provides network card detail.

    The sensor value is its health status. Note that non-HP NICs will come up as unknown.
    """
    gauge = Gauge('hpilo_nic_status_gauge', 'HP iLO NIC Status', ['status', 'name', 'location', 'ip_address', 'mac_address', 'description'])

    def __init__(self, ip_address, location, mac_address, network_port, port_description, status):
        self.promData = {}
        self.promData['ip_address'] = ip_address
        self.promData['mac_address'] = mac_address
        self.promData['name'] = location
        self.promData['status'] = status
        self.promData['location'] = network_port
        self.promData['description'] = port_description

        try:
            self.value = ['OK','Disabled','Unknown','Link Down'].index(status) + 1
        except ValueError:
            self.value = 0


class MemorySensor(Sensor):
    """
    This sensor details memory DIMM health.

    The sensor value is its health status. Labels provide information about the DIMM
    including its part number and location.

    The DIMM serial number may or may not be present.
    """
    gauge = Gauge('hpilo_memory', 'HP iLO memory status', ['cpu', 'frequency', 'part', 'size', 'socket', 'mem_type', 'status', 'serial'])

    def __init__(self, cpu, frequency, hp_smart_memory, minimum_voltage, part, ranks, size, socket, status, technology, mem_type, serial=None):
        self.promData = {}
        self.promData['cpu'] = cpu
        self.promData['frequency'] = frequency
        self.promData['part'] = part['number']
        self.promData['size'] = size
        self.promData['socket'] = socket
        self.promData['status'] = status
        self.promData['mem_type'] = mem_type
        try:
          self.promData['serial'] = serial['number']
        except TypeError:
          self.promData['serial'] = 'N/A'
  

        self.value = 0
        if self.healthy:
            self.value = 1

class DiskSensor(Sensor):
    """
    This sensor details disk information.

    The sensor value is its health status. Labels provide information about the disk
    including its serial number and location.
    """
    gauge = Gauge('hpilo_disk', 'HP iLO disk status', ['capacity', 'media_type', 'serial_number', 'model', 'fw_version', 'location', 'status'])

    def __init__(self, capacity, drive_configuration, encryption_status, fw_version, label, location, marketing_capacity, media_type, model, serial_number, status):
        self.promData = {}
        self.promData['capacity'] = capacity
        self.promData['media_type'] = media_type
        self.promData['serial_number'] = serial_number
        self.promData['model'] = model
        self.promData['fw_version'] = fw_version
        self.promData['location'] = location
        self.promData['status'] = status

        self.value = 0
        if self.healthy:
            self.value = 1

class TemperatureSensor(Sensor):
    """
    This sensor details temperature.

    The sensor value is the current temperature reading. Labels will provide
    the caution and critical thresholds when that information is available.

    Unlike the other sensors, this has separate timeseries to track the
    caution and critical thresholds. This is because prometheus does not
    allow for metrics to be compared against label values.
    """
    gauges = { 'hpilo_temperature_detail': Gauge('hpilo_temperature_detail', 'HP iLO temperature detail', ['name', 'caution', 'critical', 'location', 'status', 'unit']),
               'hpilo_temperature_caution': Gauge('hpilo_temperature_caution', 'HP iLO temperature caution values', ['name', 'location', 'unit']),
               'hpilo_temperature_critical': Gauge('hpilo_temperature_critical', 'HP iLO temperature critical values', ['name', 'location', 'unit']) }

    def __init__(self, caution, critical, currentreading, label, location, status):
        self.promData = {}
        self.promData['unit'] = currentreading[1]
        self.promData['name'] = label
        self.promData['status'] = status
        self.promData['location'] = location
        try:
            self.promData['caution'] = int(caution[0])
        except ValueError:
            self.promData['caution'] = -1
        try:
            self.promData['critical'] = int(critical[0])
        except ValueError:
            self.promData['critical'] = -1

        self.value = currentreading[0]

    @property
    def promMetrics(self):
        """
        Generate the metrics that will go into the global registry.
        Use the contents of the promData dictionary to populate the labels
        and set the value to the object's value attribute.

        For the other series, first confirm that the thresholds exist.
        """
        self.gauges['hpilo_temperature_detail'].labels(**self.promData).set(self.value)

        if self.promData['critical'] > 0:
          self.gauges['hpilo_temperature_critical'].labels(name=self.promData['name'], location=self.promData['location'], unit=self.promData['unit']).set(self.promData['critical'])
        if self.promData['caution'] > 0:
          self.gauges['hpilo_temperature_caution'].labels(name=self.promData['name'], location=self.promData['location'], unit=self.promData['unit']).set(self.promData['caution'])
        return self.gauges.values()
