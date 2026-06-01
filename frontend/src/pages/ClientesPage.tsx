import { useEffect, useRef, useState } from "react";
import {
  createCliente, deleteCliente, exportClientesXlsxUrl,
  getClienteModulos, importClientesXlsx, listClientes, listGrupos, listPlanos,
  setClienteModulos, updateCliente,
} from "../api/endpoints";
import type {
  Cliente, ClienteCreate, ClienteModulosResponse,
  Grupo, ImportResult, PlanoServico,
} from "../api/types";
import Modal from "../components/Modal";
import ErrorBanner from "../components/ErrorBanner";

const MODULOS_LABELS: Array<[string, string]> = [
  ["comemorativo", "Aniversário e marcos de parceria"],
  ["expiracao",    "Alertas de expiração de plano"],
  ["pos_venda",    "Pós-venda (após compra)"],
  ["evento",       "Eventos (véspera e pós)"],
  ["sumiu",        "Reativação 'Sumiu por quê?'"],
];

const empty: ClienteCreate = {
  nome: "", telefone: "",
  data_inicio_parceria: new Date().toISOString().slice(0, 10),
  status: "ativo",
};

export default function ClientesPage() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [planos, setPlanos] = useState<PlanoServico[]>([]);
  const [grupos, setGrupos] = useState<Grupo[]>([]);
  const [q, setQ] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Cliente | null>(null);
  const [form, setForm] = useState<ClienteCreate>(empty);
  const [error, setError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [modulosCliente, setModulosCliente] = useState<ClienteModulosResponse | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    try {
      const [cs, ps, gs] = await Promise.all([
        listClientes({ q: q || undefined }),
        listPlanos(true),
        listGrupos(true),
      ]);
      setClientes(cs); setPlanos(ps); setGrupos(gs);
    } catch (e) { setError(String(e)); }
  };
  useEffect(() => { void load(); /* eslint-disable-next-line */ }, []);

  const planoNome = (c: Cliente): string | null => {
    if (c.plano_id) {
      return planos.find((p) => p.id === c.plano_id)?.nome ?? `#${c.plano_id}`;
    }
    return c.plano ?? null;
  };
  const grupoInfo = (c: Cliente): { nome: string; cor?: string } | null => {
    if (c.grupo_id) {
      const g = grupos.find((x) => x.id === c.grupo_id);
      return g ? { nome: g.nome, cor: g.cor ?? undefined } : { nome: `#${c.grupo_id}` };
    }
    return c.grupo ? { nome: c.grupo } : null;
  };

  const openCreate = () => {
    setEditing(null); setForm(empty); setModulosCliente(null); setModalOpen(true);
  };
  const openEdit = async (c: Cliente) => {
    setEditing(c);
    setForm({
      nome: c.nome, telefone: c.telefone, email: c.email ?? undefined,
      data_nascimento: c.data_nascimento ?? undefined,
      data_inicio_parceria: c.data_inicio_parceria,
      plano: c.plano ?? undefined, grupo: c.grupo ?? undefined,
      plano_id: c.plano_id ?? null, grupo_id: c.grupo_id ?? null,
      status: c.status, observacoes: c.observacoes ?? undefined,
    });
    setModulosCliente(null);
    setModalOpen(true);
    try { setModulosCliente(await getClienteModulos(c.id)); }
    catch (e) { console.warn("falha ao carregar módulos:", e); }
  };
  const toggleModulo = (mod: string) => {
    if (!modulosCliente) return;
    setModulosCliente({
      ...modulosCliente,
      explicito: true,
      modulos: {
        ...modulosCliente.modulos,
        [mod]: {
          ...modulosCliente.modulos[mod],
          ativo: !modulosCliente.modulos[mod]?.ativo,
          legado: false,
        },
      },
    });
  };

  const save = async () => {
    try {
      let savedId: number;
      if (editing) {
        await updateCliente(editing.id, form);
        savedId = editing.id;
      } else {
        const created = await createCliente(form);
        savedId = created.id;
      }
      // persiste módulos se foi modificado
      if (modulosCliente && modulosCliente.explicito) {
        const moduloFlags: Record<string, boolean> = {};
        for (const [k, v] of Object.entries(modulosCliente.modulos)) {
          moduloFlags[k] = v.ativo;
        }
        await setClienteModulos(savedId, moduloFlags);
      }
      setModalOpen(false); setError(null); await load();
    } catch (e) { setError(String(e)); }
  };

  const remove = async (c: Cliente) => {
    if (!confirm(`Deletar ${c.nome}?`)) return;
    try {
      await deleteCliente(c.id);
      await load();
    } catch (e) {
      // 409: cliente tem dependências (envios, comemorativos, etc.)
      const err = e as { status?: number; body?: { detail?: { message?: string; dependencies?: Record<string, number> } } };
      if (err.status === 409 && err.body?.detail?.dependencies) {
        const deps = err.body.detail.dependencies;
        const summary = Object.entries(deps).map(([k, v]) => `${v} ${k}`).join(", ");
        if (confirm(`${c.nome} tem registros vinculados (${summary}).\n\nApagar TUDO em cascata?`)) {
          try { await deleteCliente(c.id, true); await load(); }
          catch (e2) { setError(String(e2)); }
        }
      } else {
        setError(String(e));
      }
    }
  };

  const doImport = async (file: File) => {
    try {
      const result = await importClientesXlsx(file);
      setImportResult(result);
      await load();
    } catch (e) { setError(String(e)); }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Clientes</h1>
        <div className="btn-row">
          <input ref={fileRef} type="file" accept=".xlsx" style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void doImport(f);
              e.target.value = "";
            }} />
          <button className="btn" onClick={() => fileRef.current?.click()}>Importar Excel</button>
          <a className="btn" href={exportClientesXlsxUrl()} target="_blank" rel="noreferrer">
            Exportar Excel
          </a>
          <button className="btn primary" onClick={openCreate}>+ Novo cliente</button>
        </div>
      </div>

      <ErrorBanner message={error} onClose={() => setError(null)} />

      {importResult && (
        <div className="card">
          <strong>Import:</strong> {importResult.inseridos} inseridos,{" "}
          {importResult.duplicados} duplicados, {importResult.erros.length} erros.
          {importResult.erros.length > 0 && (
            <ul style={{ marginTop: 8 }}>
              {importResult.erros.slice(0, 10).map((e, i) => (
                <li key={i}>linha {e.row}{e.column ? ` [${e.column}]` : ""}: {e.message}</li>
              ))}
            </ul>
          )}
          <button className="btn" onClick={() => setImportResult(null)}>Ok</button>
        </div>
      )}

      <div className="card">
        <div className="row" style={{ marginBottom: 12 }}>
          <input placeholder="buscar nome ou telefone" value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") void load(); }}
            style={{ flex: 1, maxWidth: 320, padding: "8px 10px",
                     border: "1px solid #d1d5db", borderRadius: 6 }} />
          <button className="btn" onClick={() => void load()}>Buscar</button>
        </div>
        {clientes.length === 0 ? (
          <div className="empty">Nenhum cliente. Cadastre ou importe.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Telefone</th>
                <th>Plano</th>
                <th>Grupo</th>
                <th>Status</th>
                <th>Parceria</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {clientes.map((c) => {
                const planoNm = planoNome(c);
                const grupoInf = grupoInfo(c);
                return (
                  <tr key={c.id}>
                    <td>{c.nome}</td>
                    <td>{c.telefone}</td>
                    <td>{planoNm ?? <span className="muted">—</span>}</td>
                    <td>
                      {grupoInf ? (
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                          {grupoInf.cor && (
                            <span style={{
                              width: 10, height: 10, borderRadius: 2,
                              background: grupoInf.cor, display: "inline-block",
                            }} />
                          )}
                          {grupoInf.nome}
                        </span>
                      ) : <span className="muted">—</span>}
                    </td>
                    <td>
                      <span className={`badge ${c.status === "ativo" ? "ok" : "muted"}`}>
                        {c.status}
                      </span>
                    </td>
                    <td>{c.data_inicio_parceria}</td>
                    <td className="btn-row" style={{ justifyContent: "flex-end" }}>
                      <button className="btn" onClick={() => openEdit(c)}>Editar</button>
                      <button className="btn danger" onClick={() => void remove(c)}>Del</button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <Modal title={editing ? "Editar cliente" : "Novo cliente"}
        open={modalOpen} onClose={() => setModalOpen(false)}
        footer={
          <>
            <button className="btn" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button className="btn primary" onClick={() => void save()}>Salvar</button>
          </>
        }>
        <div className="form-grid">
          <label>Nome *<input value={form.nome}
            onChange={(e) => setForm({ ...form, nome: e.target.value })} /></label>
          <label>Telefone *<input value={form.telefone}
            placeholder="+5531999999999"
            onChange={(e) => setForm({ ...form, telefone: e.target.value })} /></label>
          <label>Email<input value={form.email ?? ""}
            onChange={(e) => setForm({ ...form, email: e.target.value || null })} /></label>
          <label>Data nascimento<input type="date" value={form.data_nascimento ?? ""}
            onChange={(e) => setForm({ ...form, data_nascimento: e.target.value || null })} /></label>
          <label>Data início parceria *<input type="date" value={form.data_inicio_parceria}
            onChange={(e) => setForm({ ...form, data_inicio_parceria: e.target.value })} /></label>
          <label>Plano
            <select value={form.plano_id ?? ""}
              onChange={(e) => setForm({
                ...form,
                plano_id: e.target.value ? Number(e.target.value) : null,
                plano: e.target.value
                  ? (planos.find((p) => p.id === Number(e.target.value))?.nome ?? null)
                  : null,
              })}>
              <option value="">— sem plano —</option>
              {planos.map((p) => (
                <option key={p.id} value={p.id}>{p.nome}</option>
              ))}
            </select>
          </label>
          <label>Grupo
            <select value={form.grupo_id ?? ""}
              onChange={(e) => setForm({
                ...form,
                grupo_id: e.target.value ? Number(e.target.value) : null,
                grupo: e.target.value
                  ? (grupos.find((g) => g.id === Number(e.target.value))?.nome ?? null)
                  : null,
              })}>
              <option value="">— sem grupo —</option>
              {grupos.map((g) => (
                <option key={g.id} value={g.id}>{g.nome}</option>
              ))}
            </select>
          </label>
          <label>Status<select value={form.status ?? "ativo"}
            onChange={(e) => setForm({ ...form, status: e.target.value as "ativo" | "inativo" })}>
            <option value="ativo">Ativo</option>
            <option value="inativo">Inativo</option>
          </select></label>
          <label className="span2">Observações<textarea value={form.observacoes ?? ""}
            onChange={(e) => setForm({ ...form, observacoes: e.target.value || null })} /></label>

          {editing && (
            <div className="span2" style={{
              borderTop: "1px solid #e5e7eb", paddingTop: 12, marginTop: 4,
            }}>
              <strong>Módulos ativos para este cliente</strong>
              {modulosCliente === null ? (
                <div className="muted" style={{ fontSize: 11, marginTop: 6 }}>
                  Carregando…
                </div>
              ) : (
                <>
                  <div className="muted" style={{ fontSize: 11, marginTop: 2,
                    marginBottom: 8 }}>
                    {modulosCliente.explicito
                      ? "Configurado explicitamente."
                      : "Legado: cliente recebe TODOS os módulos. Desmarcando algum vira explícito."}
                  </div>
                  {MODULOS_LABELS.map(([mod, label]) => {
                    const info = modulosCliente.modulos[mod];
                    return (
                      <label key={mod} style={{
                        display: "flex", flexDirection: "row",
                        alignItems: "center", gap: 8, padding: "4px 0",
                      }}>
                        <input type="checkbox" checked={info?.ativo ?? false}
                          onChange={() => toggleModulo(mod)} />
                        <span>{label}</span>
                        {info?.legado && <span className="badge muted">legado</span>}
                      </label>
                    );
                  })}
                </>
              )}
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}
