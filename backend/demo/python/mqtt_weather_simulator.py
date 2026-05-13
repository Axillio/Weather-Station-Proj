#!/usr/bin/env python3
"""Fake ESP32 weather station publisher for end-to-end project demos."""

from __future__ import annotations

import argparse
import json
import math
import random
import signal
import sys
import time
from dataclasses import dataclass

import paho.mqtt.client as mqtt


@dataclass
class SimConfig:
    mqtt_host: str
    mqtt_port: int
    mqtt_username: str | None
    mqtt_password: str | None
    device_id: str
    interval: float
    start_seq: int


def build_topics(device_id: str) -> dict[str, str]:
    base = f"weather/station/{device_id}"
    return {
        "data": f"{base}/data",
        "status": f"{base}/status",
        "cmd": f"{base}/cmd",
        "ack": f"{base}/ack",
    }


def build_reading(seq: int, device_id: str) -> dict[str, object]:
    phase = seq * 0.17
    rain_raw = int(1900 + math.sin(phase * 0.7) * 800)
    temp_c = round(28.5 + math.sin(phase) * 4.2, 2)
    humidity_pct = round(60.0 + math.cos(phase * 0.9) * 10.5, 2)
    pressure_hpa = round(1008.0 + math.sin(phase * 0.5) * 5.5, 2)
    battery_mv = max(3600, 4100 - (seq % 250))
    rssi_dbm = random.randint(-67, -46)
    return {
        "schema": "weather.v1",
        "device_id": device_id,
        "seq": seq,
        "ts": int(time.time()),
        "temp_c": temp_c,
        "humidity_pct": humidity_pct,
        "pressure_hpa": pressure_hpa,
        "rain_raw": rain_raw,
        "rain": rain_raw < 1400,
        "rssi_dbm": rssi_dbm,
        "battery_mv": battery_mv,
        "fw_version": "python-sim-1.0.0",
    }


def publish_status(client: mqtt.Client, topic: str, device_id: str, status: str) -> None:
    payload = {
        "device_id": device_id,
        "status": status,
        "server_ts": int(time.time()),
    }
    client.publish(topic, json.dumps(payload), qos=1, retain=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish fake weather station readings to MQTT.")
    parser.add_argument("--mqtt-host", default="broker.hivemq.com")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--mqtt-username", default=None)
    parser.add_argument("--mqtt-password", default=None)
    parser.add_argument("--device-id", default="ws-esp32-001")
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--start-seq", type=int, default=1)
    args = parser.parse_args()

    config = SimConfig(
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        mqtt_username=args.mqtt_username,
        mqtt_password=args.mqtt_password,
        device_id=args.device_id,
        interval=args.interval,
        start_seq=args.start_seq,
    )
    topics = build_topics(config.device_id)
    running = True

    def handle_signal(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"python-sim-{config.device_id}")
    if config.mqtt_username:
        client.username_pw_set(config.mqtt_username, config.mqtt_password)

    def on_connect(_client: mqtt.Client, _userdata: object, _flags: object, reason_code: object, _properties: object) -> None:
        print(f"[MQTT] connected rc={reason_code}")
        client.subscribe(topics["cmd"], qos=1)
        client.subscribe(topics["ack"], qos=1)
        publish_status(client, topics["status"], config.device_id, "online")

    def on_message(_client: mqtt.Client, _userdata: object, message: mqtt.MQTTMessage) -> None:
        try:
            body = message.payload.decode("utf-8")
        except UnicodeDecodeError:
            body = "<binary>"
        print(f"[MQTT] {message.topic}: {body}")

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[MQTT] connecting to {config.mqtt_host}:{config.mqtt_port}")
    client.connect(config.mqtt_host, config.mqtt_port, keepalive=60)
    client.loop_start()

    seq = config.start_seq
    try:
        while running:
            payload = build_reading(seq, config.device_id)
            ok = client.publish(topics["data"], json.dumps(payload), qos=1, retain=False)
            print(f"[PUB] seq={seq} result={ok.rc} payload={json.dumps(payload)}")
            seq += 1
            time.sleep(config.interval)
    finally:
        publish_status(client, topics["status"], config.device_id, "offline")
        time.sleep(0.2)
        client.loop_stop()
        client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
