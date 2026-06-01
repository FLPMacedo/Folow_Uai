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
  plano?: string | null;                 // legado (texto livre)
  grupo?: string | null;                 // legado (texto livre)
  plano_id?: number | null;              // FK → planos_servicos
  grupo_id?: number | null;              // FK → grupos
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
  plano_id?: number | null;
  grupo_id?: number | null;
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
  // Anti-banimento por número
  intervalo_min_minutos?: number | null;
  limite_diario?: number | null;
  horario_inicio?: string | null;        // 'HH:MM'
  horario_fim?: string | null;           // 'HH:MM'
  variacao_texto_ativa: boolean;
  criado_em: string;
  atualizado_em: string;
}

export interface TelefoneCreate {
  numero: string;
  instancia_evolution: string;
  nome_fantasia?: string | null;
  status?: StatusTelefone;
  intervalo_min_minutos?: number | null;
  limite_diario?: number | null;
  horario_inicio?: string | null;
  horario_fim?: string | null;
  variacao_texto_ativa?: boolean;
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

export interface PlanoServico {
  id: number;
  nome: string;
  descricao?: string | null;
  preco?: number | null;
  periodicidade?: string | null;
  duracao_dias?: number | null;
  ativo: boolean;
  criado_em: string;
  atualizado_em: string;
}

export interface PlanoServicoCreate {
  nome: string;
  descricao?: string | null;
  preco?: number | null;
  periodicidade?: string | null;
  duracao_dias?: number | null;
  ativo?: boolean;
}

export type PlanoServicoUpdate = Partial<PlanoServicoCreate>;

export interface Grupo {
  id: number;
  nome: string;
  cor?: string | null;
  descricao?: string | null;
  ativo: boolean;
  criado_em: string;
  atualizado_em: string;
}

export interface GrupoCreate {
  nome: string;
  cor?: string | null;
  descricao?: string | null;
  ativo?: boolean;
}

export type GrupoUpdate = Partial<GrupoCreate>;

export interface Negocio {
  id: number;
  nome: string;
  endereco?: string | null;
  telefone_contato?: string | null;
  whatsapp_duvidas?: string | null;
  email?: string | null;
  site?: string | null;
  descricao?: string | null;
  is_default: boolean;
  ativo: boolean;
  criado_em: string;
  atualizado_em: string;
}

export interface NegocioCreate {
  nome: string;
  endereco?: string | null;
  telefone_contato?: string | null;
  whatsapp_duvidas?: string | null;
  email?: string | null;
  site?: string | null;
  descricao?: string | null;
  is_default?: boolean;
  ativo?: boolean;
}

export type NegocioUpdate = Partial<NegocioCreate>;

export type TipoEvento = "pos_venda" | "evento";

export interface Resposta {
  id: number;
  cliente_id: number | null;
  cliente_nome: string | null;
  telefone_origem: string;
  telefone_destino: string;
  mensagem_texto: string;
  tipo_mensagem?: string | null;
  mensagem_evolution_id?: string | null;
  processado: boolean;
  recebido_em: string;
  criado_em: string;
}

export interface RespostasStats {
  total: number;
  nao_lidas: number;
}

export interface FilaItem {
  id: number;
  cliente_id: number | null;
  cliente_nome: string | null;
  telefone_whatsapp_id: number | null;
  telefone_destino: string;
  modulo: string;
  mensagem_texto: string;
  imagem_path?: string | null;
  status: StatusEnvio;
  erro?: string | null;
  enviado_em?: string | null;
  criado_em: string;
}

export interface FilaResponse {
  pendentes: FilaItem[];
  falhas: FilaItem[];
  bloqueados: FilaItem[];
  total: number;
}

export interface AgendaItem {
  data: string;                  // YYYY-MM-DD
  modulo: string;
  cliente_id: number;
  cliente_nome: string;
  telefone: string;
  titulo: string;
  ja_processado: boolean;
}

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
