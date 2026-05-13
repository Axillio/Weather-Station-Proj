"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Device = {
  id: string;
  name?: string | null;
};

type DeviceStatus = {
  device_id: string;
  is_online: boolean;
  status: string;
  last_seen_at: string | null;
  seconds_since_seen: number | null;
  rssi_dbm: number | null;
  rssi_status: string;
  battery_mv: number | null;
  battery_status: string;
  fw_version: string | null;
  last_seq: number | null;
};

type Reading = {
  id: number;
  device_id: string;
  seq: number | null;
  ts: number;
  temp_c: number | null;
  humidity_pct: number | null;
  pressure_hpa: number | null;
  rain: boolean | null;
  rain_raw: number | null;
  rssi_dbm: number | null;
  battery_mv: number | null;
  fw_version: string | null;
  is_valid: boolean;
  created_at: string;
};

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

function formatNumber(value: number | null | undefined, suffix: string, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return `${value.toFixed(digits)}${suffix}`;
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "--";
  }
  return new Date(value).toLocaleString();
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function TrendCanvas({ readings }: { readings: Reading[] }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const pad = 34;
    const points = readings.filter((reading) => reading.temp_c !== null).reverse();

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#fbfcfd";
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = "#dce3e8";
    ctx.lineWidth = 1;

    for (let i = 0; i <= 4; i++) {
      const y = pad + ((height - pad * 2) * i) / 4;
      ctx.beginPath();
      ctx.moveTo(pad, y);
      ctx.lineTo(width - pad, y);
      ctx.stroke();
    }

    if (points.length < 2) {
      ctx.fillStyle = "#66727f";
      ctx.font = "16px system-ui";
      ctx.fillText("Waiting for more readings", pad, height / 2);
      return;
    }

    const values = points.map((reading) => Number(reading.temp_c));
    const min = Math.min(...values) - 1;
    const max = Math.max(...values) + 1;
    const xStep = (width - pad * 2) / Math.max(points.length - 1, 1);

    ctx.strokeStyle = "#0f766e";
    ctx.lineWidth = 3;
    ctx.beginPath();

    points.forEach((reading, index) => {
      const x = pad + xStep * index;
      const y = height - pad - ((Number(reading.temp_c) - min) / (max - min || 1)) * (height - pad * 2);
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });

    ctx.stroke();
    ctx.fillStyle = "#17212b";
    ctx.font = "13px system-ui";
    ctx.fillText(`${max.toFixed(1)} C`, 6, pad + 4);
    ctx.fillText(`${min.toFixed(1)} C`, 6, height - pad + 4);
  }, [readings]);

  return <canvas ref={canvasRef} width={900} height={320} />;
}

export default function DashboardPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [deviceId, setDeviceId] = useState("ws-esp32-001");
  const [status, setStatus] = useState<DeviceStatus | null>(null);
  const [history, setHistory] = useState<Reading[]>([]);
  const [error, setError] = useState<string | null>(null);

  const latest = history[0];

  const statusClass = useMemo(() => {
    if (!status?.is_online) return "dot dotDown";
    return "dot dotUp";
  }, [status]);

  async function refresh(selectedDeviceId = deviceId) {
    try {
      const [nextStatus, nextHistory] = await Promise.all([
        fetchJson<DeviceStatus>(`/api/v1/devices/${encodeURIComponent(selectedDeviceId)}/status`),
        fetchJson<Reading[]>(`/api/v1/history?device_id=${encodeURIComponent(selectedDeviceId)}&limit=25`),
      ]);
      setStatus(nextStatus);
      setHistory(nextHistory);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reach API");
    }
  }

  useEffect(() => {
    fetchJson<Device[]>("/api/v1/devices")
      .then((loadedDevices) => {
        setDevices(loadedDevices);
        if (loadedDevices[0]) {
          setDeviceId(loadedDevices[0].id);
          return refresh(loadedDevices[0].id);
        }
        return undefined;
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to reach API"));
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => refresh(), 5000);
    return () => window.clearInterval(timer);
  }, [deviceId]);

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <h1>Weather Station</h1>
          <p>{deviceId}</p>
        </div>
        <div className="statusWrap">
          <span className={statusClass} />
          <span>{error ? "API unavailable" : status?.is_online ? "Online" : "Down"}</span>
        </div>
      </header>

      <section className="toolbar">
        <label htmlFor="device">Device</label>
        <select
          id="device"
          value={deviceId}
          onChange={(event) => {
            setDeviceId(event.target.value);
            refresh(event.target.value);
          }}
        >
          {devices.map((device) => (
            <option key={device.id} value={device.id}>
              {device.name ? `${device.name} (${device.id})` : device.id}
            </option>
          ))}
        </select>
        <button type="button" onClick={() => refresh()}>
          Refresh
        </button>
      </section>

      {error ? <div className="errorBanner">{error}</div> : null}

      <section className="metrics" aria-label="Latest sensor readings">
        <article className="metric">
          <span>Temperature</span>
          <strong>{formatNumber(latest?.temp_c, " C")}</strong>
        </article>
        <article className="metric">
          <span>Humidity</span>
          <strong>{formatNumber(latest?.humidity_pct, "%")}</strong>
        </article>
        <article className="metric">
          <span>Pressure</span>
          <strong>{formatNumber(latest?.pressure_hpa, " hPa")}</strong>
        </article>
        <article className="metric">
          <span>Rain</span>
          <strong>{latest ? (latest.rain ? "Detected" : "Clear") : "--"}</strong>
        </article>
      </section>

      <section className="grid">
        <article className="panel">
          <div className="panelHead">
            <h2>Live Trend</h2>
            <span>{latest ? `Updated ${formatDate(latest.created_at)}` : "Waiting for data"}</span>
          </div>
          <TrendCanvas readings={history} />
        </article>

        <article className="panel">
          <div className="panelHead">
            <h2>Connection</h2>
          </div>
          <dl className="statusList">
            <div>
              <dt>Last seen</dt>
              <dd>{status?.last_seen_at ? `${formatDate(status.last_seen_at)} (${status.seconds_since_seen}s ago)` : "--"}</dd>
            </div>
            <div>
              <dt>Wi-Fi RSSI</dt>
              <dd className={status?.rssi_status === "good" ? "good" : status?.rssi_status === "weak" ? "weak" : "bad"}>
                {status?.rssi_dbm === null || status?.rssi_dbm === undefined ? "--" : `${status.rssi_dbm} dBm`}
              </dd>
            </div>
            <div>
              <dt>Network</dt>
              <dd>{status?.rssi_status ?? "--"}</dd>
            </div>
            <div>
              <dt>Battery</dt>
              <dd>{status?.battery_mv === null || status?.battery_mv === undefined ? "--" : `${status.battery_mv} mV`}</dd>
            </div>
            <div>
              <dt>Firmware</dt>
              <dd>{status?.fw_version ?? "--"}</dd>
            </div>
            <div>
              <dt>Last seq</dt>
              <dd>{status?.last_seq ?? "--"}</dd>
            </div>
          </dl>
        </article>
      </section>

      <section className="panel">
        <div className="panelHead">
          <h2>Recent Readings</h2>
          <span>{history.length} rows</span>
        </div>
        <div className="tableWrap">
          <table>
            <thead>
              <tr>
                <th>Seq</th>
                <th>Received</th>
                <th>Temp</th>
                <th>Humidity</th>
                <th>Pressure</th>
                <th>Rain</th>
                <th>RSSI</th>
                <th>Valid</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan={8}>No data yet</td>
                </tr>
              ) : (
                history.map((reading) => (
                  <tr key={reading.id}>
                    <td>{reading.seq ?? "--"}</td>
                    <td>{formatDate(reading.created_at)}</td>
                    <td>{formatNumber(reading.temp_c, " C")}</td>
                    <td>{formatNumber(reading.humidity_pct, "%")}</td>
                    <td>{formatNumber(reading.pressure_hpa, " hPa")}</td>
                    <td>{reading.rain ? "Yes" : "No"}</td>
                    <td>{reading.rssi_dbm ?? "--"}</td>
                    <td className={reading.is_valid ? "good" : "bad"}>{reading.is_valid ? "Yes" : "No"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
