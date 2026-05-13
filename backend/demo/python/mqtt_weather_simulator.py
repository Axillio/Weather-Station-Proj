#!/usr/bin/env python3
"""Fake ESP32 weather station publisher for end-to-end project demos."""

from __future__ import annotations

import argparse
import json
import random
import signal
import ssl
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
    mqtt_transport: str
    mqtt_tls: bool
    mqtt_websocket_path: str
    device_id: str
    interval: float
    start_seq: int


@dataclass
class SensorState:
    temp_c: float = 28.5
    humidity_pct: float = 62.0
    pressure_hpa: float = 1008.0
    rain_raw: int = 2200
    battery_mv: int = 4100
    rssi_dbm: int = -55

    def next_reading(self, seq: int, device_id: str) -> dict[str, object]:
        self.temp_c = _jitter(self.temp_c, drift=random.uniform(-0.28, 0.28), low=-5.0, high=48.0)
        self.humidity_pct = _jitter(
            self.humidity_pct,
            drift=random.uniform(-1.3, 1.3) + (0.25 if self.rain_raw < 1400 else -0.08),
            low=18.0,
            high=96.0,
        )
        self.pressure_hpa = _jitter(self.pressure_hpa, drift=random.uniform(-0.55, 0.55), low=985.0, high=1032.0)

        rain_drift = random.randint(-90, 90)
        if random.random() < 0.035:
            rain_drift += random.choice([-850, -650, 650, 850])
        self.rain_raw = int(_jitter(float(self.rain_raw), drift=rain_drift, low=250.0, high=3900.0))

        battery_drift = random.choice([-3, -2, -1, -1, 0, 0, 1])
        if random.random() < 0.02:
            battery_drift += random.choice([5, 8, -8])
        self.battery_mv = int(_jitter(float(self.battery_mv), drift=battery_drift, low=3550.0, high=4200.0))
        self.rssi_dbm = int(_jitter(float(self.rssi_dbm), drift=random.randint(-3, 3), low=-82.0, high=-42.0))

        return {
            "schema": "weather.v1",
            "device_id": device_id,
            "seq": seq,
            "ts": int(time.time()),
            "temp_c": round(self.temp_c, 2),
            "humidity_pct": round(self.humidity_pct, 2),
            "pressure_hpa": round(self.pressure_hpa, 2),
            "rain_raw": self.rain_raw,
            "rain": self.rain_raw < 1400,
            "rssi_dbm": self.rssi_dbm,
            "battery_mv": self.battery_mv,
            "fw_version": "esp32-weather-fw-1.1.0",
        }


def _jitter(value: float, drift: float, low: float, high: float) -> float:
    return max(low, min(high, value + drift))


def build_topics(device_id: str) -> dict[str, str]:
    base = f"weather/station/{device_id}"
    return {
        "data": f"{base}/data",
        "status": f"{base}/status",
        "cmd": f"{base}/cmd",
        "ack": f"{base}/ack",
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
    parser.add_argument("--mqtt-transport", choices=["tcp", "websockets"], default="tcp")
    parser.add_argument("--mqtt-tls", action="store_true", help="Use TLS. Required for wss:// routes.")
    parser.add_argument("--mqtt-websocket-path", default="/mqtt")
    parser.add_argument("--device-id", default="ws-esp32-001")
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--start-seq", type=int, default=1)
    args = parser.parse_args()

    config = SimConfig(
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        mqtt_username=args.mqtt_username,
        mqtt_password=args.mqtt_password,
        mqtt_transport=args.mqtt_transport,
        mqtt_tls=args.mqtt_tls,
        mqtt_websocket_path=args.mqtt_websocket_path,
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

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"esp32-{config.device_id}",
        transport=config.mqtt_transport,
    )
    if config.mqtt_username:
        client.username_pw_set(config.mqtt_username, config.mqtt_password)
    if config.mqtt_transport == "websockets":
        client.ws_set_options(path=config.mqtt_websocket_path)
    if config.mqtt_tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

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

    retry_delay = 2.0
    while running:
        try:
            print(
                f"[MQTT] connecting to {config.mqtt_host}:{config.mqtt_port} via {config.mqtt_transport}",
                flush=True,
            )
            client.connect(config.mqtt_host, config.mqtt_port, keepalive=60)
            break
        except OSError as exc:
            print(f"[MQTT] connection failed: {exc}; retrying in {retry_delay:.0f}s", flush=True)
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 1.5, 30.0)

    if not running:
        return 0

    client.loop_start()

    seq = config.start_seq
    sensor = SensorState()
    try:
        while running:
            payload = sensor.next_reading(seq, config.device_id)
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
