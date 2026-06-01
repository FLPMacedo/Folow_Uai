import { useEffect, useState } from "react";
import {
  createEvento, createEventoBroadcast, deleteEvento, dispatchEvento,
  dispatchPosVenda, listClientes, listEventos, listGrupos,
  previewBroadcast, updateEvento,
} from "../api/endpoints";
import type {
  BroadcastPreview, Cliente, Evento, EventoCreate, Grupo, TipoEvento,
} from "../api/types";
import Modal from "../components/Modal";
import ErrorBanner from "../components/ErrorBanner";

type Destino = "cliente" | "grupo";

const empty: EventoCreate = {
  cliente_id: 0,
  nome_evento: "",
  tipo_evento: "pos_venda",
  data_evento: new Date().toISOString().slice(0, 10),
  data_compra: new Date().toISOString().slice(0, 10),
};

export default function EventosPage() {
  const [eventos, setEventos] = useState<Evento[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [grupos, setGrupos] = useState<Grupo[]>([]);
  const [filterTipo, setFilterTipo] = useState<TipoEvento | "">("");
  const [filterCliente, setFilterCliente] = useState<number | "">("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Evento | null>(null);
  const [form, setForm] = useState<EventoCreate>(empty);
  const [destino, setDestino] = useState<Destino>("cliente");
  const [grupoId, setGrupoId] = useState<number | null>(null);
  const [preview, setPreview] = useState<BroadcastPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [lastStats, setLastStats] = useState<{ which: string; stats: { enviados: number; falhas: number; pendentes: number; ignorados: number } } | null>(null);

  const load = async () => {
    try {
      const [evs, cs, gs] = await Promise.all([
        listEventos({
          tipo_evento: filterTipo || undefined,
          cliente_id: typeof filterCliente === "number" ? filterCliente : undefined,
        }),
        listClientes({ limit: 1000 }),
        listGrupos(true),
      ]);
      setEventos(evs);
      setClientes(cs);
      setGrupos(gs);
    } catch (e) { setError(String(e)); }
  };
  useEffect(() => { void load(); /* eslint-disable-next-line */ }, [filterTipo, filterCliente]);

  // Atualiza preview quando muda grupo
  useEffect(() => {
    if (destino !== "grupo" || !grupoId) { setPreview(null); return; }
    let canceled = false;
    void previewBroadcast(grupoId).then((p) => {
      if (!canceled) setPreview(p);
    }).catch(() => setPreview(null));
    return () => { canceled = true; };
  }, [destino, grupoId]);

  const openCreate = (tipo: TipoEvento) => {
    setEditing(null);
    setForm({
      ...empty,
      tipo_evento: tipo,
      cliente_id: clientes[0]?.id ?? 0,
      data_compra: tipo === "pos_venda" ? new Date().toISOString().slice(0, 10) : null,
    });
    setDestino("cliente");
    setGrupoId(grupos[0]?.id ?? null);
    setPreview(null);
    setModalOpen(true);
  };
  const openEdit = (ev: Evento) => {
    setEditing(ev);
    setForm({
      cliente_id: ev.cliente_id,
      nome_evento: ev.nome_evento,
      tipo_evento: ev.tipo_evento,
      data_evento: ev.data_evento,
      data_compra: ev.data_compra ?? null,
      observacoes: ev.observacoes ?? null,
    });
    setDestino("cliente");  // editar é sempre 1 evento
    setModalOpen(true);
  };
  const save = async () => {
    try {
      if (editing) {
        await updateEvento(editing.id, form);
      } else if (destino === "grupo") {
        if (!grupoId) throw new Error("Escolha um grupo");
        if (preview?.total_clientes_ativos === 0)
          throw new Error("Grupo sem clientes ativos");
        const ok = confirm(
          `Criar ${preview?.total_clientes_ativos ?? "?"} eventos ` +
          `(um por cliente do grupo)?`,
        );
        if (!ok) return;
        const r = await createEventoBroadcast({
          grupo_id: grupoId,
          nome_evento: form.nome_evento,
          tipo_evento: form.tipo_evento,
          data_evento: form.data_evento,
          data_compra: form.data_compra ?? null,
          observacoes: form.observacoes ?? null,
        });
        alert(`${r.criados} eventos criados.`);
      } else {
        await createEvento(form);
      }
      setModalOpen(false); setError(null); await load();
    } catch (e) { setError(String(e)); }
  };
  const remove = async (ev: Evento) => {
    if (!confirm(`Apagar evento "${ev.nome_evento}"?`)) return;
    try { await deleteEvento(ev.id); await load(); }
    catch (e) { setError(String(e)); }
  };
  const dispatch = async (which: "pos_venda" | "evento") => {
    setBusy(true);
    try {
      const stats = which === "pos_venda" ? await dispatchPosVenda() : await dispatchEvento();
      setLastStats({ which, stats });
      await load();
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  };

  const clienteNome = (id: number) =>
    clientes.find((c) => c.id === id)?.nome ?? `id=${id}`;

  return (
    <div>
      <div className="page-header">
        <h1>Eventos &amp; Pós-Venda</h1>
        <div className="btn-row">
          <button className="btn" disabled={busy} onClick={() => void dispatch("pos_venda")}>
            Disparar Pós-Venda
          </button>
          <button className="btn" disabled={busy} onClick={() => void dispatch("evento")}>
            Disparar Evento
          </button>
          <button className="btn primary" onClick={() => openCreate("pos_venda")}>
            + Nova compra
          </button>
          <button className="btn primary" onClick={() => openCreate("evento")}>
            + Novo evento
          </button>
        </div>
      </div>
      <ErrorBanner message={error} onClose={() => setError(null)} />

      {lastStats && (
        <div className="card">
          <strong>{lastStats.which}:</strong>{" "}
          enviados {lastStats.stats.enviados},{" "}
          falhas {lastStats.stats.falhas},{" "}
          pendentes {lastStats.stats.pendentes},{" "}
          ignorados {lastStats.stats.ignorados}
          <button className="btn" style={{ marginLeft: 12 }}
            onClick={() => setLastStats(null)}>×</button>
        </div>
      )}

      <div className="card">
        <div className="row" style={{ marginBottom: 12 }}>
          <label className="muted">Tipo:&nbsp;
            <select value={filterTipo}
              onChange={(e) => setFilterTipo(e.target.value as TipoEvento | "")}>
              <option value="">Todos</option>
              <option value="pos_venda">Pós-venda</option>
              <option value="evento">Evento</option>
            </select>
          </label>
          <label className="muted">Cliente:&nbsp;
            <select value={filterCliente}
              onChange={(e) => setFilterCliente(
                e.target.value === "" ? "" : Number(e.target.value),
              )}>
              <option value="">Todos</option>
              {clientes.map((c) => (
                <option key={c.id} value={c.id}>{c.nome}</option>
              ))}
            </select>
          </label>
        </div>

        {eventos.length === 0 ? (
          <div className="empty">Nenhum evento. Cadastre uma compra ou evento agendado.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Tipo</th>
                <th>Nome</th>
                <th>Data evento</th>
                <th>Data compra</th>
                <th>Véspera</th>
                <th>Pós</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {eventos.map((ev) => (
                <tr key={ev.id}>
                  <td>{clienteNome(ev.cliente_id)}</td>
                  <td><span className="badge muted">{ev.tipo_evento}</span></td>
                  <td>{ev.nome_evento}</td>
                  <td>{ev.data_evento}</td>
                  <td>{ev.data_compra ?? <span className="muted">—</span>}</td>
                  <td>
                    <span className={`badge ${ev.vespera_mensagem_enviada ? "ok" : "muted"}`}>
                      {ev.vespera_mensagem_enviada ? "sim" : "não"}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${ev.pos_mensagem_enviada ? "ok" : "muted"}`}>
                      {ev.pos_mensagem_enviada ? "sim" : "não"}
                    </span>
                  </td>
                  <td className="btn-row" style={{ justifyContent: "flex-end" }}>
                    <button className="btn" onClick={() => openEdit(ev)}>Editar</button>
                    <button className="btn danger" onClick={() => void remove(ev)}>Del</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal title={editing ? "Editar" : (form.tipo_evento === "pos_venda" ? "Nova compra" : "Novo evento")}
        open={modalOpen} onClose={() => setModalOpen(false)}
        footer={
          <>
            <button className="btn" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button className="btn primary" onClick={() => void save()}>Salvar</button>
          </>
        }>
        <div className="form-grid">
          {!editing && (
            <div className="span2" style={{
              display: "flex", gap: 12, padding: 8,
              background: "#f9fafb", borderRadius: 6,
            }}>
              <label style={{ display: "flex", flexDirection: "row",
                alignItems: "center", gap: 6, cursor: "pointer" }}>
                <input type="radio" checked={destino === "cliente"}
                  onChange={() => setDestino("cliente")} />
                <span>1 cliente</span>
              </label>
              <label style={{ display: "flex", flexDirection: "row",
                alignItems: "center", gap: 6, cursor: "pointer" }}>
                <input type="radio" checked={destino === "grupo"}
                  onChange={() => setDestino("grupo")}
                  disabled={grupos.length === 0} />
                <span>Grupo inteiro (broadcast)</span>
                {grupos.length === 0 && (
                  <span className="muted" style={{ fontSize: 11 }}>
                    (cadastre grupos primeiro)
                  </span>
                )}
              </label>
            </div>
          )}

          {destino === "cliente" ? (
            <label>Cliente *
              <select value={form.cliente_id}
                onChange={(e) => setForm({ ...form, cliente_id: Number(e.target.value) })}>
                {clientes.map((c) => (
                  <option key={c.id} value={c.id}>{c.nome} ({c.telefone})</option>
                ))}
              </select>
            </label>
          ) : (
            <label>Grupo *
              <select value={grupoId ?? ""}
                onChange={(e) => setGrupoId(e.target.value ? Number(e.target.value) : null)}>
                {grupos.map((g) => (
                  <option key={g.id} value={g.id}>{g.nome}</option>
                ))}
              </select>
            </label>
          )}

          <label>Tipo *
            <select value={form.tipo_evento}
              onChange={(e) => setForm({ ...form, tipo_evento: e.target.value as TipoEvento })}>
              <option value="pos_venda">Pós-venda (compra)</option>
              <option value="evento">Evento agendado</option>
            </select>
          </label>

          {destino === "grupo" && preview && (
            <div className="span2" style={{
              padding: 8, background: preview.total_clientes_ativos > 0 ? "#dcfce7" : "#fee2e2",
              borderRadius: 6, fontSize: 13,
            }}>
              <strong>{preview.total_clientes_ativos}</strong> clientes ativos
              {preview.total_clientes_ativos > 0 && (
                <span className="muted">
                  {" · "}
                  ex: {preview.amostra_nomes.slice(0, 5).join(", ")}
                  {preview.amostra_nomes.length > 5 && "…"}
                </span>
              )}
              {preview.total_clientes_ativos === 0 && (
                <span className="muted"> — cadastre clientes nesse grupo primeiro.</span>
              )}
            </div>
          )}
          <label className="span2">Nome *
            <input value={form.nome_evento} placeholder={
              form.tipo_evento === "pos_venda" ? "Ex: Tênis Nike, Curso X" : "Ex: Corrida 5K"
            } onChange={(e) => setForm({ ...form, nome_evento: e.target.value })} />
          </label>
          <label>Data {form.tipo_evento === "pos_venda" ? "compra" : "evento"} *
            <input type="date"
              value={form.tipo_evento === "pos_venda"
                ? (form.data_compra ?? form.data_evento)
                : form.data_evento}
              onChange={(e) => setForm(form.tipo_evento === "pos_venda"
                ? { ...form, data_compra: e.target.value, data_evento: e.target.value }
                : { ...form, data_evento: e.target.value })} />
          </label>
          <label className="span2">Observações
            <textarea value={form.observacoes ?? ""}
              onChange={(e) => setForm({ ...form, observacoes: e.target.value || null })} />
          </label>
        </div>
      </Modal>
    </div>
  );
}
