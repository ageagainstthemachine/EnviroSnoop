# EnviroSnoop

<img src="assets/envirosnoop_logo.png" width="200px" />

## A Raspberry Pi Pico W-Based Environmental Monitor

EnviroSnoop is an environmental monitoring system employing a Raspberry Pi Pico W. It leverages CircuitPython to measure various environmental parameters using a suite of sensors. Sensors can be easily enabled and disabled, making it a modular framework that supports various sensors. Data is sent to an InfluxDB 2 server for further visualization and analysis.

## Key Features:

- **Multiple Sensor Support:** Compatible with BME680, SCD4X, RadSens, and PM2.5 sensors for comprehensive environmental data collection.
- **Asynchronous Operation:** Employs asyncio for effective concurrent handling of sensor data reading, display updates, and network tasks.
- **Sensor Configuration Flexibility:** Dynamically manage sensor operations based on user-configured settings.
- **Dual Logging System:** Integrates both console and syslog server logging for thorough monitoring and diagnostics.
- **InfluxDB Connectivity:** Automatically transmits collected environmental data to an InfluxDB 2 database for analysis and storage.
- **Real-Time Display Updates:** Utilizes an OLED display for immediate visualization of some key sensor readings.
- **WiFi and NTP Synchronization:** Features WiFi connectivity for network operations and accurate timekeeping through NTP.

## System Requirements:

- Raspberry Pi Pico W with CircuitPython 8.2.x.
- Sensor modules (corresponding to desired environmental measurements).
- Various CircuitPython libraries and sensor libraries (see below).
- WiFi internet/network access.
- InfluxDB 2 server and auth info/token.
- A configured `settings.toml` file (see below for configuration).

## Required Modules and Libraries

EnviroSnoop requires various CircuitPython libraries and modules for its functionality. Below is a detailed list of these requirements:

- `os`: Provides a way of using operating system dependent functionality.
- `gc`: This module provides an interface to the garbage collector.
- `struct`: Performs conversions between Python values and C structs represented as Python bytes objects.
- `board`: Board-specific configuration for CircuitPython.
- `digitalio`: Digital input/output support.
- `wifi`: For handling WiFi connections.
- `socketpool`: Provides a pool of socket resources.
- `adafruit_ntp`: Network Time Protocol client for CircuitPython.
- `time`: Time related functions.
- `asyncio`: Provides infrastructure for writing single-threaded concurrent code using coroutines and multiplexing I/O access.
- `supervisor`: Provides access to CircuitPython's supervisor functions.
- `busio`: Provides support for bus protocols like I2C and SPI.
- `adafruit_requests`: CircuitPython library for making HTTP requests.
- `adafruit_connection_manager`: Library for managing sockets and connections.
- `ssl`: Provides access to Transport Layer Security (TLS) encryption and peer authentication facilities for network sockets.
- `circuitpython_base64`: Base64 encoding and decoding for CircuitPython. Note: I have renamed the standard base64.mpy to be circuitpython_base64.mpy.

### Display Libraries
- `displayio`: For managing displays.
- `adafruit_displayio_ssd1306`: Driver for the SSD1306 OLED display.
- `terminalio`: Default font and text size for CircuitPython.
- `adafruit_display_text.label`: For creating text labels on the display.

### Sensor Libraries
- `adafruit_bme680`: Library for the BME680 sensor (temperature, humidity, pressure, gas).
- `adafruit_scd4x`: Library for the SCD4X sensor (CO2, temperature, humidity).
- `adafruit_pm25.uart`: Library for the PM2.5 sensor using UART.

### Custom Sensor Modules
- `RadSens`: Custom module for the RadSens radiation sensor.

### Syslog
- `usyslog`: A minimal syslog client for CircuitPython.

## Installation and Usage:

1. **Hardware Assembly:** Connect the required sensors to the Raspberry Pi Pico W (I2C & UART).
2. **Configuration Setup:** Adjust the `settings.toml` file to suit your needs.
3. **Program Execution:** Upload the code to the Raspberry Pi Pico W. Check the InfluxDB server to see if data is making it there.

## Monitored Parameters:

- BME680: Temperature, Humidity, Air Pressure, Gas Resistance
- SCD4X: CO2 Levels, Temperature, Humidity
- RadSens: Radiation Intensity, Pulse Count
- PM2.5 Sensor: Particulate Matter Concentration

## Configuration Overview

EnviroSnoop's behavior and sensor integration can be customized via the `settings.toml` file. Below is an overview of the configuration parameters:

### WiFi Configuration
- `SSID`: WiFi network SSID.
- `PSK`: Password for the WiFi network.

### SSL/TLS Configuration
- `SSL_VERIFY_HOSTNAME`: Set to "TRUE" to verify the SSL/TLS hostname.

### Location Configuration
- `LOCATION`: Physical location of the device (e.g., "Some-Room").

### NTP (Network Time Protocol) Configuration
- `NTP_OFFSET`: Timezone offset from UTC (e.g., "-8" for Pacific Time).
- `NTP_SYNC_INTERVAL`: Time synchronization interval (in seconds).

### Sensor Enable/Disable Flags
- `ENABLE_PM25_SENSOR`: Enable or disable the PM2.5 sensor.
- `ENABLE_SCD4X_SENSOR`: Enable or disable the SCD4X sensor.
- `ENABLE_RADSENS_SENSOR`: Enable or disable the RadSens sensor.
- `ENABLE_BME680_SENSOR`: Enable or disable the BME680 sensor.

### Sensor Read Intervals
- `SCD4X_INTERVAL`, `BME680_INTERVAL`, `RADSENS_INTERVAL`, `PM25_INTERVAL`: Read intervals for each sensor (in seconds).

### Display Configuration
- `ENABLE_DISPLAY`: Enable or disable the OLED display functionality.
- `DISPLAY_UPDATE_INTERVAL`: Interval for updating the display (in seconds).
- `OLED_I2C_ADDR`: I2C address (in hexadecimal) for the OLED screen (default is 0x3C).
- `OLED_CONTRAST`: OLED display contrast (brightness) with acceptable values between 0.00 and 1.00.

### Sensor Calibrations
- `SEA_LEVEL_PRESSURE`: Sea level pressure in hPa for calibrating sensors.
- `BME680_TEMP_CALIBRATION_OFFSET`: Temperature calibration offset for the BME680 sensor.

### InfluxDB Configuration
- `INFLUXDB_URL`: IP/URL of the InfluxDB instance.
- `INFLUXDB_ORG`: Organization name for InfluxDB.
- `INFLUXDB_BUCKET`: Bucket name in InfluxDB.
- `INFLUXDB_TOKEN`: Authentication token for InfluxDB.
- `INFLUXDB_SEND_INTERVAL`: Interval for sending data to InfluxDB in seconds.

### Syslog Server Configuration
- `SYSLOG_SERVER_ENABLED`: Enable or disable syslog server logging.
- `SYSLOG_SERVER`: IP address or hostname of the syslog server.
- `SYSLOG_PORT`: Port number for the syslog server (note that only basic UDP syslog is supported currently).

### Diagnostic Configuration
- `MEMORY_MONITORING`: Enable or disable memory monitoring (during critical program execution points, memory usage stats are sent to syslog or the console).
- `CONSOLE_LOG_ENABLED`: Enable or disable console logging.

## Logo

The logo was generated by OpenAI's DALL-E 3 using an input prompt created by myself.

## License

EnviroSnoop is being release under the GNU GENERAL PUBLIC LICENSE VERSION 3. Please see the LICENSE file for more information. 

## Disclaimer

This code is probably extremely unstable and full of bugs. Like everything else on the internet, run at your own risk.

---

*EnviroSnoop - Precision Environmental Analytics in Real-Time*
