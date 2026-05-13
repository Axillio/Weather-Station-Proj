# Smart Weather Station Backend

FastAPI backend for receiving MQTT weather-station data, validating it, storing it, serving REST endpoints, generating baseline forecasts, comparing station data with API weather data, and sending MQTT commands back to ESP32 devices.

## Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

The frontend is a separate Next.js app in `../frontend`.

For the ESP32 Mobile Hotspot demo, see [../HOTSPOT_DEMO_STEPS.md](../HOTSPOT_DEMO_STEPS.md).

For a separate MQTT worker process:

```bash
cd backend
RUN_MQTT_WORKER=false uvicorn app.main:app --reload
python -m app.mqtt_worker
```

## Main endpoints

- `GET /health`
- `GET /api/v1/devices`
- `GET /api/v1/latest?device_id=ws-esp32-001`
- `GET /api/v1/history?device_id=ws-esp32-001&start=1710000000&end=1710086400`
- `GET /api/v1/export?device_id=ws-esp32-001`
- `GET /api/v1/forecast?device_id=ws-esp32-001`
- `GET /api/v1/comparison?date=2026-04-30`
- `POST /api/v1/alerts/config`
- `POST /api/v1/devices/ws-esp32-001/commands`
