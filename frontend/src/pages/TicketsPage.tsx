import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../AuthContext";
import { api, ApiError } from "../api/client";
import { EmptyState, ErrorMessage, Loading } from "../components/StateMessage";
import type { Machine, Ticket } from "../api/types";

export function TicketsPage() {
  const { me } = useAuth();
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [machineId, setMachineId] = useState("");
  const [symptoms, setSymptoms] = useState("");
  const [errorCode, setErrorCode] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function loadTickets() {
    try {
      const rows = await api.get<Ticket[]>("/tickets");
      setTickets(rows);
    } catch {
      setError("Could not load tickets.");
    }
  }

  useEffect(() => {
    loadTickets();
    api.get<Machine[]>("/machines").then(setMachines).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!machineId || symptoms.trim().length < 3) {
      setFormError("Choose a machine and describe the symptoms (at least 3 characters).");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/tickets", { machine_id: machineId, symptoms: symptoms.trim(), error_code: errorCode.trim() || null });
      setSymptoms("");
      setErrorCode("");
      await loadTickets();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not submit the ticket.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section>
      <h1>Tickets</h1>

      {me?.role === "customer" && (
        <form className="card" onSubmit={onSubmit} aria-label="Report a machine problem">
          <h2>Report a problem</h2>
          <div className="field">
            <label htmlFor="machine">Machine</label>
            <select id="machine" value={machineId} onChange={(e) => setMachineId(e.target.value)} required>
              <option value="">Select a machine</option>
              {machines.map((m) => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="symptoms">Symptoms</label>
            <textarea id="symptoms" rows={3} value={symptoms} onChange={(e) => setSymptoms(e.target.value)} required placeholder="e.g. motor keeps stopping" />
          </div>
          <div className="field">
            <label htmlFor="error-code">Error code (optional)</label>
            <input id="error-code" value={errorCode} onChange={(e) => setErrorCode(e.target.value)} placeholder="e.g. E-104" />
          </div>
          {formError && <p role="alert" style={{ color: "var(--crit)" }}>{formError}</p>}
          <button type="submit" disabled={submitting}>{submitting ? "Submitting..." : "Submit ticket"}</button>
        </form>
      )}

      {error && <ErrorMessage message={error} />}
      {!error && tickets === null && <Loading />}
      {!error && tickets !== null && tickets.length === 0 && <EmptyState message="No tickets yet." />}
      {!error && tickets !== null && tickets.length > 0 && (
        <div className="card" style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr><th>Machine</th><th>Symptoms</th><th>Error code</th><th>Status</th><th>Reported</th></tr>
            </thead>
            <tbody>
              {tickets.map((t) => (
                <tr key={t.id}>
                  <td>{t.machine_name}</td>
                  <td>{t.symptoms}</td>
                  <td>{t.error_code ?? "-"}</td>
                  <td><span className={`badge ${t.status === "open" ? "missing" : t.status === "linked" ? "fault" : "healthy"}`}>{t.status}</span></td>
                  <td>{new Date(t.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
