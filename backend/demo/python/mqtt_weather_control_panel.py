#!/usr/bin/env python3
"""Interactive browser-based MQTT weather simulator."""

from __future__ import annotations

import argparse
import json
import ssl
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import httpx
import paho.mqtt.client as mqtt


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Weather Station Control Panel</title>
  <style>
    :root {
      --bg: #f6f4ed;
      --card: #fffdf7;
      --ink: #1f2a33;
      --muted: #64707a;
      --accent: #0f766e;
      --accent-2: #d97706;
      --line: #d8d2c4;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(15,118,110,0.10), transparent 30%),
        radial-gradient(circle at bottom right, rgba(217,119,6,0.10), transparent 25%),
        var(--bg);
    }
    .wrap {
      max-width: 1040px;
      margin: 0 auto;
      padding: 32px 20px 60px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: 2rem;
    }
    p {
      margin: 0;
      color: var(--muted);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 18px;
      margin-top: 28px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 12px 30px rgba(24, 34, 42, 0.06);
    }
    .reading {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }
    .reading strong {
      font-size: 1.6rem;
    }
    label {
      display: block;
      margin: 14px 0 8px;
      font-weight: 600;
    }
    input[type="range"] {
      width: 100%;
      accent-color: var(--accent);
    }
    .row {
      display: flex;
      gap: 10px;
      align-items: center;
      margin-top: 12px;
      flex-wrap: wrap;
    }
    .knob {
      width: 140px;
      height: 140px;
      border-radius: 999px;
      margin: 12px auto 8px;
      border: 10px solid #d8e3e0;
      background:
        radial-gradient(circle at 50% 50%, #fff 0 34%, #cad8d5 35% 100%);
      position: relative;
      box-shadow: inset 0 0 16px rgba(0,0,0,0.08);
    }
    .needle {
      position: absolute;
      width: 6px;
      height: 42px;
      background: var(--accent-2);
      left: 50%;
      top: 18px;
      transform-origin: 50% 52px;
      translate: -50% 0;
      border-radius: 6px;
    }
    button {
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      font-weight: 700;
      cursor: pointer;
    }
    .primary {
      background: var(--accent);
      color: white;
    }
    .secondary {
      background: #e7ece8;
      color: var(--ink);
    }
    .status {
      margin-top: 18px;
      padding: 12px 14px;
      border-radius: 12px;
      background: #eef6f4;
      color: #12453f;
      font-size: 0.95rem;
      min-height: 46px;
    }
    code {
      background: #f0ece2;
      padding: 2px 6px;
      border-radius: 6px;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Weather Station Control Panel</h1>
    <p>Adjust values like a virtual circuit demo, then publish them to MQTT for the backend and dashboard.</p>

    <div class="grid">
      <section class="card">
        <div class="reading"><span>Temperature</span><strong id="tempVal">28.0 C</strong></div>
        <input id="temp" type="range" min="-10" max="60" step="0.1" value="28">

        <div class="reading"><span>Humidity</span><strong id="humVal">60.0 %</strong></div>
        <input id="hum" type="range" min="0" max="100" step="0.1" value="60">

        <div class="reading"><span>Pressure</span><strong id="presVal">1008.0 hPa</strong></div>
        <input id="pres" type="range" min="800" max="1100" step="0.1" value="1008">
      </section>

      <section class="card">
        <div class="reading"><span>Rain Sensor Knob</span><strong id="rainVal">2200</strong></div>
        <div class="knob">
          <div id="needle" class="needle"></div>
        </div>
        <input id="rain" type="range" min="0" max="4095" step="1" value="2200">
        <div class="row">
          <span>Rain state:</span>
          <strong id="rainState">No</strong>
        </div>

        <label for="battery">Battery</label>
        <input id="battery" type="range" min="3300" max="4200" step="1" value="4050">
        <div class="row">
          <span>Battery:</span>
          <strong id="batteryVal">4050 mV</strong>
        </div>
      </section>

      <section class="card">
        <div class="row">
          <button id="publishBtn" class="primary">Publish Now</button>
          <button id="toggleBtn" class="secondary">Start Auto Publish</button>
        </div>
        <label for="interval">Auto-publish interval</label>
        <input id="interval" type="range" min="1" max="15" step="1" value="5">
        <div class="row">
          <span>Interval:</span>
          <strong id="intervalVal">5 sec</strong>
        </div>
        <div class="status" id="status">Ready. MQTT topic: <code>weather/station/ws-esp32-001/data</code></div>
      </section>
    </div>
  </div>

  <script>
    const temp = document.getElementById("temp");
    const hum = document.getElementById("hum");
    const pres = document.getElementById("pres");
    const rain = document.getElementById("rain");
    const battery = document.getElementById("battery");
    const interval = document.getElementById("interval");
    const needle = document.getElementById("needle");
    const status = document.getElementById("status");
    const toggleBtn = document.getElementById("toggleBtn");
    let autoTimer = null;

    function updateReadout() {
      document.getElementById("tempVal").textContent = `${Number(temp.value).toFixed(1)} C`;
      document.getElementById("humVal").textContent = `${Number(hum.value).toFixed(1)} %`;
      document.getElementById("presVal").textContent = `${Number(pres.value).toFixed(1)} hPa`;
      document.getElementById("rainVal").textContent = rain.value;
      document.getElementById("rainState").textContent = Number(rain.value) < 1400 ? "YES" : "No";
      document.getElementById("batteryVal").textContent = `${battery.value} mV`;
      document.getElementById("intervalVal").textContent = `${interval.value} sec`;
      const angle = -135 + (Number(rain.value) / 4095) * 270;
      needle.style.transform = `translate(-50%, 0) rotate(${angle}deg)`;
    }

    async function publishOnce() {
      const payload = {
        temp_c: Number(temp.value),
        humidity_pct: Number(hum.value),
        pressure_hpa: Number(pres.value),
        rain_raw: Number(rain.value),
        battery_mv: Number(battery.value)
      };
      const response = await fetch("/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      status.textContent = response.ok
        ? `Published seq ${data.seq} at ${new Date().toLocaleTimeString()}`
        : `Publish failed: ${data.error || "unknown error"}`;
    }

    function setAutoPublishing(enabled) {
      if (autoTimer) {
        clearInterval(autoTimer);
        autoTimer = null;
      }
      if (enabled) {
        autoTimer = setInterval(() => { publishOnce().catch(console.error); }, Number(interval.value) * 1000);
        toggleBtn.textContent = "Stop Auto Publish";
      } else {
        toggleBtn.textContent = "Start Auto Publish";
      }
    }

    document.getElementById("publishBtn").addEventListener("click", () => publishOnce().catch(console.error));
    toggleBtn.addEventListener("click", () => setAutoPublishing(!autoTimer));
    interval.addEventListener("input", () => {
      updateReadout();
      if (autoTimer) setAutoPublishing(true);
    });
    [temp, hum, pres, rain, battery].forEach((el) => el.addEventListener("input", updateReadout));
    updateReadout();
    // Backend considers the device "online" if it has a reading within ~60 seconds.
    // Auto-publish by default so the dashboard stays live without extra clicks.
    setAutoPublishing(true);
  </script>
</body>
</html>
"""


class SimulatorState:
    def __init__(
        self,
        mqtt_host: str,
        mqtt_port: int,
        mqtt_username: str | None,
        mqtt_password: str | None,
        mqtt_transport: str,
        mqtt_tls: bool,
        mqtt_websocket_path: str,
        device_id: str,
        api_base_url: str,
        mode: str,
    ) -> None:
        self.device_id = device_id
        self.topic = f"weather/station/{device_id}/data"
        self.seq = 1
        self.lock = threading.Lock()
        self.current: dict[str, Any] = {
            "temp_c": 28.0,
            "humidity_pct": 60.0,
            "pressure_hpa": 1008.0,
            "rain_raw": 2200,
            "battery_mv": 4050,
        }
        self.interval_sec = 5.0
        self._running = True
        self.mode = mode
        self.api_base_url = api_base_url.rstrip("/")
        self.http = httpx.Client(timeout=5.0)
        self._init_seq_from_backend()

        self.client: mqtt.Client | None = None
        if self.mode == "mqtt":
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=f"panel-sim-{device_id}",
                transport=mqtt_transport,
            )
            if mqtt_username:
                client.username_pw_set(mqtt_username, mqtt_password)
            if mqtt_transport == "websockets":
                client.ws_set_options(path=mqtt_websocket_path)
            if mqtt_tls:
                client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
            client.connect(mqtt_host, mqtt_port, keepalive=60)
            client.loop_start()
            self.client = client

    def _init_seq_from_backend(self) -> None:
        # Avoid 409 conflicts on /api/v1/ingest due to the unique (device_id, seq) constraint.
        if self.mode != "http":
            return
        try:
            resp = self.http.get(
                f"{self.api_base_url}/api/v1/history",
                params={"device_id": self.device_id, "limit": 200},
            )
            resp.raise_for_status()
            rows = resp.json()
            if isinstance(rows, list):
                seqs = [
                    row.get("seq")
                    for row in rows
                    if isinstance(row, dict) and isinstance(row.get("seq"), int)
                ]
                if seqs:
                    self.seq = max(seqs) + 1
        except Exception:
            # If the backend isn't reachable yet, we just start at 1; duplicates will be skipped.
            return

    def _resync_seq_from_backend(self) -> None:
        self._init_seq_from_backend()

    def publish(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        with self.lock:
            if overrides:
                self.current.update(overrides)
            payload = {
                "schema": "weather.v1",
                "device_id": self.device_id,
                "seq": self.seq,
                "ts": int(time.time()),
                "temp_c": float(self.current["temp_c"]),
                "humidity_pct": float(self.current["humidity_pct"]),
                "pressure_hpa": float(self.current["pressure_hpa"]),
                "rain_raw": int(self.current["rain_raw"]),
                "rain": int(self.current["rain_raw"]) < 1400,
                "rssi_dbm": -52,
                "battery_mv": int(self.current["battery_mv"]),
                "fw_version": "esp32-weather-fw-1.1.0",
            }
            if self.mode == "mqtt":
                if self.client is None:
                    raise RuntimeError("MQTT client not initialized")
                info = self.client.publish(self.topic, json.dumps(payload), qos=1, retain=False)
                mqtt_result = info.rc
            else:
                # HTTP fallback for demo environments without working DNS/MQTT.
                resp = self.http.post(f"{self.api_base_url}/api/v1/ingest", json=payload)
                if resp.status_code == 409:
                    # Another run or old DB contents may already own this seq. Resync and retry.
                    self._resync_seq_from_backend()
                    payload["seq"] = self.seq
                    resp = self.http.post(f"{self.api_base_url}/api/v1/ingest", json=payload)
                resp.raise_for_status()
                mqtt_result = 0
            self.seq += 1
            return {"seq": payload["seq"], "mqtt_result": mqtt_result, "payload": payload}

    def run_autopublish(self) -> None:
        while self._running:
            try:
                self.publish()
            except Exception:
                pass
            time.sleep(self.interval_sec)

    def close(self) -> None:
        self._running = False
        if self.client is not None:
            self.client.loop_stop()
            self.client.disconnect()
        self.http.close()


def make_handler(state: SimulatorState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path not in {"/", "/index.html"}:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            if self.path != "/publish":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8")) if raw else {}
                result = state.publish(data if isinstance(data, dict) else None)
                body = json.dumps(result).encode("utf-8")
                self.send_response(HTTPStatus.OK)
            except Exception as exc:  # noqa: BLE001
                body = json.dumps({"error": str(exc)}).encode("utf-8")
                self.send_response(HTTPStatus.BAD_REQUEST)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *args: Any) -> None:
            return

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive MQTT weather simulator with browser sliders.")
    parser.add_argument("--mqtt-host", default="broker.hivemq.com")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--mqtt-username", default=None)
    parser.add_argument("--mqtt-password", default=None)
    parser.add_argument("--mqtt-transport", choices=["tcp", "websockets"], default="tcp")
    parser.add_argument("--mqtt-tls", action="store_true", help="Use TLS. Required for wss:// routes.")
    parser.add_argument("--mqtt-websocket-path", default="/mqtt")
    parser.add_argument("--device-id", default="ws-esp32-001")
    parser.add_argument("--port", type=int, default=8765, help="HTTP port for the local control panel")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000", help="Backend API base URL for HTTP fallback")
    parser.add_argument("--mode", choices=["mqtt", "http"], default="mqtt", help="Publish via MQTT or HTTP (/api/v1/ingest)")
    args = parser.parse_args()

    state = SimulatorState(
        args.mqtt_host,
        args.mqtt_port,
        args.mqtt_username,
        args.mqtt_password,
        args.mqtt_transport,
        args.mqtt_tls,
        args.mqtt_websocket_path,
        args.device_id,
        args.api_base_url,
        args.mode,
    )
    thread = threading.Thread(target=state.run_autopublish, name="autopublish", daemon=True)
    thread.start()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(state))
    print(f"Control panel: http://127.0.0.1:{args.port}")
    if args.mode == "mqtt":
        print(f"MQTT topic: weather/station/{args.device_id}/data")
    else:
        print(f"HTTP ingest: {args.api_base_url.rstrip('/')}/api/v1/ingest")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        state.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
