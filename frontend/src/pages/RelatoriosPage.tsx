import { useEffect, useState } from "react";
import { enviosStats, listEnvios } from "../api/endpoints";
import type { Envio, ModuloStats } from "../api/types";
import ErrorBanner from "../components/ErrorBanner";

export default function RelatoriosPage() {
  const [stats, setStats] = useState<ModuloStats[]>([]);
  const [envios, setEnvios] = useState<Envio[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const [s, e] = await Promise.all([enviosStats(), listEnvios({ limit: 50 })]);
      setStats(s); setEnvios(e);
    } catch (e) { setError(String(e)); }
  };
  useEffect(() => { void load(); }, []);

  return (
    <div>
      <div className="page-header">
        <h1>Relatórios</h1>
        <button className="btn" onClick={() => void load()}>Atualizar</button>
      </div>
      <ErrorBanner message={error} onClose={() => setError(null)} />

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Envios por módulo</h3>
        {stats.length === 0 ? (
          <div className="empty">Nenhum envio ainda.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Módulo</th>
                <th>Total</th>
                <th>Enviados</th>
                <th>Pendentes</th>
                <th>Falhas</th>
                <th>Bloqueados</th>
              </tr>
            </thead>
            <tbody>
              {stats.map((s) => (
                <tr key={s.modulo}>
                  <td><span className="badge muted">{s.modulo}</span></td>
                  <td>{s.total_envios}</td>
                  <td><span className="badge ok">{s.enviados}</span></td>
                  <td>{s.pendentes}</td>
                  <td>{s.falhas > 0 ? <span className="badge bad">{s.falhas}</span> : 0}</td>
                  <td>{s.bloqueados}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Envios recentes (50)</h3>
        {envios.length === 0 ? (
          <div className="empty">Nenhum envio.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Quando</th>
                <th>Módulo</th>
                <th>Destino</th>
                <th>Status</th>
                <th>Mensagem</th>
              </tr>
            </thead>
            <tbody>
              {envios.map((e) => (
                <tr key={e.id}>
                  <td>{e.enviado_em ? new Date(e.enviado_em).toLocaleString("pt-BR")
                    : <span className="muted">—</span>}</td>
                  <td><span className="badge muted">{e.modulo}</span></td>
                  <td>{e.telefone_destino}</td>
                  <td>
                    <span className={`badge ${
                      e.status === "enviado" ? "ok" :
                      e.status === "falha" ? "bad" :
                      e.status === "bloqueado" ? "bad" : "warn"
                    }`}>{e.status}</span>
                  </td>
                  <td className="muted" style={{ maxWidth: 360 }}>
                    {e.mensagem_texto.slice(0, 80)}{e.mensagem_texto.length > 80 ? "…" : ""}
                    {e.erro && <div style={{ color: "#991b1b" }}>err: {e.erro.slice(0, 80)}</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
