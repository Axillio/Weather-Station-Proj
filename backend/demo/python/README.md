# Python MQTT Device Simulator

It simulates the ESP32 device by publishing backend-compatible MQTT payloads.

There are two simulator modes:

- `mqtt_weather_simulator.py`: automatic fake readings every few seconds
- `mqtt_weather_control_panel.py`: browser sliders for temperature, humidity, pressure, and a rain knob

## What It Replaces

- ESP32 firmware
- sensor hardware
- Wokwi circuit simulation

It does **not** replace:

- MQTT broker
- FastAPI backend
- Next.js frontend

So the demo chain becomes:

`python simulator -> MQTT broker -> FastAPI backend -> dashboard`

In Dokploy, the root `docker-compose.yml` can run this automatically as:

`mqtt-simulator container -> mqtt container -> backend container -> dashboard`

## Run It

Use the same Python environment as the backend:

```bash
cd backend
source .venv/bin/activate
python demo/python/mqtt_weather_simulator.py --mqtt-host broker.hivemq.com
```

## Interactive Control Panel

If you want a demo where you manually adjust values like a virtual circuit:

```bash
cd backend
source .venv/bin/activate
python demo/python/mqtt_weather_control_panel.py --mqtt-host broker.hivemq.com
```

Then open:

[http://127.0.0.1:8765](http://127.0.0.1:8765)

This gives you:

- temperature slider
- humidity slider
- pressure slider
- rain knob
- battery slider
- publish button
- auto-publish toggle

That is the closest replacement for “adjusting the virtual sensor values” without depending on Wokwi.

If your broker requires authentication:

```bash
python demo/python/mqtt_weather_simulator.py \
  --mqtt-host 192.168.137.1 \
  --mqtt-username weather_device \
  --mqtt-password strong_password
```

## Dokploy MQTT over WebSockets

The Dokploy compose runs Mosquitto with:

- internal MQTT/TCP on `1883` for the backend container
- external MQTT-over-WebSockets on container port `3000` for local simulator scripts

Point a Dokploy domain or route at the `mqtt` service on port `3000`, then run the simulator over WSS:

```bash
python demo/python/mqtt_weather_simulator.py \
  --mqtt-host YOUR_MQTT_DOMAIN \
  --mqtt-port 443 \
  --mqtt-transport websockets \
  --mqtt-tls \
  --mqtt-username weather_device \
  --mqtt-password strong_password
```

For the browser control panel:

```bash
python demo/python/mqtt_weather_control_panel.py \
  --mqtt-host YOUR_MQTT_DOMAIN \
  --mqtt-port 443 \
  --mqtt-transport websockets \
  --mqtt-tls \
  --mqtt-username weather_device \
  --mqtt-password strong_password
```

## Default Behavior

- device ID: `ws-esp32-001`
- topic: `weather/station/ws-esp32-001/data`
- publish interval: 5 seconds
- generated values use random drift for temperature, humidity, pressure, rain, RSSI, and battery

## Useful Options

```bash
python demo/python/mqtt_weather_simulator.py --interval 2
python demo/python/mqtt_weather_simulator.py --device-id ws-esp32-001
python demo/python/mqtt_weather_simulator.py --start-seq 50
```

## How To Verify

Backend:

```bash
curl "http://127.0.0.1:8000/api/v1/latest?device_id=ws-esp32-001"
```

Frontend:

Open [http://127.0.0.1:3000](http://127.0.0.1:3000)

## Minimal Backend MQTT Settings

For Docker/Dokploy, set these in the root `docker-compose.yml`:

```env
MQTT_HOST=mqtt
MQTT_PORT=1883
MQTT_USERNAME=weather_device
MQTT_PASSWORD=strong_password
MQTT_TLS=false
DEFAULT_DEVICE_ID=ws-esp32-001
RUN_MQTT_WORKER=true
```
