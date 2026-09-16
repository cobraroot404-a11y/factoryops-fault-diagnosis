import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ErrorMessage, Loading } from "../components/StateMessage";
import type { FaultInjection, FaultType, Machine } from "../api/types";

const FAULT_TYPES: FaultType[] = ["overheating", "overload", "vibration", "missing_telemetry"];

export function FaultInjectionPage() {
  const [machines, setMachines] = useState<Machine[] | null>(null);
  const [active, setActive] = useState<FaultInjection[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  async function loadAll() {
    try {
      const [m, a] = await Promise.all([
        api.get<Machine[]>("/machines"),
        api.get<FaultInjection[]>("/admin/fault-injections"),
      ]);
      setMachines(m);
      setActive(a);
    } catch {
      setError("Could not load fault-injection controls. This page requires the technician role.");
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  function findActive(machineId: string, faultType: FaultType) {
    return active.find((a) => a.machine_id === machineId && a.fault_type === faultType && a.active);
  }

  async function inject(machineId: string, faultType: FaultType) {
    const key = `${machineId}-${faultType}`;
    setBusyKey(key);
    try {
      await api.post("/admin/fault-injections", { machine_id: machineId, fault_type: faultType });
      await loadAll();
    } finally {
      setBusyKey(null);
    }
  }

  async function remove(injectionId: number) {
    setBusyKey(`remove-${injectionId}`);
    try {
      await api.del(`/admin/fault-injections/${injectionId}`);
      await loadAll();
    } finally {
      setBusyKey(null);
    }
  }

  if (error) return <ErrorMessage message={error} />;
  if (machines === null) return <Loading />;

  return (
    <section>
      <h1>Authorized demo fault injection</h1>
      <p style={{ color: "var(--text-dim)" }}>
        Technician-only controls. Injecting a fault alters the simulator's simulated output for that machine so the
        diagnosis pipeline can be exercised end-to-end without physical hardware.
      </p>
      <div className="card" style={{ overflowX: "auto" }}>
        <table>
          <thead>
            <tr>
              <th>Machine</th>
              {FAULT_TYPES.map((f) => <th key={f}>{f.replace("_", " ")}</th>)}
            </tr>
          </thead>
          <tbody>
            {machines.map((m) => (
              <tr key={m.id}>
                <td>{m.name}</td>
                {FAULT_TYPES.map((f) => {
                  const existing = findActive(m.id, f);
                  const key = `${m.id}-${f}`;
                  return (
                    <td key={f}>
                      {existing ? (
                        <button className="danger" disabled={busyKey === `remove-${existing.id}`} onClick={() => remove(existing.id)}>
                          Remove
                        </button>
                      ) : (
                        <button className="secondary" disabled={busyKey === key} onClick={() => inject(m.id, f)}>
                          Inject
                        </button>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
