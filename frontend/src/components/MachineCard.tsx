import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import type { Machine, Reading } from "../api/types";
import { Loading } from "./StateMessage";

function fmtTime(ts: string) {
  return new Date(ts).toLocaleTimeString();
}

export function MachineCard({ machine }: { machine: Machine }) {
  const [readings, setReadings] = useState<Reading[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const rows = await api.get<Reading[]>(`/machines/${machine.id}/readings?limit=60`);
        if (!cancelled) setReadings(rows);
      } catch {
        if (!cancelled) setError("Could not load readings for this machine.");
      }
    }
    load();
    const interval = setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [machine.id]);

  const data = (readings ?? []).map((r) => ({ ...r, time: fmtTime(r.ts) }));
  const latest = readings && readings.length > 0 ? readings[readings.length - 1] : null;

  return (
    <article className="card" aria-label={`Machine ${machine.name}`}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>{machine.name}</h3>
        <span className={`badge ${machine.health}`}>{machine.health}</span>
      </div>
      <p style={{ color: "var(--text-dim)", fontSize: "0.85rem" }}>
        Last seen: {machine.last_seen_at ? new Date(machine.last_seen_at).toLocaleString() : "never"}
      </p>

      {error && <p role="alert" style={{ color: "var(--crit)" }}>{error}</p>}
      {!error && readings === null && <Loading label="Loading readings..." />}
      {!error && readings !== null && readings.length === 0 && (
        <p style={{ color: "var(--text-dim)" }}>No readings yet. Start the simulator to see live data.</p>
      )}

      {latest && (
        <div className="grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", gap: 8, marginBottom: 10 }}>
          <div className="kv"><span>Temp</span><strong>{latest.temperature_c.toFixed(1)}C</strong></div>
          <div className="kv"><span>Current</span><strong>{latest.current_a.toFixed(1)}A</strong></div>
          <div className="kv"><span>Vibration</span><strong>{latest.vibration_mm_s.toFixed(1)}mm/s</strong></div>
        </div>
      )}

      {data.length > 1 && (
        <>
          <ChartRow title="Temperature (C)" dataKey="temperature_c" data={data} color="#f87171" />
          <ChartRow title="Current (A)" dataKey="current_a" data={data} color="#38bdf8" />
          <ChartRow title="Vibration (mm/s)" dataKey="vibration_mm_s" data={data} color="#fbbf24" />
        </>
      )}
    </article>
  );
}

function ChartRow({ title, dataKey, data, color }: { title: string; dataKey: string; data: Record<string, unknown>[]; color: string }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>{title}</div>
      <ResponsiveContainer width="100%" height={70}>
        <LineChart data={data}>
          <XAxis dataKey="time" hide />
          <YAxis hide domain={["auto", "auto"]} />
          <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
          <Line type="monotone" dataKey={dataKey} stroke={color} dot={false} strokeWidth={2} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
