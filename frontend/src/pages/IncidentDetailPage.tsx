import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "../AuthContext";
import { api } from "../api/client";
import { ErrorMessage, Loading } from "../components/StateMessage";
import type { Incident } from "../api/types";

export function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { me } = useAuth();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!id) return;
    try {
      const row = await api.get<Incident>(`/incidents/${id}`);
      setIncident(row);
    } catch {
      setError("Could not load this incident.");
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function toggleStep(index: number, done: boolean) {
    if (!id) return;
    await api.post(`/incidents/${id}/checklist`, { step_index: index, done });
    await load();
  }

  if (error) return <ErrorMessage message={error} />;
  if (!incident) return <Loading />;

  return (
    <section>
      <h1>
        {incident.machine_name} — {incident.fault_type.replace("_", " ")}{" "}
        <span className={`badge ${incident.status}`}>{incident.status}</span>{" "}
        <span className={`badge ${incident.severity}`}>{incident.severity}</span>
      </h1>
      <p style={{ color: "var(--text-dim)" }}>
        Opened {new Date(incident.opened_at).toLocaleString()}
        {incident.resolved_at && <> · Resolved {new Date(incident.resolved_at).toLocaleString()}</>}
        {incident.recovery_verified && <> · Recovery verified after a sustained healthy observation window</>}
      </p>

      <div className="card">
        <h2>Observations</h2>
        <p>{incident.observations.summary ?? "No summary available."}</p>
      </div>

      <div className="card">
        <h2>Evidence</h2>
        <p style={{ color: "var(--text-dim)", fontSize: "0.85rem" }}>
          FactoryOps uses explicit threshold rules with persistence and hysteresis — not a trained model — and never
          reports a confidence probability.
        </p>
        {Object.entries(incident.evidence).map(([k, v]) => (
          <div className="kv" key={k}><span>{k}</span><strong>{String(v)}</strong></div>
        ))}
      </div>

      <div className="card">
        <h2>Suspected causes</h2>
        <ul>{incident.suspected_causes.map((c, i) => <li key={i}>{c}</li>)}</ul>
      </div>

      <div className="card">
        <h2>Next checks</h2>
        <ul>{incident.next_checks.map((c, i) => <li key={i}>{c}</li>)}</ul>
      </div>

      <div className="card">
        <h2>Guided troubleshooting checklist</h2>
        {incident.checklist.map((step, i) => (
          <div className="checklist-item" key={i}>
            <input
              type="checkbox"
              id={`step-${i}`}
              checked={step.done}
              disabled={me?.role !== "technician"}
              onChange={(e) => toggleStep(i, e.target.checked)}
            />
            <label htmlFor={`step-${i}`} style={{ margin: 0, color: step.done ? "var(--ok)" : "var(--text)" }}>{step.step}</label>
          </div>
        ))}
        {me?.role !== "technician" && (
          <p style={{ color: "var(--text-dim)", fontSize: "0.85rem" }}>Only technicians can update the checklist.</p>
        )}
      </div>
    </section>
  );
}
