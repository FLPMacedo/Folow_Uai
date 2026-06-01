import { useEffect, useState } from "react";
import {
  enviarAgora, getFila, marcarEnviadoManual, retryEnvio,
} from "../api/endpoints";
import type { FilaItem, FilaResponse } from "../api/types";
import ErrorBanner from "../components/ErrorBanner";

export default function FilaPage() {
  const [data, setData] = useState<FilaResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  const load = async () => {
    try {
      setData(await getFila({
        incluir_falhas: true,
        incluir_pendentes: true,
        incluir_bloqueados: true,
      }));
    } catch (e) { setErr(String(e)); }
  };
  useEffect(() => {
    void load();
    const id = setInterval(load, 10_000);  // refresh a cada 10s
    return () => clearInterval(id);
  }, []);

  const doRetry = async (it: FilaItem) => {
    setBusy(it.id);
    try { await retryEnvio(it.id); await load(); }
    catch (e) { setErr(String(e)); }
    finally { setBusy(null); }
  };
  const doMarcar = async (it: FilaItem) => {
    const nota = prompt(`Marcar envio #${it.id} como enviado manualmente. Nota (opc):`);
    if (nota === null) return;
    setBusy(it.id);
    try { await marcarEnviadoManual(it.id, nota || undefined); await load(); }
    catch (e) { setErr(String(e)); }
    finally { setBusy(null); }
  };
  const doEnviar = async (it: FilaItem) => {
    if (!confirm(`Enviar agora pelo Sender? Para ${it.cliente_nome ?? it.telefone_destino}`)) return;
    setBusy(it.id);
    try {
      const r = await enviarAgora(it.id);
      alert(`Resultado: ${r.status_novo}`);
      await load();
    }
    catch (e) { setErr(String(e)); }
    finally { setBusy(null); }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Fila de trabalho</h1>
        <button className="btn" onClick={() => void load()}>Atualizar</button>
      </div>
      <ErrorBanner message={err} onClose={() => setErr(null)} />

      {!data ? (
        <div className="empty">Carregando…</div>
      ) : (
        <>
          <Sumario data={data} />
          <Section title="🕓 Pendentes" subtitle="Aguardando janela de envio (cooldown, limite, horário)"
            items={data.pendentes} busy={busy}
            onRetry={null} onMarcar={doMarcar} onEnviar={doEnviar} />
          <Section title="⚠ Falhas" subtitle="Evolution rejeitou ou rede caiu"
            items={data.falhas} busy={busy}
            onRetry={doRetry} onMarcar={doMarcar} onEnviar={doEnviar} />
          {data.bloqueados.length > 0 && (
            <Section title="⛔ Bloqueados" subtitle="WhatsApp recusou — não recomendável retry automático"
              items={data.bloqueados} busy={busy}
              onRetry={doRetry} onMarcar={doMarcar} onEnviar={null} />
          )}
        </>
      )}
    </div>
  );
}

function Sumario({ data }: { data: FilaResponse }) {
  return (
    <div className="card" style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
      <Stat label="Pendentes" value={data.pendentes.length} color="#f59e0b" />
      <Stat label="Falhas" value={data.falhas.length} color="#ef4444" />
      <Stat label="Bloqueados" value={data.bloqueados.length} color="#6b7280" />
      <Stat label="Total na fila" value={data.total} color="#3b82f6" />
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

interface SectionProps {
  title: string;
  subtitle: string;
  items: FilaItem[];
  busy: number | null;
  onRetry: ((it: FilaItem) => Promise<void>) | null;
  onMarcar: (it: FilaItem) => Promise<void>;
  onEnviar: ((it: FilaItem) => Promise<void>) | null;
}

function Section({ title, subtitle, items, busy, onRetry, onMarcar, onEnviar }: SectionProps) {
  return (
    <div className="card">
      <div style={{ marginBottom: 12 }}>
        <strong>{title}</strong>
        <div className="muted" style={{ fontSize: 12 }}>{subtitle}</div>
      </div>
      {items.length === 0 ? (
        <div className="empty">Nada aqui.</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Quando</th>
              <th>Cliente</th>
              <th>Módulo</th>
              <th>Mensagem / Erro</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.id}>
                <td className="muted" style={{ fontSize: 11 }}>
                  {new Date(it.criado_em).toLocaleString("pt-BR")}
                </td>
                <td>
                  <div>{it.cliente_nome ?? "?"}</div>
                  <div className="muted" style={{ fontSize: 11 }}>{it.telefone_destino}</div>
                </td>
                <td><span className="badge muted">{it.modulo}</span></td>
                <td style={{ maxWidth: 360 }}>
                  <div style={{ fontSize: 12 }}>
                    {it.mensagem_texto.slice(0, 100)}
                    {it.mensagem_texto.length > 100 ? "…" : ""}
                  </div>
                  {it.erro && (
                    <div style={{ color: "#991b1b", fontSize: 11, marginTop: 4 }}>
                      <strong>erro:</strong> {it.erro.slice(0, 120)}
                    </div>
                  )}
                </td>
                <td className="btn-row" style={{ justifyContent: "flex-end" }}>
                  {onEnviar && (
                    <button className="btn" disabled={busy === it.id}
                      onClick={() => void onEnviar(it)}>
                      Enviar agora
                    </button>
                  )}
                  {onRetry && (
                    <button className="btn" disabled={busy === it.id}
                      onClick={() => void onRetry(it)}>
                      Retry
                    </button>
                  )}
                  <button className="btn" disabled={busy === it.id}
                    onClick={() => void onMarcar(it)}>
                    Marcar enviado
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
