export type Role = "customer" | "technician";
export type FaultType = "overheating" | "overload" | "vibration" | "missing_telemetry";
export type IncidentStatus = "open" | "resolved";
export type Severity = "warning" | "critical";
export type TicketStatus = "open" | "linked" | "closed";

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: Role;
  factory_id: string;
  display_name: string;
}

export interface Me {
  id: string;
  email: string;
  role: Role;
  factory_id: string;
  factory_name: string;
  display_name: string;
}

export interface Machine {
  id: string;
  name: string;
  machine_type: string;
  last_seen_at: string | null;
  health: "healthy" | "fault" | "missing" | "unknown";
}

export interface Reading {
  ts: string;
  temperature_c: number;
  current_a: number;
  vibration_mm_s: number;
}

export interface Ticket {
  id: string;
  machine_id: string;
  machine_name: string;
  symptoms: string;
  error_code: string | null;
  status: TicketStatus;
  linked_incident_id: string | null;
  created_at: string;
}

export interface Incident {
  id: string;
  machine_id: string;
  machine_name: string;
  fault_type: FaultType;
  severity: Severity;
  status: IncidentStatus;
  opened_at: string;
  resolved_at: string | null;
  observations: { summary?: string };
  evidence: Record<string, unknown>;
  suspected_causes: string[];
  next_checks: string[];
  checklist: { step: string; done: boolean }[];
  recovery_verified: boolean;
}

export interface FaultInjection {
  id: number;
  machine_id: string;
  machine_name: string;
  fault_type: FaultType;
  active: boolean;
  injected_at: string;
  removed_at: string | null;
}
