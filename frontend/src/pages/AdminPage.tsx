import { useEffect, useState } from "react";
import {
  createBackup, dispatchComemorativo, dispatchExpiracao, listBackups,
} from "../api/endpoints";
import type { Backup, DispatchStats } from "../api/types";
import ErrorBanner from "../components/ErrorBanner";

export default function AdminPage() {
  const [backups, setBackups] = useState<Backup[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [lastDispatch, setLastDispatch] = useState<
    { which: string; stats: DispatchStats } | null
  >(null);

  const load = async () => {
    try { setBackups(await listBackups()); }
    catch (e) { setError(String(e)); }
  };
  useEffect(() => { void load(); }, []);

  const doBackup = async () => {
    setBusy(true);
    try {
      const descricao = prompt("Descrição (opcional):") ?? undefined;
      await createBackup(descricao || undefined);
      await load();
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  };

  const doDispatch = async (which: "comemorativo" | "expiracao") => {
    setBusy(true);
    try {
      const stats = which === "comemorativo"
        ? await dispatchComemorativo()
        : await dispatchExpiracao();
      setLastDispatch({ which, stats });
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <div className="page-header"><h1>Admin</h1></div>
      <ErrorBanner message={error} onClose={() => setError(null)} />

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Backup do banco</h3>
        <p className="muted">
          Copia <code>database/followuai.db</code> para a pasta <code>backups/</code>.
          Recomendado fazer backup periodicamente.
        </p>
        <button className="btn primary" disabled={busy} onClick={() => void doBackup()}>
          Criar backup agora
        </button>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Disparar jobs manualmente</h3>
        <p className="muted">
          Roda os jobs como se fosse o horário agendado. Útil para testar templates.
        </p>
        <div className="btn-row">
          <button className="btn" disabled={busy}
            onClick={() => void doDispatch("comemorativo")}>
            Disparar Comemorativo (hoje)
          </button>
          <button className="btn" disabled={busy}
            onClick={() => void doDispatch("expiracao")}>
            Disparar Expiração (hoje)
          </button>
        </div>
        {lastDispatch && (
          <div style={{ marginTop: 12 }}>
            <strong>{lastDispatch.which}:</strong>{" "}
            enviados {lastDispatch.stats.enviados},{" "}
            pendentes {lastDispatch.stats.pendentes},{" "}
            falhas {lastDispatch.stats.falhas},{" "}
            ignorados {lastDispatch.stats.ignorados}
          </div>
        )}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Histórico de backups</h3>
        {backups.length === 0 ? (
          <div className="empty">Nenhum backup ainda.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Quando</th>
                <th>Arquivo</th>
                <th>Tamanho</th>
                <th>Descrição</th>
              </tr>
            </thead>
            <tbody>
              {backups.map((b) => (
                <tr key={b.id}>
                  <td>{new Date(b.criado_em).toLocaleString("pt-BR")}</td>
                  <td className="muted" style={{ fontFamily: "monospace", fontSize: 11 }}>
                    {b.caminho_arquivo}
                  </td>
                  <td>{b.tamanho_bytes ? `${(b.tamanho_bytes / 1024).toFixed(1)} KB` : "—"}</td>
                  <td>{b.descricao ?? <span className="muted">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
