import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { EmptyState, ErrorMessage, Loading } from "../components/StateMessage";
import type { Incident } from "../api/types";

export function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      if (severityFilter) params.set("severity", severityFilter);
      try {
        const rows = await api.get<Incident[]>(`/incidents?${params.toString()}`);
        if (!cancelled) setIncidents(rows);
      } catch {
        if (!cancelled) setError("Could not load incidents.");
      }
    }
    load();
    const interval = setInterval(load, 6000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [statusFilter, severityFilter]);

  return (
    <section>
      <h1>Incidents</h1>
      <div className="filters">
        <select aria-label="Filter by status" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="resolved">Resolved</option>
        </select>
        <select aria-label="Filter by severity" value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
          <option value="">All severities</option>
          <option value="warning">Warning</option>
          <option value="critical">Critical</option>
        </select>
      </div>

      {error && <ErrorMessage message={error} />}
      {!error && incidents === null && <Loading />}
      {!error && incidents !== null && incidents.length === 0 && <EmptyState message="No incidents match these filters." />}
      {!error && incidents !== null && incidents.length > 0 && (
        <div className="card" style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr><th>Machine</th><th>Fault</th><th>Severity</th><th>Status</th><th>Opened</th><th></th></tr>
            </thead>
            <tbody>
              {incidents.map((i) => (
                <tr key={i.id}>
                  <td>{i.machine_name}</td>
                  <td>{i.fault_type.replace("_", " ")}</td>
                  <td><span className={`badge ${i.severity}`}>{i.severity}</span></td>
                  <td><span className={`badge ${i.status}`}>{i.status}</span></td>
                  <td>{new Date(i.opened_at).toLocaleString()}</td>
                  <td><Link to={`/incidents/${i.id}`}>View diagnosis</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
