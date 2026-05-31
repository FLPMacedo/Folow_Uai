import { useEffect, useState } from "react";
import {
  createNegocio, deleteNegocio, listNegocios, updateNegocio,
} from "../api/endpoints";
import type { Negocio, NegocioCreate } from "../api/types";
import Modal from "../components/Modal";
import ErrorBanner from "../components/ErrorBanner";

const empty: NegocioCreate = {
  nome: "",
  endereco: null,
  telefone_contato: null,
  whatsapp_duvidas: null,
  email: null,
  site: null,
  descricao: null,
  is_default: false,
  ativo: true,
};

const VARS_INFO: Array<[string, string]> = [
  ["{empresa_nome}",     "nome"],
  ["{empresa_endereco}", "endereco"],
  ["{empresa_telefone}", "telefone_contato"],
  ["{empresa_whatsapp}", "whatsapp_duvidas"],
  ["{empresa_email}",    "email"],
  ["{empresa_site}",     "site"],
];

export default function MeuNegocioPage() {
  const [negocios, setNegocios] = useState<Negocio[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Negocio | null>(null);
  const [form, setForm] = useState<NegocioCreate>(empty);

  const load = async () => {
    try { setNegocios(await listNegocios()); }
    catch (e) { setError(String(e)); }
  };
  useEffect(() => { void load(); }, []);

  const openCreate = () => {
    setEditing(null);
    setForm({ ...empty, is_default: negocios.length === 0 });
    setModalOpen(true);
  };
  const openEdit = (n: Negocio) => {
    setEditing(n);
    setForm({
      nome: n.nome,
      endereco: n.endereco ?? null,
      telefone_contato: n.telefone_contato ?? null,
      whatsapp_duvidas: n.whatsapp_duvidas ?? null,
      email: n.email ?? null,
      site: n.site ?? null,
      descricao: n.descricao ?? null,
      is_default: n.is_default,
      ativo: n.ativo,
    });
    setModalOpen(true);
  };
  const save = async () => {
    try {
      if (editing) await updateNegocio(editing.id, form);
      else await createNegocio(form);
      setModalOpen(false); setError(null); await load();
    } catch (e) { setError(String(e)); }
  };
  const remove = async (n: Negocio) => {
    if (!confirm(`Apagar "${n.nome}"?`)) return;
    try { await deleteNegocio(n.id); await load(); }
    catch (e) { setError(String(e)); }
  };
  const tornarDefault = async (n: Negocio) => {
    try { await updateNegocio(n.id, { is_default: true }); await load(); }
    catch (e) { setError(String(e)); }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Meu Negócio</h1>
        <button className="btn primary" onClick={openCreate}>+ Nova empresa</button>
      </div>
      <ErrorBanner message={error} onClose={() => setError(null)} />

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Variáveis disponíveis nos templates</h3>
        <p className="muted">
          Quando você escrever um template em <strong>Templates</strong>, pode usar
          essas variáveis. Elas serão substituídas pelos dados do negócio marcado
          como <span className="badge ok">Padrão</span> no envio.
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
        {negocios.length === 0 ? (
          <div className="empty">
            Nenhuma empresa cadastrada. Cadastre pelo menos uma para usar variáveis
            de empresa nos templates.
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Contato</th>
                <th>WhatsApp dúvidas</th>
                <th>Endereço</th>
                <th>Padrão</th>
                <th>Ativo</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {negocios.map((n) => (
                <tr key={n.id}>
                  <td>
                    <strong>{n.nome}</strong>
                    {n.email && <div className="muted">{n.email}</div>}
                  </td>
                  <td>{n.telefone_contato ?? <span className="muted">—</span>}</td>
                  <td>{n.whatsapp_duvidas ?? <span className="muted">—</span>}</td>
                  <td className="muted" style={{ maxWidth: 220 }}>
                    {n.endereco ?? "—"}
                  </td>
                  <td>
                    {n.is_default
                      ? <span className="badge ok">PADRÃO</span>
                      : (
                        <button className="btn" onClick={() => void tornarDefault(n)}>
                          Tornar padrão
                        </button>
                      )}
                  </td>
                  <td>
                    <span className={`badge ${n.ativo ? "ok" : "muted"}`}>
                      {n.ativo ? "sim" : "não"}
                    </span>
                  </td>
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
        open={modalOpen} onClose={() => setModalOpen(false)}
        footer={
          <>
            <button className="btn" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button className="btn primary" onClick={() => void save()}>Salvar</button>
          </>
        }>
        <div className="form-grid">
          <label className="span2">Nome *<input value={form.nome}
            onChange={(e) => setForm({ ...form, nome: e.target.value })} /></label>
          <label>Telefone de contato<input value={form.telefone_contato ?? ""}
            placeholder="+5531999999999"
            onChange={(e) => setForm({ ...form, telefone_contato: e.target.value || null })} /></label>
          <label>WhatsApp dúvidas<input value={form.whatsapp_duvidas ?? ""}
            placeholder="+5531999999999"
            onChange={(e) => setForm({ ...form, whatsapp_duvidas: e.target.value || null })} /></label>
          <label>Email<input value={form.email ?? ""}
            onChange={(e) => setForm({ ...form, email: e.target.value || null })} /></label>
          <label>Site<input value={form.site ?? ""}
            placeholder="https://..."
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
    </div>
  );
}
