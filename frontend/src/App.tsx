import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { Nav } from "./components/Nav";
import { Loading } from "./components/StateMessage";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { TicketsPage } from "./pages/TicketsPage";
import { IncidentsPage } from "./pages/IncidentsPage";
import { IncidentDetailPage } from "./pages/IncidentDetailPage";
import { FaultInjectionPage } from "./pages/FaultInjectionPage";

function Protected({ children }: { children: React.ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <Loading label="Checking session..." />;
  if (!me) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <div className="app-shell">
      <Nav />
      <main className="content">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={<Protected><DashboardPage /></Protected>} />
          <Route path="/tickets" element={<Protected><TicketsPage /></Protected>} />
          <Route path="/incidents" element={<Protected><IncidentsPage /></Protected>} />
          <Route path="/incidents/:id" element={<Protected><IncidentDetailPage /></Protected>} />
          <Route path="/fault-injection" element={<Protected><FaultInjectionPage /></Protected>} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}
