"""
Classes to define various iLO metrics.

Subsystems available:
  - Power
  - Memory
  - Processors
  - Network
  - Storage
  - Temperature
  - Fans
"""
from . import sensors


class SensorMetrics(object):
    """
    Represents a generic set of metrics.

    The SENSOR_TYPE class variable corresponds to the type of sensor this metric tracks.    
    Each subclass will have to define this to match the subsystem sensor type that it
    will generate metrics for.

    The raw sensor data will be stored in the sensorData attribute. This will include all
    data for all of that sensor type that is present, e.g. the set of all temperature sensor
    data.

    Subclasses may override the populate_sensors method if the data does not fit into 
    the list of dictionaries paradigm.
    """
    SENSOR_TYPE = object

    def __init__(self, data):
        self.sensorData = data
        self.sensors = []

    def populate_sensors(self):
        """
        This function will loop over the dict of dicts containing the raw sensor data.
        Each sensor will be instantiated using the SENSOR_TYPE class defined in the
        corresponding subclass. If the subclass didn't define that, then an exception
        will be raised as object is not a sensor class.

        The iLO will include data for sensors not present on the system, so we'll just
        skip over those whenever they're encountered.
        """
        for sensor in self.sensorData.values():
            mySensor = self.SENSOR_TYPE(**sensor)
            try:
                if mySensor.installed:
                    self.sensors.append(mySensor)
                    mySensor.generateMetrics()
            except ValueError:
                pass


class PowerSummaryMetrics(SensorMetrics):
    """
    This contains overall system power consumption metrics.
    Individual power supply metrics are tracked in the 
    PowerSupplyMetrics class
    """
    SENSOR_TYPE = sensors.PowerSensor

    def __init__(self, data):
        super().__init__(data)


class MemoryMetrics(SensorMetrics):
    """
    This contains system RAM metrics.
    The populate_sensors method is different since the data
    is organized differently for this subsystem.
    """
    SENSOR_TYPE = sensors.MemorySensor

    def __init__(self, data):
        """
        Need to set up the list of cpus from the raw data
        so that we can address the data by both cpu and socket later.
        """
        super().__init__(data)
        self.cpus = self.sensorData.keys()

    def populate_sensors(self):
        """
        The memory data is structured by both cpu and socket.
        We retrieve the raw iLO data by those parameters.

        The 'type' key is renamed to 'mem_type' to avoid any
        confusion with the builtin type keyword.
        """
        for cpu in self.cpus:
            for socket in self.sensorData[cpu].keys():
                sensorData = self.sensorData[cpu][socket]
                sensorData['cpu'] = cpu
                sensorData['mem_type'] = sensorData.pop('type')
                memorySensor = sensors.MemorySensor(**sensorData)

                try:
                    if memorySensor.installed:
                        self.sensors.append(memorySensor)
                        memorySensor.generateMetrics()
                except ValueError:
                    pass

class TemperatureMetrics(SensorMetrics):
    """
    Track the temperature subsystem metrics.
    """
    SENSOR_TYPE = sensors.TemperatureSensor

    def __init__(self, data):
        super().__init__(data)


class FanMetrics(SensorMetrics):
    """
    Track the fan subsystem metrics.
    """
    SENSOR_TYPE = sensors.FanSensor

    def __init__(self, data):
        super().__init__(data)


class CPUMetrics(SensorMetrics):
    """
    Track the processor subsystem metrics.
    """
    SENSOR_TYPE = sensors.CPUSensor

    def __init__(self, data):
        super().__init__(data)


class DiskMetrics(SensorMetrics):
    """
    Track the physical disk metrics.
    """
    SENSOR_TYPE = sensors.DiskSensor

    def __init__(self, data):
        """
        Need to convert the list of dicts into a dict of dicts.
        The populate_sensors method will loop over the values of
        the sensorData dictionary.
        """
        sensorData = {}
        for disk in data:
            key = disk['label']
            sensorData[key] = disk

        self.sensorData = sensorData
        self.sensors = []


class PowerSupplyMetrics(SensorMetrics):
    """
    Track the power supply subsystem metrics.
    """
    SENSOR_TYPE = sensors.PowerSupplySensor

    def __init__(self, data):
        super().__init__(data)
            

class NICMetrics(SensorMetrics):
    """
    Track the network subsystem metrics.
    """
    SENSOR_TYPE = sensors.NICSensor

    def __init__(self, data):
        super().__init__(data)
            

class PowerMetrics(SensorMetrics):
    """
    Track the power consumption metrics.

    Need to override the populate_sensors method since
    there is only one sensor for this.
    """
    SENSOR_TYPE = sensors.PowerSensor

    def __init__(self, data):
        super().__init__(data)

    def populate_sensors(self):
        sensor = sensors.PowerSensor(**self.sensorData)
        self.sensors.append(sensor)
        sensor.generateMetrics()
            

class SystemMetrics(SensorMetrics):
    """
    Track the system summary metrics.

    Need to override the populate_sensors method since
    there is only one sensor for this.
    """
    SENSOR_TYPE = sensors.SystemSensor

    def __init__(self, data):
        super().__init__(data)

    def populate_sensors(self):
        sensor = sensors.SystemSensor(**self.sensorData)
        self.sensors.append(sensor)
        sensor.generateMetrics()

class StorageMetrics(SensorMetrics):
    SENSOR_TYPE = sensors.StorageControllerSensor

    def __init__(self, data):
        super().__init__(data)
        self.controllerIds = self.sensorData.keys()

    def populate_sensors(self):
        for controllerId in self.controllerIds:
            controller = sensors.StorageControllerSensor(**self.sensorData[controllerId])
            self.sensors.append(controller)
            controller.generateMetrics()

            for enclosure in controller.enclosures:
                enclosure.generateMetrics()

            for logical_drive in controller.logical_drives:
                logical_drive.generateMetrics()
                for disk in logical_drive.disks:
                    disk.generateMetrics()
