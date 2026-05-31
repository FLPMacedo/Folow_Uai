import { useEffect, useState } from "react";
import {
  createGrupo, createNegocio, createPlano,
  deleteGrupo, deleteNegocio, deletePlano,
  listGrupos, listNegocios, listPlanos,
  updateGrupo, updateNegocio, updatePlano,
} from "../api/endpoints";
import type {
  Grupo, GrupoCreate, Negocio, NegocioCreate,
  PlanoServico, PlanoServicoCreate,
} from "../api/types";
import Modal from "../components/Modal";
import ErrorBanner from "../components/ErrorBanner";

type Tab = "empresas" | "planos" | "grupos";

export default function MeuNegocioPage() {
  const [tab, setTab] = useState<Tab>("empresas");

  return (
    <div>
      <div className="page-header">
        <h1>Meu Negócio</h1>
      </div>

      <div className="card" style={{ padding: 4, marginBottom: 12, display: "flex", gap: 4 }}>
        <TabBtn active={tab === "empresas"} onClick={() => setTab("empresas")}>Empresas</TabBtn>
        <TabBtn active={tab === "planos"}   onClick={() => setTab("planos")}>Planos &amp; Serviços</TabBtn>
        <TabBtn active={tab === "grupos"}   onClick={() => setTab("grupos")}>Grupos</TabBtn>
      </div>

      {tab === "empresas" && <EmpresasTab />}
      {tab === "planos"   && <PlanosTab />}
      {tab === "grupos"   && <GruposTab />}
    </div>
  );
}

function TabBtn({ active, onClick, children }: {
  active: boolean; onClick: () => void; children: React.ReactNode;
}) {
  return (
    <button onClick={onClick} className="btn"
      style={{
        flex: 1,
        background: active ? "#3b82f6" : "transparent",
        color: active ? "#fff" : "#1f2937",
        borderColor: active ? "#3b82f6" : "transparent",
      }}>
      {children}
    </button>
  );
}

// =====================================================================
// Empresas
// =====================================================================
const VARS_INFO: Array<[string, string]> = [
  ["{empresa_nome}",     "nome"],
  ["{empresa_endereco}", "endereco"],
  ["{empresa_telefone}", "telefone_contato"],
  ["{empresa_whatsapp}", "whatsapp_duvidas"],
  ["{empresa_email}",    "email"],
  ["{empresa_site}",     "site"],
];

const emptyEmpresa: NegocioCreate = {
  nome: "", endereco: null, telefone_contato: null,
  whatsapp_duvidas: null, email: null, site: null,
  descricao: null, is_default: false, ativo: true,
};

function EmpresasTab() {
  const [items, setItems] = useState<Negocio[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<Negocio | null>(null);
  const [form, setForm] = useState<NegocioCreate>(emptyEmpresa);

  const load = async () => {
    try { setItems(await listNegocios()); } catch (e) { setErr(String(e)); }
  };
  useEffect(() => { void load(); }, []);

  const openCreate = () => {
    setEditing(null);
    setForm({ ...emptyEmpresa, is_default: items.length === 0 });
    setModal(true);
  };
  const openEdit = (n: Negocio) => {
    setEditing(n);
    setForm({
      nome: n.nome, endereco: n.endereco ?? null,
      telefone_contato: n.telefone_contato ?? null,
      whatsapp_duvidas: n.whatsapp_duvidas ?? null,
      email: n.email ?? null, site: n.site ?? null,
      descricao: n.descricao ?? null,
      is_default: n.is_default, ativo: n.ativo,
    });
    setModal(true);
  };
  const save = async () => {
    try {
      if (editing) await updateNegocio(editing.id, form);
      else await createNegocio(form);
      setModal(false); setErr(null); await load();
    } catch (e) { setErr(String(e)); }
  };
  const remove = async (n: Negocio) => {
    if (!confirm(`Apagar "${n.nome}"?`)) return;
    try { await deleteNegocio(n.id); await load(); }
    catch (e) { setErr(String(e)); }
  };
  const tornarDefault = async (n: Negocio) => {
    try { await updateNegocio(n.id, { is_default: true }); await load(); }
    catch (e) { setErr(String(e)); }
  };

  return (
    <>
      <ErrorBanner message={err} onClose={() => setErr(null)} />

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Variáveis nos templates</h3>
        <p className="muted">
          Use essas variáveis em Templates. Vão pegar dados da empresa marcada
          como <span className="badge ok">PADRÃO</span>.
        </p>
        <table className="table">
          <thead><tr><th>Variável</th><th>Campo</th></tr></thead>
          <tbody>
            {VARS_INFO.map(([v, c]) => (
              <tr key={v}>
                <td><code style={{ background: "#f3f4f6", padding: "2px 6px",
                       borderRadius: 4 }}>{v}</code></td>
                <td>{c}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <div className="row" style={{ marginBottom: 12 }}>
          <span className="spacer" />
          <button className="btn primary" onClick={openCreate}>+ Nova empresa</button>
        </div>
        {items.length === 0 ? (
          <div className="empty">Nenhuma empresa cadastrada.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Nome</th><th>Contato</th><th>WhatsApp dúvidas</th>
                <th>Padrão</th><th>Ativo</th><th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((n) => (
                <tr key={n.id}>
                  <td>
                    <strong>{n.nome}</strong>
                    {n.email && <div className="muted">{n.email}</div>}
                  </td>
                  <td>{n.telefone_contato ?? <span className="muted">—</span>}</td>
                  <td>{n.whatsapp_duvidas ?? <span className="muted">—</span>}</td>
                  <td>
                    {n.is_default
                      ? <span className="badge ok">PADRÃO</span>
                      : <button className="btn" onClick={() => void tornarDefault(n)}>Tornar padrão</button>}
                  </td>
                  <td><span className={`badge ${n.ativo ? "ok" : "muted"}`}>{n.ativo ? "sim" : "não"}</span></td>
                  <td className="btn-row" style={{ justifyContent: "flex-end" }}>
                    <button className="btn" onClick={() => openEdit(n)}>Editar</button>
                    <button className="btn danger" onClick={() => void remove(n)}>Del</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal title={editing ? "Editar empresa" : "Nova empresa"}
        open={modal} onClose={() => setModal(false)}
        footer={
          <>
            <button className="btn" onClick={() => setModal(false)}>Cancelar</button>
            <button className="btn primary" onClick={() => void save()}>Salvar</button>
          </>
        }>
        <div className="form-grid">
          <label className="span2">Nome *<input value={form.nome}
            onChange={(e) => setForm({ ...form, nome: e.target.value })} /></label>
          <label>Telefone de contato<input value={form.telefone_contato ?? ""}
            onChange={(e) => setForm({ ...form, telefone_contato: e.target.value || null })} /></label>
          <label>WhatsApp dúvidas<input value={form.whatsapp_duvidas ?? ""}
            onChange={(e) => setForm({ ...form, whatsapp_duvidas: e.target.value || null })} /></label>
          <label>Email<input value={form.email ?? ""}
            onChange={(e) => setForm({ ...form, email: e.target.value || null })} /></label>
          <label>Site<input value={form.site ?? ""}
            onChange={(e) => setForm({ ...form, site: e.target.value || null })} /></label>
          <label className="span2">Endereço<input value={form.endereco ?? ""}
            onChange={(e) => setForm({ ...form, endereco: e.target.value || null })} /></label>
          <label className="span2">Descrição<textarea value={form.descricao ?? ""}
            onChange={(e) => setForm({ ...form, descricao: e.target.value || null })} /></label>
          <label>Empresa padrão<input type="checkbox" checked={form.is_default ?? false}
            onChange={(e) => setForm({ ...form, is_default: e.target.checked })} /></label>
          <label>Ativa<input type="checkbox" checked={form.ativo ?? true}
            onChange={(e) => setForm({ ...form, ativo: e.target.checked })} /></label>
        </div>
      </Modal>
    </>
  );
}

// =====================================================================
// Planos & Serviços
// =====================================================================
const emptyPlano: PlanoServicoCreate = {
  nome: "", descricao: null, preco: null, periodicidade: null,
  duracao_dias: null, ativo: true,
};

function PlanosTab() {
  const [items, setItems] = useState<PlanoServico[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<PlanoServico | null>(null);
  const [form, setForm] = useState<PlanoServicoCreate>(emptyPlano);

  const load = async () => {
    try { setItems(await listPlanos()); } catch (e) { setErr(String(e)); }
  };
  useEffect(() => { void load(); }, []);

  const openCreate = () => {
    setEditing(null); setForm(emptyPlano); setModal(true);
  };
  const openEdit = (p: PlanoServico) => {
    setEditing(p);
    setForm({
      nome: p.nome, descricao: p.descricao ?? null,
      preco: p.preco ?? null, periodicidade: p.periodicidade ?? null,
      duracao_dias: p.duracao_dias ?? null, ativo: p.ativo,
    });
    setModal(true);
  };
  const save = async () => {
    try {
      if (editing) await updatePlano(editing.id, form);
      else await createPlano(form);
      setModal(false); setErr(null); await load();
    } catch (e) { setErr(String(e)); }
  };
  const remove = async (p: PlanoServico) => {
    if (!confirm(`Apagar "${p.nome}"?`)) return;
    try { await deletePlano(p.id); await load(); }
    catch (e) { setErr(String(e)); }
  };

  return (
    <>
      <ErrorBanner message={err} onClose={() => setErr(null)} />
      <div className="card">
        <div className="row" style={{ marginBottom: 12 }}>
          <span className="muted">
            Catálogo de planos/serviços que você oferece.
            Vão aparecer como dropdown no cadastro de cliente.
          </span>
          <span className="spacer" />
          <button className="btn primary" onClick={openCreate}>+ Novo plano</button>
        </div>
        {items.length === 0 ? (
          <div className="empty">Nenhum plano cadastrado.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Nome</th><th>Preço</th><th>Periodicidade</th>
                <th>Duração</th><th>Ativo</th><th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id}>
                  <td>
                    <strong>{p.nome}</strong>
                    {p.descricao && <div className="muted">{p.descricao}</div>}
                  </td>
                  <td>{p.preco !== null && p.preco !== undefined
                       ? `R$ ${p.preco.toFixed(2)}` : <span className="muted">—</span>}</td>
                  <td>{p.periodicidade ?? <span className="muted">—</span>}</td>
                  <td>{p.duracao_dias !== null && p.duracao_dias !== undefined
                       ? `${p.duracao_dias} dias` : <span className="muted">—</span>}</td>
                  <td><span className={`badge ${p.ativo ? "ok" : "muted"}`}>{p.ativo ? "sim" : "não"}</span></td>
                  <td className="btn-row" style={{ justifyContent: "flex-end" }}>
                    <button className="btn" onClick={() => openEdit(p)}>Editar</button>
                    <button className="btn danger" onClick={() => void remove(p)}>Del</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal title={editing ? "Editar plano" : "Novo plano"}
        open={modal} onClose={() => setModal(false)}
        footer={
          <>
            <button className="btn" onClick={() => setModal(false)}>Cancelar</button>
            <button className="btn primary" onClick={() => void save()}>Salvar</button>
          </>
        }>
        <div className="form-grid">
          <label className="span2">Nome *<input value={form.nome}
            onChange={(e) => setForm({ ...form, nome: e.target.value })} /></label>
          <label className="span2">Descrição<textarea value={form.descricao ?? ""}
            onChange={(e) => setForm({ ...form, descricao: e.target.value || null })} /></label>
          <label>Preço (R$)
            <input type="number" step="0.01" value={form.preco ?? ""}
              onChange={(e) => setForm({ ...form, preco: e.target.value ? Number(e.target.value) : null })} />
          </label>
          <label>Periodicidade
            <select value={form.periodicidade ?? ""}
              onChange={(e) => setForm({ ...form, periodicidade: e.target.value || null })}>
              <option value="">—</option>
              <option value="mensal">Mensal</option>
              <option value="anual">Anual</option>
              <option value="unico">Único</option>
            </select>
          </label>
          <label>Duração (dias)
            <input type="number" value={form.duracao_dias ?? ""}
              onChange={(e) => setForm({ ...form, duracao_dias: e.target.value ? Number(e.target.value) : null })} />
          </label>
          <label>Ativo<input type="checkbox" checked={form.ativo ?? true}
            onChange={(e) => setForm({ ...form, ativo: e.target.checked })} /></label>
        </div>
      </Modal>
    </>
  );
}

// =====================================================================
// Grupos
// =====================================================================
const emptyGrupo: GrupoCreate = { nome: "", cor: "#3b82f6", descricao: null, ativo: true };

function GruposTab() {
  const [items, setItems] = useState<Grupo[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<Grupo | null>(null);
  const [form, setForm] = useState<GrupoCreate>(emptyGrupo);

  const load = async () => {
    try { setItems(await listGrupos()); } catch (e) { setErr(String(e)); }
  };
  useEffect(() => { void load(); }, []);

  const openCreate = () => {
    setEditing(null); setForm(emptyGrupo); setModal(true);
  };
  const openEdit = (g: Grupo) => {
    setEditing(g);
    setForm({
      nome: g.nome, cor: g.cor ?? "#3b82f6",
      descricao: g.descricao ?? null, ativo: g.ativo,
    });
    setModal(true);
  };
  const save = async () => {
    try {
      if (editing) await updateGrupo(editing.id, form);
      else await createGrupo(form);
      setModal(false); setErr(null); await load();
    } catch (e) { setErr(String(e)); }
  };
  const remove = async (g: Grupo) => {
    if (!confirm(`Apagar "${g.nome}"?`)) return;
    try { await deleteGrupo(g.id); await load(); }
    catch (e) { setErr(String(e)); }
  };

  return (
    <>
      <ErrorBanner message={err} onClose={() => setErr(null)} />
      <div className="card">
        <div className="row" style={{ marginBottom: 12 }}>
          <span className="muted">
            Categorias de clientes (VIP, Ouro, Corredor, etc.). 1 cliente = 1 grupo.
          </span>
          <span className="spacer" />
          <button className="btn primary" onClick={openCreate}>+ Novo grupo</button>
        </div>
        {items.length === 0 ? (
          <div className="empty">Nenhum grupo cadastrado.</div>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Nome</th><th>Cor</th><th>Descrição</th><th>Ativo</th><th></th></tr>
            </thead>
            <tbody>
              {items.map((g) => (
                <tr key={g.id}>
                  <td><strong>{g.nome}</strong></td>
                  <td>
                    {g.cor && (
                      <span style={{
                        display: "inline-block", width: 24, height: 16,
                        background: g.cor, borderRadius: 4,
                        border: "1px solid #d1d5db", verticalAlign: "middle",
                      }} />
                    )}
                    <span style={{ marginLeft: 8, fontFamily: "monospace" }}>{g.cor ?? "—"}</span>
                  </td>
                  <td className="muted">{g.descricao ?? "—"}</td>
                  <td><span className={`badge ${g.ativo ? "ok" : "muted"}`}>{g.ativo ? "sim" : "não"}</span></td>
                  <td className="btn-row" style={{ justifyContent: "flex-end" }}>
                    <button className="btn" onClick={() => openEdit(g)}>Editar</button>
                    <button className="btn danger" onClick={() => void remove(g)}>Del</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal title={editing ? "Editar grupo" : "Novo grupo"}
        open={modal} onClose={() => setModal(false)}
        footer={
          <>
            <button className="btn" onClick={() => setModal(false)}>Cancelar</button>
            <button className="btn primary" onClick={() => void save()}>Salvar</button>
          </>
        }>
        <div className="form-grid">
          <label className="span2">Nome *<input value={form.nome}
            onChange={(e) => setForm({ ...form, nome: e.target.value })} /></label>
          <label>Cor
            <input type="color" value={form.cor ?? "#3b82f6"}
              onChange={(e) => setForm({ ...form, cor: e.target.value })} />
          </label>
          <label>Ativo<input type="checkbox" checked={form.ativo ?? true}
            onChange={(e) => setForm({ ...form, ativo: e.target.checked })} /></label>
          <label className="span2">Descrição<textarea value={form.descricao ?? ""}
            onChange={(e) => setForm({ ...form, descricao: e.target.value || null })} /></label>
        </div>
      </Modal>
    </>
  );
}
