# GPS Integration

The `gps` sensor platform reads location and altitude data from an [NMEA](https://en.wikipedia.org/wiki/NMEA_0183) gps attached to a USB port. Uses the Python [pynmea2](https://github.com/Knio/pynmea2) library.

## Install

The easiest way to install the BLE Monitor integration is with HACS. First install HACS if you don’t have it yet. In HACS, click on the three dots in the upper right corner and choose `Custom Repositories`. The repository is `https://github.com/iot49/HA-gps-integration.git`. Instruct HACS to download the integration, restart Home Assistant, and update your configuration per the instructions below. You will need to restart Home Assistant again to start the integration.

Alternatively, you can install it manually. Just copy paste the content of the `custom_components` folder in your `config/custom_components` directory. As example, you will get the `sensor.py` file in the following path: `config/custom_components/gps/sensor.py`. The disadvantage of a manual installation is that you won’t be notified about updates.

## Configuration

To set up the gps, add the following to your `configuration.yaml` file:

```
# Example configuration.yaml entry
sensor:
  - platform: gps
    serial_port: /dev/ttyUSB0
    tolerance: 0.01
    quality: 3
```

## Configuration Variables

**serial_port** string <br />
Local serial port where the GPS is connected. If not specified, the integration tries to find a compatible device. Check the log for a list of candidates if discovery fails.

**baudrate** integer (optional, default: 4800 bps) <br />
Baudrate of the serial port.

**tolerance** float (optional, default: 0.001) <br />
Only updates where the longitude or latitude changed by at least `tolerance` degrees are reported to Home Assistant.

**quality** integer (optional, default: 1) <br />
Skip low quality GPS readings. With a good device positioning, the quality of the GPS signal should be at least 3. Consider increasing this parameter to record only good fixes.

## Entities

Creates entities 

    * `sensor.longitude`, 
    * `sensor.latitude`, 
    * `sensor.elevation`. 
    
`sensor.elevation` has the following attributes:

    * timestamp (of last reading)
    * Number of satelites
    * GPS received signal quality
