"""Schemas Pydantic pra Create/Update.

Padrão SQLModel: classes sem `table=True` valem como Pydantic puro.
Excluem `id`, timestamps e relations — só payload mutável.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import SQLModel

from backend.models import (
    Modulo,
    StatusCampanha,
    StatusCliente,
    StatusEnvio,
    StatusTelefone,
    TipoComemorativo,
    TipoEvento,
)


# ============================================================================
# Cliente
# ============================================================================
class ClienteCreate(SQLModel):
    nome: str
    telefone: str
    email: Optional[str] = None
    data_nascimento: Optional[date] = None
    data_inicio_parceria: date
    plano: Optional[str] = None              # legado
    grupo: Optional[str] = None              # legado
    plano_id: Optional[int] = None           # FK → planos_servicos
    grupo_id: Optional[int] = None           # FK → grupos
    status: StatusCliente = StatusCliente.ativo
    observacoes: Optional[str] = None


class ClienteUpdate(SQLModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    data_nascimento: Optional[date] = None
    data_inicio_parceria: Optional[date] = None
    plano: Optional[str] = None
    grupo: Optional[str] = None
    plano_id: Optional[int] = None
    grupo_id: Optional[int] = None
    status: Optional[StatusCliente] = None
    observacoes: Optional[str] = None


# ============================================================================
# TelefoneWhatsApp
# ============================================================================
class TelefoneCreate(SQLModel):
    numero: str
    instancia_evolution: str
    nome_fantasia: Optional[str] = None
    status: StatusTelefone = StatusTelefone.ativo
    intervalo_min_minutos: Optional[int] = None
    limite_diario: Optional[int] = None
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None
    variacao_texto_ativa: bool = False


class TelefoneUpdate(SQLModel):
    numero: Optional[str] = None
    instancia_evolution: Optional[str] = None
    nome_fantasia: Optional[str] = None
    status: Optional[StatusTelefone] = None
    intervalo_min_minutos: Optional[int] = None
    limite_diario: Optional[int] = None
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None
    variacao_texto_ativa: Optional[bool] = None


# ============================================================================
# Template
# ============================================================================
class TemplateCreate(SQLModel):
    nome: str
    modulo: Modulo
    tipo_gatilho: str
    mensagem_texto: str
    caminho_imagem: Optional[str] = None
    variaveis: Optional[str] = None
    ativo: bool = True


# ============================================================================
# Plano de Serviço (catálogo)
# ============================================================================
class PlanoServicoCreate(SQLModel):
    nome: str
    descricao: Optional[str] = None
    preco: Optional[float] = None
    periodicidade: Optional[str] = None
    duracao_dias: Optional[int] = None
    ativo: bool = True


class PlanoServicoUpdate(SQLModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    preco: Optional[float] = None
    periodicidade: Optional[str] = None
    duracao_dias: Optional[int] = None
    ativo: Optional[bool] = None


# ============================================================================
# Grupo (categoria de cliente)
# ============================================================================
class GrupoCreate(SQLModel):
    nome: str
    cor: Optional[str] = None
    descricao: Optional[str] = None
    ativo: bool = True


class GrupoUpdate(SQLModel):
    nome: Optional[str] = None
    cor: Optional[str] = None
    descricao: Optional[str] = None
    ativo: Optional[bool] = None


# ============================================================================
# Negócio (multi-empresa)
# ============================================================================
class NegocioCreate(SQLModel):
    nome: str
    endereco: Optional[str] = None
    telefone_contato: Optional[str] = None
    whatsapp_duvidas: Optional[str] = None
    email: Optional[str] = None
    site: Optional[str] = None
    descricao: Optional[str] = None
    is_default: bool = False
    ativo: bool = True


class NegocioUpdate(SQLModel):
    nome: Optional[str] = None
    endereco: Optional[str] = None
    telefone_contato: Optional[str] = None
    whatsapp_duvidas: Optional[str] = None
    email: Optional[str] = None
    site: Optional[str] = None
    descricao: Optional[str] = None
    is_default: Optional[bool] = None
    ativo: Optional[bool] = None


# ============================================================================
# Evento (pós-venda + evento agendado)
# ============================================================================
class EventoCreate(SQLModel):
    cliente_id: int
    nome_evento: str
    tipo_evento: TipoEvento
    data_evento: date
    data_compra: Optional[date] = None
    observacoes: Optional[str] = None


class EventoUpdate(SQLModel):
    nome_evento: Optional[str] = None
    tipo_evento: Optional[TipoEvento] = None
    data_evento: Optional[date] = None
    data_compra: Optional[date] = None
    observacoes: Optional[str] = None
    vespera_mensagem_enviada: Optional[bool] = None
    pos_mensagem_enviada: Optional[bool] = None


class TemplateUpdate(SQLModel):
    nome: Optional[str] = None
    modulo: Optional[Modulo] = None
    tipo_gatilho: Optional[str] = None
    mensagem_texto: Optional[str] = None
    caminho_imagem: Optional[str] = None
    variaveis: Optional[str] = None
    ativo: Optional[bool] = None


# ============================================================================
# Webhook payload (Evolution → respostas)
# ============================================================================
class WebhookEvent(SQLModel):
    """Esquema flexível — Evolution v2 varia entre versões. Campos opcionais."""
    event: Optional[str] = None
    instance: Optional[str] = None
    data: Optional[dict] = None


# ============================================================================
# Stats / relatórios
# ============================================================================
class ModuloStats(SQLModel):
    modulo: str
    total_envios: int
    enviados: int
    falhas: int
    bloqueados: int
    pendentes: int


# Re-export para conveniência
__all__ = [
    "ClienteCreate", "ClienteUpdate",
    "TelefoneCreate", "TelefoneUpdate",
    "TemplateCreate", "TemplateUpdate",
    "EventoCreate", "EventoUpdate",
    "NegocioCreate", "NegocioUpdate",
    "PlanoServicoCreate", "PlanoServicoUpdate",
    "GrupoCreate", "GrupoUpdate",
    "WebhookEvent", "ModuloStats",
    "Modulo", "StatusCliente", "StatusEnvio", "StatusTelefone",
    "StatusCampanha", "TipoComemorativo", "TipoEvento",
]
