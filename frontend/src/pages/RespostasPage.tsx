import { useEffect, useState } from "react";
import {
  deleteResposta, listRespostas, marcarLida, marcarNaoLida,
  respostasStats,
} from "../api/endpoints";
import type { Resposta, RespostasStats } from "../api/types";
import ErrorBanner from "../components/ErrorBanner";

type Filter = "todas" | "nao_lidas" | "lidas";

export default function RespostasPage() {
  const [items, setItems] = useState<Resposta[]>([]);
  const [stats, setStats] = useState<RespostasStats | null>(null);
  const [filter, setFilter] = useState<Filter>("nao_lidas");
  const [q, setQ] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  const load = async () => {
    try {
      const processado =
        filter === "lidas" ? true :
        filter === "nao_lidas" ? false : undefined;
      const [rs, st] = await Promise.all([
        listRespostas({ processado, q: q || undefined, limit: 200 }),
        respostasStats(),
      ]);
      setItems(rs); setStats(st);
    } catch (e) { setErr(String(e)); }
  };
  useEffect(() => {
    void load();
    const id = setInterval(load, 15_000);
    return () => clearInterval(id);
    // eslint-disable-next-line
  }, [filter]);

  const doLida = async (r: Resposta) => {
    setBusy(r.id);
    try {
      if (r.processado) await marcarNaoLida(r.id);
      else await marcarLida(r.id);
      await load();
    } catch (e) { setErr(String(e)); }
    finally { setBusy(null); }
  };
  const doDelete = async (r: Resposta) => {
    if (!confirm("Apagar essa resposta?")) return;
    setBusy(r.id);
    try { await deleteResposta(r.id); await load(); }
    catch (e) { setErr(String(e)); }
    finally { setBusy(null); }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Respostas / Feedback</h1>
        <button className="btn" onClick={() => void load()}>Atualizar</button>
      </div>
      <ErrorBanner message={err} onClose={() => setErr(null)} />

      {stats && (
        <div className="card" style={{ display: "flex", gap: 24 }}>
          <Stat label="Não lidas" value={stats.nao_lidas} color="#ef4444" />
          <Stat label="Total" value={stats.total} color="#3b82f6" />
        </div>
      )}

      <div className="card">
        <div className="row" style={{ marginBottom: 12 }}>
          <button className={`btn ${filter === "nao_lidas" ? "primary" : ""}`}
            onClick={() => setFilter("nao_lidas")}>Não lidas</button>
          <button className={`btn ${filter === "lidas" ? "primary" : ""}`}
            onClick={() => setFilter("lidas")}>Lidas</button>
          <button className={`btn ${filter === "todas" ? "primary" : ""}`}
            onClick={() => setFilter("todas")}>Todas</button>
          <span className="spacer" />
          <input placeholder="buscar no texto" value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") void load(); }}
            style={{ maxWidth: 240, padding: "8px 10px",
                     border: "1px solid #d1d5db", borderRadius: 6 }} />
          <button className="btn" onClick={() => void load()}>Buscar</button>
        </div>

        {items.length === 0 ? (
          <div className="empty">
            {filter === "nao_lidas"
              ? "Nenhuma resposta não lida. 👍"
              : "Nenhuma resposta ainda."}
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Quando</th>
                <th>Cliente</th>
                <th>Mensagem</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id} style={{
                  background: r.processado ? "transparent" : "#fffbeb",
                }}>
                  <td className="muted" style={{ fontSize: 11, whiteSpace: "nowrap" }}>
                    {new Date(r.recebido_em).toLocaleString("pt-BR")}
                  </td>
                  <td>
                    <div>{r.cliente_nome ?? <span className="muted">desconhecido</span>}</div>
                    <div className="muted" style={{ fontSize: 11 }}>{r.telefone_origem}</div>
                  </td>
                  <td style={{ maxWidth: 480 }}>
                    <div style={{
                      fontWeight: r.processado ? 400 : 600,
                      whiteSpace: "pre-wrap",
                    }}>
                      {r.mensagem_texto}
                    </div>
                    {r.tipo_mensagem && r.tipo_mensagem !== "text" && (
                      <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
                        tipo: {r.tipo_mensagem}
                      </div>
                    )}
                  </td>
                  <td>
                    <span className={`badge ${r.processado ? "muted" : "warn"}`}>
                      {r.processado ? "lida" : "nova"}
                    </span>
                  </td>
                  <td className="btn-row" style={{ justifyContent: "flex-end" }}>
                    <button className="btn" disabled={busy === r.id}
                      onClick={() => void doLida(r)}>
                      {r.processado ? "Marcar não lida" : "Marcar lida"}
                    </button>
                    <button className="btn danger" disabled={busy === r.id}
                      onClick={() => void doDelete(r)}>Del</button>
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

function Stat({ label, value, color }: {
  label: string; value: number; color: string;
}) {
  return (
    <div style={{ minWidth: 120 }}>
      <div className="muted" style={{ fontSize: 11, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}
