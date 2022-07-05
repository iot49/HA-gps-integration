"""Read data from USB-connected GPS module."""

import asyncio
import logging
import pynmea2
import json
import time

from serial.tools import list_ports
from serial import SerialException
import serial_asyncio

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_NAME, CONF_VALUE_TEMPLATE, EVENT_HOMEASSISTANT_STOP
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE, CONF_ELEVATION
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import HomeAssistantType, ConfigType, DiscoveryInfoType
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

# Configuration

CONF_SERIAL_PORT = "serial_port"
CONF_BAUDRATE = "baudrate"
CONF_TOL = "tolerance"
CONF_QUALITY = "quality"

DEFAULT_NAME = "GPS Sensor"
DEFAULT_BAUDRATE = 4800
DEFAULT_TOL = 1e-3    # report updates only if change > TOL
DEFAULT_QUALITY = 1   # minimum GPS quality signal

def discover() -> str:
    """Helper: search USB ports for GPS receiver"""
    for port in list_ports.comports():
        # log all candidates to help user find correct port
        _LOGGER.info(f"Found device {port.vid:04x}:{port.pid:04x} by {port.manufacturer} @ {port.device}")
        # we have experience only with one device, for now ...
        if port.vid == 0x067b and port.pid == 0x23a3 and "Prolific" in port.manufacturer:
            return port.device
        return None

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_SERIAL_PORT, default=discover()): cv.string,
        vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): cv.positive_int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_TOL, default=DEFAULT_TOL): cv.positive_float,
        vol.Optional(CONF_QUALITY, default=DEFAULT_QUALITY): cv.positive_int,
    }
)

# platform setup

async def async_setup_platform(
    hass: HomeAssistantType,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the GPS sensor platform."""
    name = config.get(CONF_NAME)
    port = config.get(CONF_SERIAL_PORT)
    baudrate = config.get(CONF_BAUDRATE)
    tol = config.get(CONF_TOL)
    quality = config.get(CONF_QUALITY)

    sensor = GPSSensor(name, port, baudrate, tol, quality)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, sensor.stop_gps_read)
    async_add_entities([sensor], True)


class GPSSensor(SensorEntity):
    """Representation of a GitHub Repo sensor."""

    def __init__(self, name, port, baudrate, tol, quality):
        """Initialize the GPS sensor."""
        self._name = name
        self._port = port
        self._baudrate = baudrate
        self._tol = tol
        self._quality = quality
        self._state = None
        self._attributes = {}
        self._domain = name

    async def async_added_to_hass(self):
        """Handle when an entity is about to be added to Home Assistant."""
        self._gps_loop_task = self.hass.loop.create_task(
            self.gps_read(self._port, self._baudrate)
        )

    async def gps_read(self, device, baudrate, **kwargs):
        """Read the data from the connected GPS."""
        logged_error = False
        skip_count = 0
        last_latitude = last_longitude = 0
        while True:
            try:
                reader, _ = await serial_asyncio.open_serial_connection(url=device, baudrate=baudrate, **kwargs)

            except SerialException as exc:
                if not logged_error:
                    _LOGGER.exception(f"Unable to connect to the GPS {device}: {exc}. Will retry ...")
                    logged_error = True
                await self._handle_error()
            else:
                _LOGGER.info("GPS %s connected", device)
                while True:
                    try:
                        line = await reader.readline()
                    except SerialException as exc:
                        _LOGGER.exception(f"Error while reading GPS {device}: {exc}")
                        await self._handle_error()
                        break
                    else:
                        line = line.decode("utf-8").strip()
                        _LOGGER.debug("Received: {line}")
                        try:
                            msg = pynmea2.parse(line)
                            _LOGGER.debug("Parsed: {msg}")
                            if msg.gps_qual < self._quality:
                                skip_count += 1
                                if skip_count % 120 == 0:
                                    _LOGGER.warning(f"{skip_count} low quality gps readings ignored")
                                continue
                            if abs(msg.latitude - last_latitude) < self._tol and abs(msg.longitude - last_longitude) < self._tol:
                                # ignore small changes
                                continue
                            self._state = "gps_time"  # msg.timestamp
                            self._attributes[ATTR_LATITUDE] = msg.latitude
                            self._attributes[ATTR_LONGITUDE] = msg.longitude
                            self._attributes[CONF_ELEVATION] = msg.altitude
                            self._attributes['signal_quality'] = msg.gps_qual

                            last_latitude = msg.latitude
                            last_longitude = msg.longitude
                            # notify HA of new state
                            self.async_write_ha_state()

                        except (AttributeError, pynmea2.ParseError) as e:
                            _LOGGER.debug("Parsed: {e}")


    @callback
    def stop_gps_read(self, event):
        """Close resources."""
        if self._gps_loop_task:
            self._gps_loop_task.cancel()

    async def _handle_error(self):
        """Handle error for serial connection."""
        self._state = None
        self._attributes = None
        self.async_write_ha_state()
        await asyncio.sleep(5)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def extra_state_attributes(self):
        """Return the attributes of the entity (if any JSON present)."""
        return self._attributes

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state
