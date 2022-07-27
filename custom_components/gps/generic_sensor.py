from homeassistant.components.sensor import SensorEntity
import logging

_LOGGER = logging.getLogger(__name__)

"""Generic SensorEntity."""

class GenericSensor(SensorEntity):

    def __init__(self, name, icon, unit):
        self._name = name
        self._icon = icon
        self._unit = unit
        self._state = self._attributes = None

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self) -> str:
        return self._icon

    @property
    def native_unit_of_measurement(self) -> str:
        return self._unit
        
    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the attributes of the entity."""
        return self._attributes

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def unique_id(self) -> str:
        return f"{self.name}_id"