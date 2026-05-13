import json
import ssl
import time
from typing import Any

import paho.mqtt.client as mqtt

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.services.alert_service import evaluate_reading
from app.services.storage_service import store_reading

_client: mqtt.Client | None = None


def _topic_device_id(topic: str) -> str | None:
    parts = topic.split("/")
    if len(parts) >= 4 and parts[:2] == ["weather", "station"]:
        return parts[2]
    return None


def _on_connect(client: mqtt.Client, _userdata: Any, _flags: dict[str, Any], rc: int, *_extra: Any) -> None:
    if rc == 0:
        client.subscribe("weather/station/+/data", qos=1)
        client.subscribe("weather/station/+/status", qos=1)


def _on_message(client: mqtt.Client, _userdata: Any, message: mqtt.MQTTMessage) -> None:
    topic = message.topic
    device_id = _topic_device_id(topic)
    try:
        payload = json.loads(message.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = {"device_id": device_id, "ts": int(time.time())}

    if not isinstance(payload, dict):
        payload = {"device_id": device_id, "ts": int(time.time())}

    with SessionLocal() as db:
        reading, duplicate = store_reading(db, payload, topic_device_id=device_id)
        if reading is not None:
            evaluate_reading(db, reading)
        seq = payload.get("seq") if isinstance(payload, dict) else None
        status = "duplicate" if duplicate else "stored"
        _publish_ack(client, device_id, seq, status)


def _publish_ack(client: mqtt.Client, device_id: str | None, seq: Any, status: str) -> None:
    if not device_id:
        return
    client.publish(
        f"weather/station/{device_id}/ack",
        json.dumps({"seq": seq, "status": status, "server_ts": int(time.time())}),
        qos=1,
        retain=False,
    )


def start_mqtt_worker() -> None:
    global _client
    if _client is not None:
        return

    settings = get_settings()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if settings.mqtt_username:
        client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
    if settings.mqtt_tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

    client.on_connect = _on_connect
    client.on_message = _on_message
    client.connect_async(settings.mqtt_host, settings.mqtt_port, keepalive=60)
    client.loop_start()
    _client = client


def stop_mqtt_worker() -> None:
    global _client
    if _client is None:
        return
    _client.loop_stop()
    _client.disconnect()
    _client = None


def publish_command(device_id: str, payload: dict[str, Any]) -> str:
    if _client is None:
        raise RuntimeError("MQTT worker is not running")
    topic = f"weather/station/{device_id}/cmd"
    _client.publish(topic, json.dumps(payload), qos=1, retain=False)
    return topic


def main() -> None:
    init_db()
    start_mqtt_worker()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_mqtt_worker()


if __name__ == "__main__":
    main()
