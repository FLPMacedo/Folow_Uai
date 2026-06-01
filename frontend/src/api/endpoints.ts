// Endpoints tipados — todos retornam Promise<T>.
import { api, API_BASE } from "./client";
import type {
  AgendaItem,
  Backup,
  BroadcastPreview,
  BroadcastResult,
  ClienteModulosResponse,
  EventoBroadcastCreate,
  FilaResponse,
  Resposta,
  RespostasStats,
  Cliente,
  ClienteCreate,
  ClienteUpdate,
  DispatchStats,
  Envio,
  Evento,
  EventoCreate,
  EventoUpdate,
  Grupo,
  GrupoCreate,
  GrupoUpdate,
  ImportResult,
  ModuloStats,
  Negocio,
  NegocioCreate,
  NegocioUpdate,
  PlanoServico,
  PlanoServicoCreate,
  PlanoServicoUpdate,
  Telefone,
  TelefoneCreate,
  TelefoneUpdate,
  Template,
  TemplateCreate,
  TemplateUpdate,
} from "./types";

// =========================================================================
// Health
// =========================================================================
export const getHealth = () => api.get<{ status: string }>("/../health");

// =========================================================================
// Clientes
// =========================================================================
export const listClientes = (params?: {
  status?: string; grupo?: string; q?: string; limit?: number; offset?: number;
}) => api.get<Cliente[]>("/clientes", params);

export const getCliente = (id: number) =>
  api.get<Cliente>(`/clientes/${id}`);

export const createCliente = (payload: ClienteCreate) =>
  api.post<Cliente>("/clientes", payload);

export const updateCliente = (id: number, payload: ClienteUpdate) =>
  api.put<Cliente>(`/clientes/${id}`, payload);

export const deleteCliente = (id: number, force = false) =>
  api.delete(`/clientes/${id}${force ? "?force=true" : ""}`);

export async function importClientesXlsx(file: File): Promise<ImportResult> {
  const form = new FormData();
  form.append("file", file);
  const r = await fetch(`${API_BASE}/clientes/import`, { method: "POST", body: form });
  if (!r.ok) throw new Error(`Import falhou: ${r.status} ${await r.text()}`);
  return r.json();
}

export const exportClientesXlsxUrl = (status?: string) =>
  `${API_BASE}/clientes/export.xlsx${status ? `?status=${status}` : ""}`;

// =========================================================================
// Telefones
// =========================================================================
export const listTelefones = () => api.get<Telefone[]>("/telefones");

export const createTelefone = (payload: TelefoneCreate) =>
  api.post<Telefone>("/telefones", payload);

export const updateTelefone = (id: number, payload: TelefoneUpdate) =>
  api.put<Telefone>(`/telefones/${id}`, payload);

export const deleteTelefone = (id: number) =>
  api.delete(`/telefones/${id}`);

export const createInstance = (id: number) =>
  api.post<Record<string, unknown>>(`/telefones/${id}/create-instance`);

export const telefoneState = (id: number) =>
  api.get<Record<string, unknown>>(`/telefones/${id}/state`);

// =========================================================================
// Templates
// =========================================================================
export const listTemplates = (params?: { modulo?: string; ativo?: boolean }) =>
  api.get<Template[]>("/templates", params);

export const getTemplate = (id: number) => api.get<Template>(`/templates/${id}`);

export const createTemplate = (payload: TemplateCreate) =>
  api.post<Template>("/templates", payload);

export const updateTemplate = (id: number, payload: TemplateUpdate) =>
  api.put<Template>(`/templates/${id}`, payload);

export const deleteTemplate = (id: number) =>
  api.delete(`/templates/${id}`);

// =========================================================================
// Envios + relatórios
// =========================================================================
export const listEnvios = (params?: {
  modulo?: string; status?: string; cliente_id?: number; since?: string;
  limit?: number; offset?: number;
}) => api.get<Envio[]>("/envios", params);

export const enviosStats = () => api.get<ModuloStats[]>("/envios/stats");

// =========================================================================
// Admin
// =========================================================================
export const createBackup = (descricao?: string) =>
  api.post<Backup>("/admin/backup", undefined, descricao ? { descricao } : undefined);

export const listBackups = () => api.get<Backup[]>("/admin/backups");

export const dispatchComemorativo = (today?: string) =>
  api.post<DispatchStats>(
    "/admin/dispatch/comemorativo",
    undefined,
    today ? { today } : undefined,
  );

export const dispatchExpiracao = (today?: string) =>
  api.post<DispatchStats>(
    "/admin/dispatch/expiracao",
    undefined,
    today ? { today } : undefined,
  );

export const dispatchPosVenda = (today?: string) =>
  api.post<DispatchStats>(
    "/admin/dispatch/pos_venda",
    undefined,
    today ? { today } : undefined,
  );

export const dispatchEvento = (today?: string) =>
  api.post<DispatchStats>(
    "/admin/dispatch/evento",
    undefined,
    today ? { today } : undefined,
  );

// =========================================================================
// Eventos (pós-venda + agendados)
// =========================================================================
export const listEventos = (params?: {
  cliente_id?: number; tipo_evento?: string; limit?: number; offset?: number;
}) => api.get<Evento[]>("/eventos", params);

export const getEvento = (id: number) => api.get<Evento>(`/eventos/${id}`);

export const createEvento = (payload: EventoCreate) =>
  api.post<Evento>("/eventos", payload);

export const updateEvento = (id: number, payload: EventoUpdate) =>
  api.put<Evento>(`/eventos/${id}`, payload);

export const deleteEvento = (id: number) =>
  api.delete(`/eventos/${id}`);

export const previewBroadcast = (grupoId: number) =>
  api.get<BroadcastPreview>(`/eventos/preview-broadcast/${grupoId}`);

export const createEventoBroadcast = (payload: EventoBroadcastCreate) =>
  api.post<BroadcastResult>("/eventos/broadcast", payload);

// =========================================================================
// Negócios (meu negócio / multi-empresa)
// =========================================================================
export const listNegocios = (ativo?: boolean) =>
  api.get<Negocio[]>("/negocios", ativo === undefined ? undefined : { ativo });

export const getNegocioDefault = () =>
  api.get<Negocio | null>("/negocios/default");

export const getNegocio = (id: number) => api.get<Negocio>(`/negocios/${id}`);

export const createNegocio = (payload: NegocioCreate) =>
  api.post<Negocio>("/negocios", payload);

export const updateNegocio = (id: number, payload: NegocioUpdate) =>
  api.put<Negocio>(`/negocios/${id}`, payload);

export const deleteNegocio = (id: number) =>
  api.delete(`/negocios/${id}`);

// =========================================================================
// Planos & Serviços (catálogo)
// =========================================================================
export const listPlanos = (ativo?: boolean) =>
  api.get<PlanoServico[]>("/planos-servicos",
    ativo === undefined ? undefined : { ativo });

export const createPlano = (payload: PlanoServicoCreate) =>
  api.post<PlanoServico>("/planos-servicos", payload);

export const updatePlano = (id: number, payload: PlanoServicoUpdate) =>
  api.put<PlanoServico>(`/planos-servicos/${id}`, payload);

export const deletePlano = (id: number) =>
  api.delete(`/planos-servicos/${id}`);

// =========================================================================
// Grupos
// =========================================================================
export const listGrupos = (ativo?: boolean) =>
  api.get<Grupo[]>("/grupos",
    ativo === undefined ? undefined : { ativo });

export const createGrupo = (payload: GrupoCreate) =>
  api.post<Grupo>("/grupos", payload);

export const updateGrupo = (id: number, payload: GrupoUpdate) =>
  api.put<Grupo>(`/grupos/${id}`, payload);

export const deleteGrupo = (id: number) =>
  api.delete(`/grupos/${id}`);

// =========================================================================
// Agenda (preview de disparos futuros)
// =========================================================================
export const getAgenda = (from: string, to: string) =>
  api.get<AgendaItem[]>("/agenda", { from, to });

// =========================================================================
// Fila de trabalho
// =========================================================================
export const getFila = (opts?: {
  incluir_falhas?: boolean;
  incluir_pendentes?: boolean;
  incluir_bloqueados?: boolean;
}) => api.get<FilaResponse>("/fila", opts);

export const retryEnvio = (id: number) =>
  api.post<{ ok: boolean; envio_id: number; novo_status: string }>(
    `/fila/${id}/retry`,
  );

export const marcarEnviadoManual = (id: number, nota?: string) =>
  api.post<{ ok: boolean; envio_id: number }>(
    `/fila/${id}/marcar-enviado`,
    undefined,
    nota ? { nota } : undefined,
  );

export const enviarAgora = (id: number) =>
  api.post<{ ok: boolean; envio_id_original: number; envio_id_novo: number; status_novo: string }>(
    `/fila/${id}/enviar-agora`,
  );

// =========================================================================
// Respostas (feedback dos clientes recebido via webhook)
// =========================================================================
export const listRespostas = (params?: {
  cliente_id?: number; processado?: boolean; q?: string;
  limit?: number; offset?: number;
}) => api.get<Resposta[]>("/respostas", params);

export const respostasStats = () =>
  api.get<RespostasStats>("/respostas/stats");

export const marcarLida = (id: number) =>
  api.post<{ ok: boolean }>(`/respostas/${id}/marcar-lida`);

export const marcarNaoLida = (id: number) =>
  api.post<{ ok: boolean }>(`/respostas/${id}/marcar-nao-lida`);

export const deleteResposta = (id: number) =>
  api.delete(`/respostas/${id}`);

// =========================================================================
// Opt-in cliente↔módulo
// =========================================================================
export const getClienteModulos = (clienteId: number) =>
  api.get<ClienteModulosResponse>(`/modulos/cliente/${clienteId}`);

export const setClienteModulos = (
  clienteId: number, modulos: Record<string, boolean>,
) =>
  api.put<ClienteModulosResponse>(`/modulos/cliente/${clienteId}`, { modulos });
