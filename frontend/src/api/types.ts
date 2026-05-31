// Espelha schemas Pydantic do backend (backend/api/schemas.py + models.py)
// Mantenha em sync ao mudar models. TODO: gerar via openapi futuro.

export type StatusCliente = "ativo" | "inativo";
export type StatusTelefone = "ativo" | "inativo" | "bloqueado";
export type StatusEnvio = "pendente" | "enviado" | "falha" | "bloqueado";
export type StatusCampanha = "ativo" | "pausado" | "concluido";
export type Modulo = "pos_venda" | "evento" | "comemorativo" | "sumiu" | "expiracao";

export interface Cliente {
  id: number;
  nome: string;
  telefone: string;
  email?: string | null;
  data_nascimento?: string | null;       // ISO YYYY-MM-DD
  data_inicio_parceria: string;
  plano?: string | null;
  grupo?: string | null;
  status: StatusCliente;
  observacoes?: string | null;
  criado_em: string;
  atualizado_em: string;
}

export interface ClienteCreate {
  nome: string;
  telefone: string;
  email?: string | null;
  data_nascimento?: string | null;
  data_inicio_parceria: string;
  plano?: string | null;
  grupo?: string | null;
  status?: StatusCliente;
  observacoes?: string | null;
}

export type ClienteUpdate = Partial<ClienteCreate>;

export interface Telefone {
  id: number;
  numero: string;
  instancia_evolution: string;
  nome_fantasia?: string | null;
  status: StatusTelefone;
  ultimo_envio?: string | null;
  total_envios: number;
  criado_em: string;
  atualizado_em: string;
}

export interface TelefoneCreate {
  numero: string;
  instancia_evolution: string;
  nome_fantasia?: string | null;
  status?: StatusTelefone;
}

export type TelefoneUpdate = Partial<TelefoneCreate>;

export interface Template {
  id: number;
  nome: string;
  modulo: Modulo;
  tipo_gatilho: string;
  mensagem_texto: string;
  caminho_imagem?: string | null;
  variaveis?: string | null;
  ativo: boolean;
  criado_em: string;
  atualizado_em: string;
}

export interface TemplateCreate {
  nome: string;
  modulo: Modulo;
  tipo_gatilho: string;
  mensagem_texto: string;
  caminho_imagem?: string | null;
  variaveis?: string | null;
  ativo?: boolean;
}

export type TemplateUpdate = Partial<TemplateCreate>;

export interface Envio {
  id: number;
  cliente_id: number;
  telefone_whatsapp_id?: number | null;
  campanha_id?: number | null;
  template_id?: number | null;
  modulo: Modulo;
  telefone_destino: string;
  mensagem_texto: string;
  imagem_path?: string | null;
  status: StatusEnvio;
  mensagem_evolution_id?: string | null;
  erro?: string | null;
  enviado_em?: string | null;
  criado_em: string;
}

export interface ModuloStats {
  modulo: string;
  total_envios: number;
  enviados: number;
  falhas: number;
  bloqueados: number;
  pendentes: number;
}

export interface Backup {
  id: number;
  caminho_arquivo: string;
  tamanho_bytes?: number | null;
  descricao?: string | null;
  criado_em: string;
}

export interface ImportResult {
  inseridos: number;
  duplicados: number;
  erros: Array<{ row: number; column?: string | null; message: string }>;
}

export interface DispatchStats {
  enviados: number;
  falhas: number;
  pendentes: number;
  ignorados: number;
}

export type TipoEvento = "pos_venda" | "evento";

export interface Evento {
  id: number;
  cliente_id: number;
  nome_evento: string;
  tipo_evento: TipoEvento;
  data_evento: string;
  data_compra?: string | null;
  vespera_mensagem_enviada: boolean;
  pos_mensagem_enviada: boolean;
  observacoes?: string | null;
  criado_em: string;
  atualizado_em: string;
}

export interface EventoCreate {
  cliente_id: number;
  nome_evento: string;
  tipo_evento: TipoEvento;
  data_evento: string;
  data_compra?: string | null;
  observacoes?: string | null;
}

export type EventoUpdate = Partial<Omit<EventoCreate, "cliente_id">> & {
  vespera_mensagem_enviada?: boolean;
  pos_mensagem_enviada?: boolean;
};
