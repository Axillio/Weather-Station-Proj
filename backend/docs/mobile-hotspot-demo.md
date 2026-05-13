# Mobile Hotspot Demo Setup

This project has three moving parts:

```text
ESP32 Arduino sketch
  Wi-Fi + MQTT publish/subscribe
        |
        | connects to laptop hotspot IP, usually 192.168.137.1 on Windows
        v
MQTT broker on laptop
  Mosquitto listens on port 1883
        |
        | backend connects to localhost:1883
        v
FastAPI backend on laptop
  validates, stores, exposes API, sends commands
```

## Recommended Presentation Setup

Use your laptop Mobile Hotspot instead of school Wi-Fi.

Suggested hotspot values:

```text
SSID: WeatherDemo
Password: weatherdemo123
Laptop hotspot IP: 192.168.137.1
```

The ESP32 firmware uses `192.168.137.1` as `MQTT_HOST`.

If Mosquitto runs on Windows and FastAPI runs inside WSL, use `192.168.137.1` as `MQTT_HOST` in the backend too. If both Mosquitto and FastAPI run in the same WSL environment, use `localhost`.

## 1. Install Mosquitto

### Windows

Install Mosquitto from:

```text
https://mosquitto.org/download/
```

Add the Mosquitto install folder to PATH if needed.

Create a password file from PowerShell or Command Prompt:

```powershell
mosquitto_passwd -c C:\mosquitto\passwd weather_device
```

Use password:

```text
strong_password
```

In `mosquitto.conf`, add or update:

```conf
listener 1883 0.0.0.0
allow_anonymous false
password_file C:\mosquitto\passwd
```

Allow TCP port `1883` through Windows Firewall for private networks.

Start Mosquitto:

```powershell
mosquitto -c C:\Program Files\mosquitto\mosquitto.conf -v
```

If your path contains spaces and PowerShell complains, use:

```powershell
& "C:\Program Files\mosquitto\mosquitto.exe" -c "C:\Program Files\mosquitto\mosquitto.conf" -v
```

### Ubuntu/Linux

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo mosquitto_passwd -c /etc/mosquitto/passwd weather_device
sudo cp backend/mosquitto/weather-demo.conf /etc/mosquitto/conf.d/weather-demo.conf
sudo systemctl restart mosquitto
```

## 2. Configure FastAPI

Use this in `backend/.env`:

```env
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_USERNAME=weather_device
MQTT_PASSWORD=strong_password
MQTT_TLS=false
RUN_MQTT_WORKER=true
```

Run:

```bash
cd /home/zeeshan/WORK/IOTProj/backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 3. Configure Arduino IDE

Install board support:

```text
Arduino IDE -> Boards Manager -> install "esp32 by Espressif Systems"
```

Install library:

```text
Arduino IDE -> Library Manager -> install "PubSubClient" by Nick O'Leary
```

Open:

```text
backend/demo/arduino/WeatherStationMqttSimulator/WeatherStationMqttSimulator.ino
```

For real hardware sensors, open:

```text
backend/demo/arduino/WeatherStationProduction/WeatherStationProduction.ino
```

The production sketch reads a BME280 sensor over I2C, an analog rain sensor, optional battery voltage, Wi-Fi RSSI, receives MQTT commands, and publishes the same backend-compatible JSON payload.

Check these values at the top of the sketch:

```cpp
const char* WIFI_SSID = "WeatherDemo";
const char* WIFI_PASSWORD = "weatherdemo123";
const char* MQTT_HOST = "192.168.137.1";
const char* MQTT_USERNAME = "weather_device";
const char* MQTT_PASSWORD = "strong_password";
```

Upload to the ESP32 and open Serial Monitor at `115200`.

## 4. Test Data Flow

Watch raw MQTT readings:

```bash
mosquitto_sub -h localhost -p 1883 -u weather_device -P strong_password -t "weather/station/#" -v
```

Check FastAPI health:

```bash
curl http://127.0.0.1:8000/health
```

Check latest reading:

```bash
curl "http://127.0.0.1:8000/api/v1/latest?device_id=ws-esp32-001"
```

Send a command to the ESP32:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/devices/ws-esp32-001/commands" \
  -H "Content-Type: application/json" \
  -d '{"cmd":"sample_interval","value":10}'
```

The Arduino Serial Monitor should print the command, and the MQTT stream should show ACKs from the backend.

## WSL Note

If Python is running inside WSL but Mosquitto is running on Windows, set the backend `MQTT_HOST` to the Windows host address visible from WSL, or use the Windows broker IP. If both Mosquitto and Python run inside WSL, an ESP32 on the hotspot usually cannot directly reach WSL unless you add Windows port forwarding.

For the least painful school presentation, run Mosquitto on Windows and run the Python backend wherever it can reach that broker.
