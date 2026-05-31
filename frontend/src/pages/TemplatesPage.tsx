import { useEffect, useState } from "react";
import {
  createTemplate, deleteTemplate, listTemplates, updateTemplate,
} from "../api/endpoints";
import type { Modulo, Template, TemplateCreate } from "../api/types";
import Modal from "../components/Modal";
import ErrorBanner from "../components/ErrorBanner";

const MODULOS: Modulo[] = ["comemorativo", "expiracao", "pos_venda", "evento", "sumiu"];

const empty: TemplateCreate = {
  nome: "", modulo: "comemorativo", tipo_gatilho: "",
  mensagem_texto: "", ativo: true,
};

export default function TemplatesPage() {
  const [tmpls, setTmpls] = useState<Template[]>([]);
  const [filter, setFilter] = useState<Modulo | "">("");
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<TemplateCreate>(empty);
  const [editing, setEditing] = useState<Template | null>(null);

  const load = async () => {
    try {
      setTmpls(await listTemplates(filter ? { modulo: filter } : undefined));
    } catch (e) { setError(String(e)); }
  };
  useEffect(() => { void load(); /* eslint-disable-next-line */ }, [filter]);

  const save = async () => {
    try {
      if (editing) await updateTemplate(editing.id, form);
      else await createTemplate(form);
      setModalOpen(false); setError(null); await load();
    } catch (e) { setError(String(e)); }
  };

  const openCreate = () => {
    setEditing(null); setForm(empty); setModalOpen(true);
  };
  const openEdit = (t: Template) => {
    setEditing(t);
    setForm({
      nome: t.nome, modulo: t.modulo, tipo_gatilho: t.tipo_gatilho,
      mensagem_texto: t.mensagem_texto,
      caminho_imagem: t.caminho_imagem ?? undefined,
      variaveis: t.variaveis ?? undefined,
      ativo: t.ativo,
    });
    setModalOpen(true);
  };

  const remove = async (t: Template) => {
    if (!confirm(`Deletar template "${t.nome}"?`)) return;
    try { await deleteTemplate(t.id); await load(); }
    catch (e) { setError(String(e)); }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Templates</h1>
        <div className="btn-row">
          <select value={filter} onChange={(e) => setFilter(e.target.value as Modulo | "")}>
            <option value="">Todos módulos</option>
            {MODULOS.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          <button className="btn primary" onClick={openCreate}>+ Novo template</button>
        </div>
      </div>
      <ErrorBanner message={error} onClose={() => setError(null)} />

      <div className="card">
        {tmpls.length === 0 ? (
          <div className="empty">Nenhum template para esse filtro.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Módulo</th>
                <th>Gatilho</th>
                <th>Ativo</th>
                <th>Mensagem</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {tmpls.map((t) => (
                <tr key={t.id}>
                  <td>{t.nome}</td>
                  <td><span className="badge muted">{t.modulo}</span></td>
                  <td>{t.tipo_gatilho}</td>
                  <td>
                    <span className={`badge ${t.ativo ? "ok" : "muted"}`}>
                      {t.ativo ? "sim" : "não"}
                    </span>
                  </td>
                  <td className="muted" style={{ maxWidth: 360 }}>
                    {t.mensagem_texto.slice(0, 80)}{t.mensagem_texto.length > 80 ? "…" : ""}
                  </td>
                  <td className="btn-row" style={{ justifyContent: "flex-end" }}>
                    <button className="btn" onClick={() => openEdit(t)}>Editar</button>
                    <button className="btn danger" onClick={() => void remove(t)}>Del</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal title={editing ? "Editar template" : "Novo template"}
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
          <label>Módulo *<select value={form.modulo}
            onChange={(e) => setForm({ ...form, modulo: e.target.value as Modulo })}>
            {MODULOS.map((m) => <option key={m} value={m}>{m}</option>)}
          </select></label>
          <label className="span2">Tipo gatilho *<input value={form.tipo_gatilho}
            placeholder="aniversario | 30_dias | imediato | dias_parceria"
            onChange={(e) => setForm({ ...form, tipo_gatilho: e.target.value })} /></label>
          <label className="span2">Mensagem *<textarea value={form.mensagem_texto}
            placeholder="Oi {nome}! Parceria de {tempo_parceria}!"
            onChange={(e) => setForm({ ...form, mensagem_texto: e.target.value })} /></label>
          <label className="span2">Caminho imagem (opc)<input value={form.caminho_imagem ?? ""}
            onChange={(e) => setForm({ ...form, caminho_imagem: e.target.value || null })} /></label>
          <label className="span2">Variáveis JSON (opc)<input value={form.variaveis ?? ""}
            placeholder='["nome","tempo_parceria"]'
            onChange={(e) => setForm({ ...form, variaveis: e.target.value || null })} /></label>
          <label>Ativo<input type="checkbox" checked={form.ativo ?? true}
            onChange={(e) => setForm({ ...form, ativo: e.target.checked })} /></label>
        </div>
      </Modal>
    </div>
  );
}
