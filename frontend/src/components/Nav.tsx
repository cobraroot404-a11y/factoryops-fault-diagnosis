import { NavLink } from "react-router-dom";
import { useAuth } from "../AuthContext";

export function Nav() {
  const { me, logout } = useAuth();
  if (!me) return null;
  return (
    <header className="topnav">
      <div className="brand">FactoryOps <span className="simulated-tag">simulated demo data</span></div>
      <nav aria-label="Primary">
        <NavLink to="/dashboard" className={({ isActive }) => (isActive ? "active" : "")}>Dashboard</NavLink>
        <NavLink to="/tickets" className={({ isActive }) => (isActive ? "active" : "")}>Tickets</NavLink>
        <NavLink to="/incidents" className={({ isActive }) => (isActive ? "active" : "")}>Incidents</NavLink>
        {me.role === "technician" && (
          <NavLink to="/fault-injection" className={({ isActive }) => (isActive ? "active" : "")}>Fault Injection</NavLink>
        )}
      </nav>
      <div className="who">
        <span>{me.display_name} · {me.role} · {me.factory_name}</span>
        <button className="secondary" onClick={logout}>Sign out</button>
      </div>
    </header>
  );
}
