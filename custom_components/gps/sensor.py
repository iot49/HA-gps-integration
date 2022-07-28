"""Read and decode USB NMEA GPS."""

# see https://github.com/home-assistant/core/blob/dev/homeassistant/components/serial/sensor.py
from __future__ import annotations

import asyncio
import logging
import pynmea2
import time

from serial.tools import list_ports
from serial import SerialException
import serial_asyncio
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .generic_sensor import GenericSensor
from .const import *

_LOGGER = logging.getLogger(__name__)


def discover() -> str:
    """Search for and return connected GPS"""
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
        vol.Optional(CONF_TOL, default=DEFAULT_TOL): cv.positive_float,
        vol.Optional(CONF_QUALITY, default=DEFAULT_QUALITY): cv.positive_int,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the GPS sensor platform."""
    port = config.get(CONF_SERIAL_PORT)
    baudrate = config.get(CONF_BAUDRATE)
    tol = config.get(CONF_TOL)
    quality = config.get(CONF_QUALITY)
    
    sensors = {
        'latitude':  GenericSensor("latitude",  "mdi:longitude", "º"),
        'longitude': GenericSensor("longitude", "mdi:latitude", "º"),
        'elevation': GPSSensor(port, baudrate, tol, quality)
    }
    sensors['elevation']._sensors = sensors

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, sensors['elevation'].stop_gps_read)
    async_add_entities(sensors.values(), True)


class GPSSensor(GenericSensor):
    """Representation of a GPS sensor."""

    def __init__(self, port, baudrate, tol, quality):
        """Initialize the GPS sensor."""
        super().__init__("elevation", "mdi:elevation-rise", "m")
        self._port = port
        self._baudrate = baudrate
        self._tol = tol
        self._quality = quality

    async def async_added_to_hass(self):
        """Handle when an entity is about to be added to Home Assistant."""
        self._gps_loop_task = self.hass.loop.create_task(
            self.gps_read(self._port, self._baudrate)
        )

    async def gps_read(self, port, baudrate, **kwargs):
        """Read the data from the connected GPS."""
        sensors = self._sensors
        logged_error = False
        skip_count = 0
        last_latitude = last_longitude = 0
        while True:
            try:
                reader, _ = await serial_asyncio.open_serial_connection(url=port, baudrate=baudrate, **kwargs)

            except SerialException as exc:
                if not logged_error:
                    _LOGGER.exception(f"Unable to connect to the GPS {port}: {exc}. Keep trying ...")
                    # don't spam log
                    logged_error = True
                await self._handle_error()
            else:
                _LOGGER.info(f"Connected to GPS at {port}")
                while True:
                    try:           
                        line = await reader.readline()
                    except SerialException as exc:
                        _LOGGER.exception(f"Error while reading GPS {port}: {exc}")
                        await self._handle_error()
                        break
                    else:
                        line = line.decode("utf-8").strip()
                        try:
                            msg = pynmea2.parse(line)
                            if msg.gps_qual < self._quality:
                                _LOGGER.debug(f"skip low quality ({msg.gps_qual}) GPS reading")
                                skip_count += 1
                                if skip_count % 120 == 0:
                                    _LOGGER.warning(f"{skip_count} low quality (msg.gps_qual) gps readings ignored")
                                continue
                            if abs(msg.latitude - last_latitude) < self._tol and abs(msg.longitude - last_longitude) < self._tol:
                                _LOGGER.debug(f"ignore small position change")
                                continue
                            # update state
                            sensors['longitude']._state = msg.longitude
                            sensors['latitude' ]._state = msg.latitude
                            sensors['elevation']._state = msg.altitude
                            sensors['elevation']._attributes = {
                                'num_satelites': int(msg.num_sats),
                                'signal_quality': msg.gps_qual,
                                'timestamp': time.ctime(),
                            }
                            # report changed state to HA
                            _LOGGER.debug("update states in HA")
                            for s in sensors.values():
                                _LOGGER.debug(f"state[{s.name}] = {s.native_value} {s.native_unit_of_measurement}")
                                s.async_write_ha_state()
                            last_latitude = msg.latitude
                            last_longitude = msg.longitude
                        except (AttributeError, pynmea2.ParseError) as e:
                            _LOGGER.debug(f"***** Exception: {type(e)} {e}")
                        except Exception as e:
                            _LOGGER.exception(f"***** Unexpected error: {e}")

    async def _handle_error(self):
        """Handle error for serial connection."""
        self._state = None
        self._attributes = None
        self.async_write_ha_state()
        await asyncio.sleep(5)

    @callback
    def stop_gps_read(self, event):
        """Close resources."""
        if self._gps_loop_task:
            self._gps_loop_task.cancel()