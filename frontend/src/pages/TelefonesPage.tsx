import { useEffect, useState } from "react";
import {
  createInstance, createTelefone, deleteTelefone, listTelefones,
  telefoneState, updateTelefone,
} from "../api/endpoints";
import type { Telefone, TelefoneCreate } from "../api/types";
import Modal from "../components/Modal";
import ErrorBanner from "../components/ErrorBanner";

const emptyForm: TelefoneCreate = {
  numero: "", instancia_evolution: "", status: "ativo",
  intervalo_min_minutos: null, limite_diario: null,
  horario_inicio: null, horario_fim: null,
  variacao_texto_ativa: false,
};

export default function TelefonesPage() {
  const [tels, setTels] = useState<Telefone[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<TelefoneCreate>(emptyForm);
  const [editing, setEditing] = useState<Telefone | null>(null);
  const [qrModal, setQrModal] = useState<{ qr?: string; state?: string; raw?: unknown } | null>(null);

  const load = async () => {
    try { setTels(await listTelefones()); }
    catch (e) { setError(String(e)); }
  };
  useEffect(() => { void load(); }, []);

  const save = async () => {
    try {
      if (editing) await updateTelefone(editing.id, form);
      else await createTelefone(form);
      setModalOpen(false); setError(null); await load();
    } catch (e) { setError(String(e)); }
  };

  const openCreate = () => {
    setEditing(null); setForm(emptyForm); setModalOpen(true);
  };
  const openEdit = (t: Telefone) => {
    setEditing(t);
    setForm({
      numero: t.numero,
      instancia_evolution: t.instancia_evolution,
      nome_fantasia: t.nome_fantasia ?? undefined,
      status: t.status,
      intervalo_min_minutos: t.intervalo_min_minutos ?? null,
      limite_diario: t.limite_diario ?? null,
      horario_inicio: t.horario_inicio ?? null,
      horario_fim: t.horario_fim ?? null,
      variacao_texto_ativa: t.variacao_texto_ativa ?? false,
    });
    setModalOpen(true);
  };

  const remove = async (t: Telefone) => {
    if (!confirm(`Deletar ${t.numero}?`)) return;
    try { await deleteTelefone(t.id); await load(); }
    catch (e) { setError(String(e)); }
  };

  const connect = async (t: Telefone) => {
    try {
      const result = await createInstance(t.id);
      const qr = extractQr(result);
      setQrModal({ qr, raw: result });
    } catch (e) { setError(String(e)); }
  };

  const refreshState = async (t: Telefone) => {
    try {
      const s = await telefoneState(t.id);
      setQrModal({ state: JSON.stringify(s), raw: s });
    } catch (e) { setError(String(e)); }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Telefones WhatsApp</h1>
        <button className="btn primary" onClick={openCreate}>+ Novo telefone</button>
      </div>
      <ErrorBanner message={error} onClose={() => setError(null)} />

      <div className="card">
        {tels.length === 0 ? (
          <div className="empty">Nenhum telefone cadastrado. Adicione pelo menos 1.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Número</th>
                <th>Instância Evolution</th>
                <th>Status</th>
                <th>Último envio</th>
                <th>Total enviado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {tels.map((t) => (
                <tr key={t.id}>
                  <td>{t.numero}{t.nome_fantasia && <div className="muted">{t.nome_fantasia}</div>}</td>
                  <td>{t.instancia_evolution}</td>
                  <td>
                    <span className={`badge ${
                      t.status === "ativo" ? "ok" :
                      t.status === "bloqueado" ? "bad" : "muted"
                    }`}>{t.status}</span>
                  </td>
                  <td>{t.ultimo_envio ? new Date(t.ultimo_envio).toLocaleString("pt-BR") : <span className="muted">nunca</span>}</td>
                  <td>{t.total_envios}</td>
                  <td className="btn-row" style={{ justifyContent: "flex-end" }}>
                    <button className="btn" onClick={() => void connect(t)}>Conectar</button>
                    <button className="btn" onClick={() => void refreshState(t)}>Estado</button>
                    <button className="btn" onClick={() => openEdit(t)}>Editar</button>
                    <button className="btn danger" onClick={() => void remove(t)}>Del</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal title={editing ? "Editar telefone" : "Novo telefone"}
        open={modalOpen} onClose={() => setModalOpen(false)}
        footer={
          <>
            <button className="btn" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button className="btn primary" onClick={() => void save()}>Salvar</button>
          </>
        }>
        <div className="form-grid">
          <label>Número *<input value={form.numero} placeholder="+5531999999999"
            onChange={(e) => setForm({ ...form, numero: e.target.value })} /></label>
          <label>Instância Evolution *<input value={form.instancia_evolution}
            placeholder="followuai-instancia-1"
            onChange={(e) => setForm({ ...form, instancia_evolution: e.target.value })} /></label>
          <label>Nome fantasia<input value={form.nome_fantasia ?? ""}
            onChange={(e) => setForm({ ...form, nome_fantasia: e.target.value || null })} /></label>
          <label>Status<select value={form.status ?? "ativo"}
            onChange={(e) => setForm({ ...form, status: e.target.value as "ativo" | "inativo" | "bloqueado" })}>
            <option value="ativo">Ativo</option>
            <option value="inativo">Inativo</option>
            <option value="bloqueado">Bloqueado</option>
          </select></label>

          <div className="span2" style={{ borderTop: "1px solid #e5e7eb",
            paddingTop: 12, marginTop: 4 }}>
            <strong>Anti-banimento</strong>
            <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
              Deixe em branco para usar os padrões globais.
            </div>
          </div>

          <label>Intervalo entre envios (min)
            <input type="number" min={0}
              placeholder="padrão 5"
              value={form.intervalo_min_minutos ?? ""}
              onChange={(e) => setForm({
                ...form,
                intervalo_min_minutos: e.target.value ? Number(e.target.value) : null,
              })} />
          </label>
          <label>Limite diário de envios
            <input type="number" min={0}
              placeholder="ilimitado"
              value={form.limite_diario ?? ""}
              onChange={(e) => setForm({
                ...form,
                limite_diario: e.target.value ? Number(e.target.value) : null,
              })} />
          </label>
          <label>Horário início (HH:MM)
            <input type="time" value={form.horario_inicio ?? ""}
              onChange={(e) => setForm({ ...form, horario_inicio: e.target.value || null })} />
          </label>
          <label>Horário fim (HH:MM)
            <input type="time" value={form.horario_fim ?? ""}
              onChange={(e) => setForm({ ...form, horario_fim: e.target.value || null })} />
          </label>
          <label>Variação de texto<input type="checkbox"
            checked={form.variacao_texto_ativa ?? false}
            onChange={(e) => setForm({ ...form, variacao_texto_ativa: e.target.checked })} />
          </label>
        </div>
      </Modal>

      <Modal title="Conectar WhatsApp" open={qrModal !== null}
        onClose={() => setQrModal(null)}
        footer={<button className="btn" onClick={() => setQrModal(null)}>Fechar</button>}>
        {qrModal?.qr ? (
          <div style={{ textAlign: "center" }}>
            <p>Escaneie no WhatsApp → Aparelhos conectados:</p>
            <img src={qrModal.qr} alt="QR code" style={{ maxWidth: 320 }} />
          </div>
        ) : qrModal?.state ? (
          <pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>{qrModal.state}</pre>
        ) : (
          <pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>
            {JSON.stringify(qrModal?.raw, null, 2)}
          </pre>
        )}
      </Modal>
    </div>
  );
}

function extractQr(payload: unknown): string | undefined {
  if (!payload || typeof payload !== "object") return undefined;
  const p = payload as Record<string, unknown>;
  const qrObj = p.qrcode;
  if (qrObj && typeof qrObj === "object") {
    const b64 = (qrObj as Record<string, unknown>).base64;
    if (typeof b64 === "string") {
      return b64.startsWith("data:") ? b64 : `data:image/png;base64,${b64}`;
    }
  }
  if (typeof p.base64 === "string") {
    const b = p.base64;
    return b.startsWith("data:") ? b : `data:image/png;base64,${b}`;
  }
  return undefined;
}
