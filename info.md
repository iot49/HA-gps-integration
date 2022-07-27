# GPS Integration

The `gps` sensor platform reads location and altitude data from an [NMEA](https://en.wikipedia.org/wiki/NMEA_0183) gps attached to a USB port. Uses the Python [pynmea2](https://github.com/Knio/pynmea2) library.

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
