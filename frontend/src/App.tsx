import { NavLink, Route, Routes, Navigate } from "react-router-dom";
import ClientesPage from "./pages/ClientesPage";
import TelefonesPage from "./pages/TelefonesPage";
import TemplatesPage from "./pages/TemplatesPage";
import EventosPage from "./pages/EventosPage";
import MeuNegocioPage from "./pages/MeuNegocioPage";
import AgendaPage from "./pages/AgendaPage";
import FilaPage from "./pages/FilaPage";
import RespostasPage from "./pages/RespostasPage";
import RelatoriosPage from "./pages/RelatoriosPage";
import AdminPage from "./pages/AdminPage";
import HealthBadge from "./components/HealthBadge";

const NAV = [
  { to: "/agenda",     label: "Agenda" },
  { to: "/fila",       label: "Fila" },
  { to: "/respostas",  label: "Respostas" },
  { to: "/clientes",   label: "Clientes" },
  { to: "/telefones",  label: "Telefones" },
  { to: "/eventos",    label: "Eventos" },
  { to: "/templates",  label: "Templates" },
  { to: "/meu-negocio", label: "Meu Negócio" },
  { to: "/relatorios", label: "Relatórios" },
  { to: "/admin",      label: "Admin" },
];

export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-name">FollowUai</span>
          <span className="brand-tag">o follow-up que seu negócio merece</span>
        </div>
        <nav>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <HealthBadge />
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/agenda" replace />} />
          <Route path="/agenda"      element={<AgendaPage />} />
          <Route path="/fila"        element={<FilaPage />} />
          <Route path="/respostas"   element={<RespostasPage />} />
          <Route path="/clientes"    element={<ClientesPage />} />
          <Route path="/telefones"   element={<TelefonesPage />} />
          <Route path="/eventos"     element={<EventosPage />} />
          <Route path="/templates"   element={<TemplatesPage />} />
          <Route path="/meu-negocio" element={<MeuNegocioPage />} />
          <Route path="/relatorios"  element={<RelatoriosPage />} />
          <Route path="/admin"       element={<AdminPage />} />
        </Routes>
      </main>
    </div>
  );
}
