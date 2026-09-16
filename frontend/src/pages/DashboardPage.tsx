import { useEffect, useState } from "react";
import { api } from "../api/client";
import { MachineCard } from "../components/MachineCard";
import { EmptyState, ErrorMessage, Loading } from "../components/StateMessage";
import type { Machine } from "../api/types";

export function DashboardPage() {
  const [machines, setMachines] = useState<Machine[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const rows = await api.get<Machine[]>("/machines");
        if (!cancelled) setMachines(rows);
      } catch {
        if (!cancelled) setError("Could not load machines.");
      }
    }
    load();
    const interval = setInterval(load, 8000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (error) return <ErrorMessage message={error} />;
  if (machines === null) return <Loading label="Loading machines..." />;
  if (machines.length === 0) return <EmptyState message="No machines have been seeded for your factory yet." />;

  return (
    <section>
      <h1>Machine health</h1>
      <div className="grid">
        {machines.map((m) => (
          <MachineCard key={m.id} machine={m} />
        ))}
      </div>
    </section>
  );
}
