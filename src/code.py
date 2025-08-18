# EnviroSnoop Environmental Monitor 20250816a
# https://github.com/ageagainstthemachine/EnviroSnoop

# ------------------------
# Libraries & Modules
# ------------------------

# Import minimum necessary libraries and modules
import os
import gc
import struct
import board
import digitalio
import wifi
import socketpool
import adafruit_ntp
import time
import asyncio
import supervisor
import busio
import adafruit_requests as requests
import ssl
from circuitpython_base64 import b64decode

# Syslog
SYSLOG_SERVER_ENABLED = os.getenv('SYSLOG_SERVER_ENABLED', 'false').lower() == 'true'
import usyslog

# Environment variables to determine if a sensor is enabled
# BME680
ENABLE_BME680_SENSOR = os.getenv('ENABLE_BME680_SENSOR', 'true').lower() == 'true'
# Import if enabled
if ENABLE_BME680_SENSOR:
    import adafruit_bme680

# SCD4X
ENABLE_SCD4X_SENSOR = os.getenv('ENABLE_SCD4X_SENSOR', 'true').lower() == 'true'
# Import if enabled
if ENABLE_SCD4X_SENSOR:
    import adafruit_scd4x

#RadSens
ENABLE_RADSENS_SENSOR = os.getenv('ENABLE_RADSENS_SENSOR', 'true').lower() == 'true'
# Import if enabled
if ENABLE_RADSENS_SENSOR:
    from RadSens import CG_RadSens

# PMS7003
ENABLE_PM25_SENSOR = os.getenv('ENABLE_PM25_SENSOR', 'true').lower() == 'true'
# Import if enabled
if ENABLE_PM25_SENSOR:
    from adafruit_pm25.uart import PM25_UART

# SSD1306
ENABLE_DISPLAY = os.getenv('ENABLE_DISPLAY', 'true').lower() == 'true'
# Import if enabled
if ENABLE_DISPLAY:
    import displayio
    import adafruit_displayio_ssd1306
    import terminalio
    from adafruit_display_text import label
    # CP 9+: I2CDisplay moved/renamed. Fall back for CP 8.x.
    try:
        from i2cdisplaybus import I2CDisplayBus
    except ImportError:
        from displayio import I2CDisplay as I2CDisplayBus  # Backwards compatability

# ------------------------
# Initial Operations
# ------------------------

# If display is enabled, release the display
if ENABLE_DISPLAY:
    # Release the display
    displayio.release_displays()

# Load WiFi credentials from settings.toml for network connection
ssid = os.getenv('SSID')
psk = os.getenv('PSK')

# SSL context (verify or skip verification of the cert)
SSL_VERIFY_HOSTNAME = os.getenv('SSL_VERIFY_HOSTNAME', 'true').lower() == 'true'

# Initialize socketpool for network operations
pool = socketpool.SocketPool(wifi.radio)

# Synchronous version of wifi_connect for initial setup
# This function will attempt to connect to WiFi using the provided SSID and password.
# It is designed to be called before the main asynchronous loop of the program starts.
def wifi_connect_sync():
    # Check if the device is already connected to WiFi.
    # If not, proceed to attempt a connection.
    if not wifi.radio.connected:
        try:
            # Attempt to connect to WiFi using the global SSID and PSK (password) variables.
            # These should be defined earlier in the code, read from the settings.toml file.
            wifi.radio.connect(ssid, psk)

            # If the connection is successful, print a confirmation message to the console.
            print("Connected to WiFi")

        # If the WiFi connection fails, catch the exception.
        # This could be due to incorrect credentials, network issues, or other WiFi-related errors.
        except ConnectionError as e:
            # Print an error message with the exception details.
            # This helps in diagnosing why the connection attempt failed.
            print(f"WiFi connection failed: {e}")

# Call wifi_connect_sync in initial operations
wifi_connect_sync()

# ------------------------
# Diagnostics
# ------------------------

# Global variable to store the console logging setting
CONSOLE_LOG_ENABLED = os.getenv('CONSOLE_LOG_ENABLED', 'false').lower() == 'true'

# Read the MEMORY_MONITORING setting from the environment and default to False if not set
ENABLE_MEMORY_MONITORING = os.getenv('MEMORY_MONITORING', 'false').lower() == 'true'

# Syslog server configuration for syslog logging
SYSLOG_SERVER = os.getenv('SYSLOG_SERVER')
SYSLOG_PORT = int(os.getenv('SYSLOG_PORT', 514))  # Default to 514 if not set

# Initialize syslog server if enabled
if SYSLOG_SERVER_ENABLED:
    s = usyslog.UDPClient(pool, SYSLOG_SERVER, SYSLOG_PORT)

# Structured logging (logs messages to both the console and syslog server based on configuration)
def structured_log(message, level=usyslog.S_INFO):
    if CONSOLE_LOG_ENABLED:
        print(message)
    
    if SYSLOG_SERVER_ENABLED:
        try:
            s.log(level, message)
        except RuntimeError:
            pass

# This function is designed to monitor and log the current memory usage of the program.
# It can be used to track memory consumption at various points in the code.
# Usage example: monitor_memory("Before starting a large operation")
def monitor_memory(tag=""):
    # Check if memory monitoring is enabled by the ENABLE_MEMORY_MONITORING flag.
    # This allows the memory monitoring feature to be toggled on or off as needed.
    if ENABLE_MEMORY_MONITORING:
        # Run garbage collection to free up unused memory and get a more accurate reading of memory usage.
        # This is useful in a constrained environment like microcontrollers where memory is limited.
        gc.collect()

        # Determine the amount of free memory available on the system.
        free_memory = gc.mem_free()

        # Determine the amount of memory currently allocated and in use.
        used_memory = gc.mem_alloc()

        # Calculate the total memory by adding free and used memory.
        total_memory = free_memory + used_memory

        # Calculate the percentage of free memory relative to the total memory.
        free_memory_pct = 100 * (free_memory / total_memory)

        # Log the memory usage details using the structured_log function.
        # The tag parameter can be used to specify where in the code this function was called
        # for easier identification in the logs.
        structured_log((f"[Memory] {tag} - Free: {free_memory} bytes and {free_memory_pct}%, Used: {used_memory} bytes, Total: {total_memory} bytes"))

# Print ENABLE_MEMORY_MONITORING to the log for diagnostic purposes
structured_log("Memory Monitoring Enabled = " + str(ENABLE_MEMORY_MONITORING))

# Print SYSLOG_SERVER_ENABLED to the log for diagnostic purposes
structured_log('Syslog Server Enabled = ' + str(SYSLOG_SERVER_ENABLED))

# Manually trigger garbage collection
gc.collect()

# ------------------------
# Main Configuration
# ------------------------

# Default NTP offset and sync interval configuration
DEFAULT_NTP_OFFSET = -8 # Pacific time
DEFAULT_NTP_SYNC_INTERVAL = 3600  # in seconds (1 hour)
# Read settings.toml for NTP offset
ntp_offset = int(os.getenv('NTP_OFFSET', DEFAULT_NTP_OFFSET))
# Print that to the log for diagnostic purposes
structured_log('Loaded NTP offset value of ' + str(ntp_offset))
# Read settings.toml for NTP sync interval
ntp_sync_interval = int(os.getenv('NTP_SYNC_INTERVAL', DEFAULT_NTP_SYNC_INTERVAL))
# Print that to the log for diagnostic purposes
structured_log('Loaded NTP sync interval value of ' + str(ntp_sync_interval))
# Global flag to indicate if time has been synchronized
time_synced = False

# Print I2C initializing to the log for diagnostic purposes
structured_log('Initializing I2C')
# Initialize I2C for the main program
i2c = busio.I2C(sda=board.GP20, scl=board.GP21)

# Load sea level pressure calibration value from settings.toml
SEA_LEVEL_PRESSURE = float(os.getenv('SEA_LEVEL_PRESSURE', '1013.25'))  # Default to 1013.25 hPa if not set
# Print SEA_LEVEL_PRESSURE to the log for diagnostic purposes
structured_log('SEA_LEVEL_PRESSURE loaded as ' + str(SEA_LEVEL_PRESSURE))

# If the sensor is enabled, continue configuration
if ENABLE_PM25_SENSOR:
    # Print PM2.5 UART initializing to the log for diagnostic purposes
    structured_log('Initializing PM2.5 UART')
    # Read settings.toml for PM2.5 interval
    pm25_interval = int(os.getenv('PM25_INTERVAL', 5))
    # Initialize UART with TX on GP12 and RX on GP13 for the PMS3003
    uart = busio.UART(tx=board.GP12, rx=board.GP13, baudrate=9600)
    # If you have a GPIO, its not a bad idea to connect it to the RESET pin
    # reset_pin = DigitalInOut(board.G0)
    # reset_pin.direction = Direction.OUTPUT
    # reset_pin.value = False
    reset_pin = None
    pm25 = PM25_UART(uart, reset_pin)
    # Global variables to store PM2.5 readings
    pm10_standard = None
    pm25_standard = None
    pm100_standard = None
    pm10_env = None
    pm25_env = None
    pm100_env = None
    particles_03um = None
    particles_05um = None
    particles_10um = None
    particles_25um = None
    particles_50um = None
    particles_100um = None

# If the sensor is enabled, continue configuration
if ENABLE_SCD4X_SENSOR:
    # Print SCD4X initializing to the log for diagnostic purposes
    structured_log('Initializing SCD4X')
    # Read settings.toml for SCD4X interval
    scd4x_interval = int(os.getenv('SCD4X_INTERVAL', 5))
    # Create an instance of the SCD4X class and pass it the i2c object
    scd4x = adafruit_scd4x.SCD4X(i2c)
    # Print serial number debug info on SCD4X sensor (uncomment next line if desired for testing)
    #print("Serial number:", [hex(i) for i in scd4x.serial_number])
    # Start periodic measurements on the SCD41 sensor
    scd4x.start_periodic_measurement()
    # Global variables to store SCD41 readings
    scd4x_co2 = None
    scd4x_temperature = None
    scd4x_humidity = None
    # Log the memory monitor post-initialization
    monitor_memory("Post SCD4X Initialization")

# If the sensor is enabled, continue configuration
if ENABLE_RADSENS_SENSOR:
    # Print RadSens initializing to the log for diagnostic purposes
    structured_log('Initializing RadSens')
    # Read settings.toml for RadSens interval
    radsens_interval = int(os.getenv('RADSENS_INTERVAL', 5))
    # Create an instance of the CG_RadSens class and pass the i2c object
    sensor = CG_RadSens(i2c)
    # Global variables to store radiation readings
    rad_intensy_dynamic = None
    rad_intensy_static = None
    number_of_pulses = None
    # Log the memory monitor post-initialization
    monitor_memory("Post RadSens Initialization")

# If the sensor is enabled, continue configuration
if ENABLE_BME680_SENSOR:
    # Print BE680 initializing to the log for diagnostic purposes
    structured_log('Initializing BME680')
    # Read settings.toml for BME680 interval
    bme680_interval = int(os.getenv('BME680_INTERVAL', 5))
    # Initialize the BME680 sensor.
    bme680_sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)
    bme680_sensor.sea_level_pressure = SEA_LEVEL_PRESSURE
    # Global variables to store BME680 readings
    bme680_temperature = None
    bme680_humidity = None
    bme680_pressure = None
    bme680_gas = None
    bme680_altitude = None
    # Log the memory monitor post-initialization
    monitor_memory("Post BME680 Initialization")

# Read location from settings.toml file
LOCATION = os.getenv('LOCATION', 'Unknown').replace(" ", "-")  # Remove spaces by changing them to a dash and default to 'Unknown' if not set
# Print location to the log for diagnostic purposes
structured_log('Loaded location - ' + str(LOCATION))

# Load InfluxDB configuration details from settings.toml for send interval
influxdb_send_interval = int(os.getenv('INFLUXDB_SEND_INTERVAL', 10))
# Load InfluxDB configuration details from settings.toml for time series data storage target
INFLUXDB_URL_BASE = os.getenv('INFLUXDB_URL')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_URL = f"{INFLUXDB_URL_BASE}?org={INFLUXDB_ORG}&bucket={INFLUXDB_BUCKET}"
HEADERS = {
    "Authorization": f"Token {INFLUXDB_TOKEN}",
    "Content-Type": "application/json"
}

# If display is enabled, setup the display
if ENABLE_DISPLAY:
    # Initialize the OLED display
    #displayio.release_displays() # We called this earlier
    display_update_interval = int(os.getenv('DISPLAY_UPDATE_INTERVAL', 1))
    #oled_reset = board.GP28 # If your display has a reset pin connected.
    WIDTH = 128
    HEIGHT = 64
    #BORDER = 5
    # CP 9+: use I2CDisplayBus (compat shim earlier supports CP 8.x)
    # If you have a reset pin wired, pass reset= (below)
    display_bus = I2CDisplayBus(i2c, device_address=0x3C) #, reset=oled_reset)
    display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)
    # Create a bitmap with two colors
    bitmap = displayio.Bitmap(WIDTH, HEIGHT, 2)
    # Create a two color palette
    palette = displayio.Palette(2)
    palette[0] = 0x000000  # Black
    palette[1] = 0xFFFFFF  # White
    # Create a TileGrid using the Bitmap and Palette
    tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
    # Create a Group to hold the TileGrid
    group = displayio.Group()
    # Add the TileGrid to the Group
    group.append(tile_grid)

# Conditional label creation based on whether sensors are enabled or disabled
if ENABLE_BME680_SENSOR and ENABLE_DISPLAY:
    temperature_label = label.Label(terminalio.FONT, text="Temp: ", color=0xFFFFFF, x=0, y=8)
    humidity_label = label.Label(terminalio.FONT, text="Humid: ", color=0xFFFFFF, x=0, y=20)
    pressure_label = label.Label(terminalio.FONT, text="Press: ", color=0xFFFFFF, x=0, y=32)
    ##gas_label = label.Label(terminalio.FONT, text="Gas: ", color=0xFFFFFF, x=0, y=44)
    ##altitude_label = label.Label(terminalio.FONT, text="Altitude: ", color=0xFFFFFF, x=0, y=56)
    group.append(temperature_label)
    group.append(humidity_label)
    group.append(pressure_label)
    ##group.append(gas_label)
    ##group.append(altitude_label)

if ENABLE_SCD4X_SENSOR and ENABLE_DISPLAY:
    co2_label = label.Label(terminalio.FONT, text="CO2: ", color=0xFFFFFF, x=0, y=44)
    group.append(co2_label)

if ENABLE_RADSENS_SENSOR and ENABLE_DISPLAY:
    radiation_label = label.Label(terminalio.FONT, text="Rad: ", color=0xFFFFFF, x=0, y=56)
    group.append(radiation_label)

if ENABLE_DISPLAY:
    # Show the group on the Display
    # Note: CP 9+: .show() removed in favor of root_group
    try:
        display.root_group = group
    except AttributeError:
        # Back-compat for CP 8.x
        display.show(group)

# Manually trigger garbage collection
gc.collect()

# Log the memory
monitor_memory("Initialization/Setup END")

# ------------------------
# Data Transfer
# ------------------------

# This function is an asynchronous helper function designed to send individual data points to an InfluxDB instance.
# It uses an HTTP session to post the data and logs the outcome of the operation.
async def send_data(data, http_session):
    # Check if there is any data to send.
    # This is a safeguard to prevent unnecessary network calls if there's no data.
    if data:
        try:
            # Send the data to InfluxDB using an HTTP POST request.
            # INFLUXDB_URL is the URL of the InfluxDB instance, and HEADERS contains any necessary headers for the request,
            # such as authorization tokens and content type.
            response = http_session.post(INFLUXDB_URL, headers=HEADERS, data=data)

            # Check the HTTP response status code to determine if the data was successfully sent.
            # HTTP 204 is typically returned by InfluxDB to indicate successful data ingestion without a response body.
            if response.status_code == 204:
                # Log a success message using the structured_log function.
                structured_log("Data sent to InfluxDB successfully!", usyslog.S_INFO)
            else:
                # If the status code is not 204, log the server's response as an error.
                # This can help in diagnosing why the data was not accepted by the server.
                structured_log("Failed to send data to InfluxDB:" + response.text, usyslog.S_ERR)

            # Close the response. This is important to free up system resources.
            response.close()

        # Catch any exceptions that occur during the HTTP request.
        # These could be network issues, InfluxDB server problems, etc.
        except Exception as e:
            # Log the exception details as an error for troubleshooting.
            structured_log("Error sending data to InfluxDB:" + str(e), usyslog.S_ERR)


# ------------------------
# Asynchronous Tasks
# ------------------------

# Asynchronous function to continuously read data from the PM2.5 sensor (PMS7003) and update global variables.
# This function runs indefinitely in the background (as part of an asyncio event loop) and updates air quality data.
async def read_pm25():
    # Declare global variables to store sensor data so they can be accessed elsewhere in the program.
    global pm10_standard, pm25_standard, pm100_standard
    global pm10_env, pm25_env, pm100_env
    global particles_03um, particles_05um, particles_10um
    global particles_25um, particles_50um, particles_100um

    while True:  # Infinite loop to continuously read sensor data.
        try:
            # Attempt to read data from the PM2.5 sensor.
            aqdata = pm25.read()

            # Update global variables with the sensor data.
            # These variables store concentrations of different particulate matter sizes.
            pm10_standard = aqdata["pm10 standard"]
            pm25_standard = aqdata["pm25 standard"]
            pm100_standard = aqdata["pm100 standard"]
            pm10_env = aqdata["pm10 env"]
            pm25_env = aqdata["pm25 env"]
            pm100_env = aqdata["pm100 env"]
            particles_03um = aqdata["particles 03um"]
            particles_05um = aqdata["particles 05um"]
            particles_10um = aqdata["particles 10um"]
            particles_25um = aqdata["particles 25um"]
            particles_50um = aqdata["particles 50um"]
            particles_100um = aqdata["particles 100um"]

            # Log the fetched data for debugging or monitoring purposes.
            # This uses the structured_log function to log the data in a structured format.
            structured_log(f"PM2.5 Data - PM 1.0 (Standard): {pm10_standard}, PM2.5 (Standard): {pm25_standard}, PM10 (Standard): {pm100_standard}, PM 1.0 (Env): {pm10_env}, PM2.5 (Env): {pm25_env}, PM10 (Env): {pm100_env}, Particles > 0.3um: {particles_03um}, Particles > 0.5um: {particles_05um}, Particles > 1.0um: {particles_10um}, Particles > 2.5um: {particles_25um}, Particles > 5.0um: {particles_50um}, Particles > 10um: {particles_100um}", usyslog.S_INFO)

        # If there's an error in reading from the sensor, log the error and then retry after a delay.
        # This is important for resilience, especially if the sensor temporarily fails or is disconnected.
        except IOError as io_error:
            # Handle I2C communication errors specifically
            structured_log(f"PM2.5 sensor I/O error: {io_error}", usyslog.S_ERR)
            await asyncio.sleep(10)  # Longer sleep for I/O errors

        except RuntimeError as runtime_error:
            # Handle other runtime errors
            structured_log(f"PM2.5 sensor runtime error: {runtime_error}", usyslog.S_ERR)
            await asyncio.sleep(5)

        except Exception as e:
            # Catch-all for any other exceptions
            structured_log(f"Unexpected error reading PM2.5 sensor: {e}", usyslog.S_ERR)
            await asyncio.sleep(10)
        
        # Await for pm25_interval amount before the next sensor read to limit the rate of data acquisition.
        # This interval can be adjusted based on how frequently the sensor data needs to be updated.
        await asyncio.sleep(pm25_interval)

# Asynchronous function to continuously read data from the SCD4X sensor and update global variables.
# The SCD4X sensor typically measures CO2 concentration, temperature, and humidity.
async def read_scd4x():
    # Declare global variables to store the CO2, temperature, and humidity data.
    # This allows these values to be accessed from other parts of the program.
    global scd4x_co2, scd4x_temperature, scd4x_humidity

    while True:  # An infinite loop to continuously check and read from the sensor.
        try:
            # Check if new data is ready to be read from the sensor.
            # The data_ready check is a non-blocking operation to see if the sensor has new data.
            if scd4x.data_ready:
                # Read the CO2 concentration (in parts per million), temperature (in degrees Celsius),
                # and relative humidity (in percent) from the sensor.
                scd4x_co2 = scd4x.CO2
                scd4x_temperature = scd4x.temperature
                scd4x_humidity = scd4x.relative_humidity

                # Log the read sensor data using structured logging for monitoring or debugging.
                # This helps to keep track of sensor readings over time.
                structured_log(f"SCD4X Data - CO2: {scd4x_co2} ppm, Temp: {scd4x_temperature:.2f} deg C, Humidity: {scd4x_humidity:.2f}%", usyslog.S_INFO)

        # Catch and handle any runtime errors during sensor reading.
        # This could happen due to communication issues with the sensor or hardware malfunctions.
        except IOError as io_error:
            structured_log(f"SCD4X sensor I/O error: {io_error}", usyslog.S_ERR)
            await asyncio.sleep(10)

        except RuntimeError as runtime_error:
            structured_log(f"SCD4X sensor runtime error: {runtime_error}", usyslog.S_ERR)
            await asyncio.sleep(5)

        except Exception as e:
            structured_log(f"Unexpected error reading SCD4X sensor: {e}", usyslog.S_ERR)
            await asyncio.sleep(10)

        # Await for scd4x_interval amount before the next sensor read to limit the rate of data acquisition.
        # This interval can be adjusted based on how frequently the sensor data needs to be updated.
        await asyncio.sleep(scd4x_interval)

# Asynchronous function to continuously read data from the BME680 sensor and update global variables.
# The BME680 sensor provides environmental data such as temperature, humidity, air pressure, gas resistance, and altitude.
async def read_bme680():
    # Declare global variables to store sensor data.
    # This allows these values to be accessed and used elsewhere in the program.
    global bme680_temperature, bme680_humidity, bme680_pressure, bme680_gas, bme680_altitude

    while True:  # Infinite loop to keep reading sensor data.
        try:
            # Read and store the temperature in degrees Celsius from the BME680 sensor.
            bme680_temperature = bme680_sensor.temperature

            # Read and store the relative humidity in percent from the sensor.
            bme680_humidity = bme680_sensor.humidity

            # Read and store the air pressure in hectopascals from the sensor.
            bme680_pressure = bme680_sensor.pressure

            # Read and store the gas resistance in ohms from the sensor.
            # This can be used to measure indoor air quality.
            bme680_gas = bme680_sensor.gas

            # Read and store the altitude in meters from the sensor.
            # The altitude is calculated based on air pressure.
            bme680_altitude = bme680_sensor.altitude

            # Log the read sensor data for monitoring or debugging purposes.
            # This structured log provides a consistent format for viewing or analyzing the sensor data.
            structured_log(f"Temperature: {bme680_temperature} deg C, Humidity: {bme680_humidity}%, Pressure: {bme680_pressure} hPa, Gas Resistance: {bme680_gas} ohms, Altitude: {bme680_altitude} meters", usyslog.S_INFO)

        # Catch and handle any runtime errors during sensor reading.
        # This could be due to communication issues or sensor malfunctions.
        except IOError as io_error:
            structured_log(f"BME680 sensor I/O error: {io_error}", usyslog.S_ERR)
            await asyncio.sleep(10)

        except RuntimeError as runtime_error:
            structured_log(f"BME680 sensor runtime error: {runtime_error}", usyslog.S_ERR)
            await asyncio.sleep(5)

        except Exception as e:
            structured_log(f"Unexpected error reading BME680 sensor: {e}", usyslog.S_ERR)
            await asyncio.sleep(10)

        # Await for 1 second before the next sensor read to regulate the data acquisition rate.
        await asyncio.sleep(1)

# Asynchronous function to continuously read data from the RadSens sensor and update global variables.
# The RadSens sensor is used for measuring radiation intensity and the number of radiation pulses.
async def read_radsens():
    # Declare global variables for storing radiation intensity and number of pulses.
    # These variables allow the radiation data to be accessed from other parts of the program.
    global rad_intensy_dynamic, rad_intensy_static, number_of_pulses

    while True:  # Infinite loop for continuous data reading.
        try:
            # Read and store the dynamic radiation intensity.
            # This might represent real-time or frequently updated radiation levels.
            rad_intensy_dynamic = sensor.get_rad_intensy_dynamic()

            # Read and store the static radiation intensity.
            # This could represent a less frequently updated or averaged radiation level.
            rad_intensy_static = sensor.get_rad_intensy_static()

            # Read and store the number of radiation pulses detected by the sensor.
            # This count can be useful for assessing radiation events over time.
            number_of_pulses = sensor.get_number_of_pulses()

            # Log the fetched radiation data for monitoring, analysis, or debugging.
            # This structured logging provides a consistent format for the radiation sensor data.
            structured_log(f"Radiation Intensity (Dynamic): {rad_intensy_dynamic} uR/h, Radiation Intensity (Static): {rad_intensy_static} uR/h, Number of Pulses: {number_of_pulses}", usyslog.S_INFO)

        # Catch and handle any runtime errors that occur during data retrieval from the sensor.
        # Errors might arise from communication issues with the sensor or other hardware-related problems.
        except IOError as io_error:
            structured_log(f"RadSens sensor I/O error: {io_error}", usyslog.S_ERR)
            await asyncio.sleep(10)

        except RuntimeError as runtime_error:
            structured_log(f"RadSens sensor runtime error: {runtime_error}", usyslog.S_ERR)
            await asyncio.sleep(5)

        except Exception as e:
            structured_log(f"Unexpected error reading RadSens sensor: {e}", usyslog.S_ERR)
            await asyncio.sleep(10)

        # Await for radsens_interval amount before the next sensor read to limit the rate of data acquisition.
        # This interval can be adjusted based on how frequently the sensor data needs to be updated.
        await asyncio.sleep(radsens_interval)

# Asynchronous function to manage the WiFi connection.
# This function continuously checks and maintains the WiFi connection in the background.
async def wifi_connect():
    # Infinite loop to keep the function running.
    while True:
        # Check if the device is currently not connected to WiFi.
        if not wifi.radio.connected:
            try:
                # Attempt to connect to the WiFi network using the global ssid and psk variables.
                # These variables should hold the WiFi network's SSID (name) and password.
                wifi.radio.connect(ssid, psk)

                # If the connection is successful, log a message with the device's IP address.
                # This is useful for network troubleshooting and confirming successful connections.
                structured_log("Connected! Device IP Address: " + str(wifi.radio.ipv4_address), usyslog.S_INFO)

            # Catch exceptions that occur if the WiFi connection fails.
            # This could be due to incorrect credentials, signal issues, or other WiFi-related problems.
            except ConnectionError as e:
                # Log the failed attempt and any associated information.
                structured_log(f"WiFi connection attempt failed: {e}", usyslog.S_ERR)
                # Log the memory
                monitor_memory("Post WiFi Connection Attempt")
                # If an error occurs, the function will pause for 10 seconds before retrying.
                # This prevents the function from attempting to reconnect too frequently.
                await asyncio.sleep(10)

        # If the device is already connected to WiFi,
        # the function will pause for 60 seconds before checking the connection again.
        # This is a less aggressive check to maintain the connection without constant polling.
        else:
            await asyncio.sleep(60)

# Asynchronous function to synchronize the device's time using the Network Time Protocol (NTP) at regular intervals.
async def ntp_time_sync():
    global time_synced
    # Wait until the device is connected to WiFi before attempting time synchronization.
    # This loop ensures that there is an active network connection for NTP communication.
    while not wifi.radio.connected:
        await asyncio.sleep(1)  # Pause for 1 second between each connection check.

    # Initialize the NTP client with the provided socket pool and timezone offset.
    # The timezone offset (ntp_offset) adjusts the time to the local timezone.
    ntp = adafruit_ntp.NTP(pool, tz_offset=ntp_offset)

    while True:  # Infinite loop to continuously synchronize time.
        try:
            # Log the start of the time synchronization process.
            structured_log("Syncing time...", usyslog.S_INFO)

            # Fetch the current time from an NTP server.
            # This updates the device's internal clock to the current time.
            current_time_struct = ntp.datetime

            # Format the fetched time into a human-readable string.
            formatted_time = f"{current_time_struct.tm_year}-{current_time_struct.tm_mon:02d}-{current_time_struct.tm_mday:02d} {current_time_struct.tm_hour:02d}:{current_time_struct.tm_min:02d}:{current_time_struct.tm_sec:02d}"

            # Log the successful time synchronization with the formatted time.
            structured_log(f"Time synchronized: {formatted_time}", usyslog.S_INFO)

            # Set the flag to True after successful sync
            time_synced = True

        # Catch any exceptions that might occur during the time synchronization process.
        # Exceptions can arise from network issues or NTP server unavailability.
        except Exception as e:
            # Log any errors encountered during time synchronization for troubleshooting.
            structured_log("Failed to sync time:" + str(e), usyslog.S_ERR)

        # Manually trigger garbage collection to manage memory usage effectively.
        gc.collect()

        # Pause the function based on the configured NTP sync interval (ntp_sync_interval).
        # This interval determines how frequently the device synchronizes its time with the NTP server.
        await asyncio.sleep(ntp_sync_interval)

async def send_data_to_influxdb():
    # Send data to InfluxDB
    global rad_intensy_dynamic, rad_intensy_static, number_of_pulses
    global bme680_temperature, bme680_humidity, bme680_pressure, bme680_gas, bme680_altitude
    global scd4x_co2, scd4x_temperature, scd4x_humidity
    global pm10_standard, pm25_standard, pm100_standard, pm10_env, pm25_env, pm100_env
    global particles_03um, particles_05um, particles_10um, particles_25um, particles_50um, particles_100um

    # Wait until the device is connected to WiFi and has synchronized time.
    while not wifi.radio.connected and not time_synced:
        await asyncio.sleep(1)

    # Create SSL context for secure HTTP communication.
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = SSL_VERIFY_HOSTNAME
    
    # Initialize an HTTP session for sending data.
    http_session = requests.Session(pool, ssl_context)

    while True:
        # Send RadSens sensor data
        if ENABLE_RADSENS_SENSOR and rad_intensy_dynamic is not None:
            await send_data(f"radiation_intensity_dynamic,device=radsens,location={LOCATION} value={rad_intensy_dynamic}", http_session)
        if ENABLE_RADSENS_SENSOR and rad_intensy_static is not None:
            await send_data(f"radiation_intensity_static,device=radsens,location={LOCATION} value={rad_intensy_static}", http_session)
        if ENABLE_RADSENS_SENSOR and number_of_pulses is not None:
            await send_data(f"number_of_pulses,device=radsens,location={LOCATION} value={number_of_pulses}", http_session)

        # Send BME680 sensor data
        if ENABLE_BME680_SENSOR and bme680_temperature is not None:
            await send_data(f"temperature,device=bme680,location={LOCATION} value={bme680_temperature}", http_session)
        if ENABLE_BME680_SENSOR and bme680_humidity is not None:
            await send_data(f"humidity,device=bme680,location={LOCATION} value={bme680_humidity}", http_session)
        if ENABLE_BME680_SENSOR and bme680_pressure is not None:
            await send_data(f"pressure,device=bme680,location={LOCATION} value={bme680_pressure}", http_session)
        if ENABLE_BME680_SENSOR and bme680_gas is not None:
            await send_data(f"gas_resistance,device=bme680,location={LOCATION} value={bme680_gas}", http_session)
        if ENABLE_BME680_SENSOR and bme680_altitude is not None:
            await send_data(f"altitude,device=bme680,location={LOCATION} value={bme680_altitude}", http_session)

        # Send SCD4X sensor data
        if ENABLE_SCD4X_SENSOR and scd4x_co2 is not None:
            await send_data(f"co2,device=scd4x,location={LOCATION} value={scd4x_co2}", http_session)
        if ENABLE_SCD4X_SENSOR and scd4x_temperature is not None:
            await send_data(f"temperature_scd4x,device=scd4x,location={LOCATION} value={scd4x_temperature}", http_session)
        if ENABLE_SCD4X_SENSOR and scd4x_humidity is not None:
            await send_data(f"humidity_scd4x,device=scd4x,location={LOCATION} value={scd4x_humidity}", http_session)

        # Send PM2.5 sensor data
        if ENABLE_PM25_SENSOR and pm10_standard is not None:
            await send_data(f"pm10_standard,device=pm25,location={LOCATION} value={pm10_standard}", http_session)
        if ENABLE_PM25_SENSOR and pm25_standard is not None:
            await send_data(f"pm25_standard,device=pm25,location={LOCATION} value={pm25_standard}", http_session)
        if ENABLE_PM25_SENSOR and pm100_standard is not None:
            await send_data(f"pm100_standard,device=pm25,location={LOCATION} value={pm100_standard}", http_session)
        if ENABLE_PM25_SENSOR and pm10_env is not None:
            await send_data(f"pm10_env,device=pm25,location={LOCATION} value={pm10_env}", http_session)
        if ENABLE_PM25_SENSOR and pm25_env is not None:
            await send_data(f"pm25_env,device=pm25,location={LOCATION} value={pm25_env}", http_session)
        if ENABLE_PM25_SENSOR and pm100_env is not None:
            await send_data(f"pm100_env,device=pm25,location={LOCATION} value={pm100_env}", http_session)
        # Continue with other particulate data if desired/necessary.

        # Log the memory
        monitor_memory("InfluxDB Send")

        # Manually trigger garbage collection to manage memory usage
        gc.collect()

        # Wait for the influx_send_interval amount before sending the next batch of data.
        # This interval can be adjusted based on how frequently the sensor data needs to be sent.
        await asyncio.sleep(influxdb_send_interval)

# Asynchronous function to continuously update the display with sensor readings.
async def update_display():
    while True:  # Infinite loop for continuous updates.
        # Update the display only if BME680 sensor is enabled
        if ENABLE_BME680_SENSOR:
            # Only update the display if the sensor data is available
            if bme680_temperature is not None:
                temperature_label.text = f"Temp: {bme680_temperature:.2f}C"
            else:
                temperature_label.text = "Temp: --"

            if bme680_humidity is not None:
                humidity_label.text = f"Humid: {bme680_humidity:.2f}%"
            else:
                humidity_label.text = "Humid: --"

            if bme680_pressure is not None:
                pressure_label.text = f"Press: {bme680_pressure:.2f}hPa"
            else:
                pressure_label.text = "Press: --"

            # Log the updated BME680 sensor readings for diagnostics
            structured_log(f"Updating Display - Temp: {bme680_temperature}, Humidity: {bme680_humidity}, Pressure: {bme680_pressure}", usyslog.S_INFO)

        # Update the display only if SCD4X sensor is enabled
        if ENABLE_SCD4X_SENSOR:
            # Update CO2 reading on the display
            co2_label.text = f"CO2: {scd4x_co2} ppm"

            # Log the updated SCD4X CO2 reading for diagnostics
            structured_log(f"Updating Display - CO2: {scd4x_co2}", usyslog.S_INFO)

        # Update the display only if RadSens sensor is enabled
        if ENABLE_RADSENS_SENSOR:
            # Update radiation reading on the display
            radiation_label.text = f"Rad: {rad_intensy_dynamic} uR/h"

            # Log the updated RadSens radiation reading for diagnostics
            structured_log(f"Updating Display - Radiation: {rad_intensy_dynamic}", usyslog.S_INFO)

        # Refreshing the display is not needed in every environment, hence it's commented out.
        # If your display requires manual refreshing after changing label texts, uncomment the next line.
        # display.refresh()

        # Manually trigger garbage collection to manage memory usage effectively.
        gc.collect()

        # Wait for display_update_interval amount before updating the display again.
        await asyncio.sleep(display_update_interval)

# The main asynchronous function that orchestrates and runs all other asynchronous tasks.
async def main():
    # Define a list of tasks that need to be run concurrently.
    # Each task is created using asyncio.create_task from the respective asynchronous function.
    tasks = [
        # Create a task for managing the WiFi connection.
        asyncio.create_task(wifi_connect()),
        # Create a task for synchronizing the device's time with an NTP server.
        asyncio.create_task(ntp_time_sync()),
        # Create a task for sending sensor data to an InfluxDB database.
        asyncio.create_task(send_data_to_influxdb()),
    ]
    # Create a task for continuously updating the display with the latest sensor readings.
    if ENABLE_DISPLAY:
        tasks.append(asyncio.create_task(update_display()))

    # Create tasks for reading data from the SCD4X, BME680, and RadSens sensors.
    if ENABLE_SCD4X_SENSOR:
        tasks.append(asyncio.create_task(read_scd4x()))
    if ENABLE_BME680_SENSOR:
        tasks.append(asyncio.create_task(read_bme680()))
    if ENABLE_PM25_SENSOR:
        tasks.append(asyncio.create_task(read_pm25()))
    if ENABLE_RADSENS_SENSOR:
        tasks.append(asyncio.create_task(read_radsens()))

    # Use asyncio.gather to run all the tasks concurrently.
    # This allows the program to handle multiple operations in parallel.
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        # If an exception occurs in any of the tasks, log the error for debugging.
        # This is important for understanding and resolving issues that may arise during execution.
        structured_log(f"An error occurred in the main task: {e}", usyslog.S_ERR)
        # Additional exception handling logic can be added here as needed.

# ------------------------
# Main Function
# ------------------------

# Run the main function
asyncio.run(main())
