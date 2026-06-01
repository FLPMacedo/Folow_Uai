"""SQLModel mapping for FollowUai SQLite schema.

Schema source of truth: ../database/schema.sql
Doc spec: ../../3 modelo.banco.md (typos corrigidos)
"""
from datetime import date, datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================================
# Enums
# ============================================================================
class StatusCliente(str, Enum):
    ativo = "ativo"
    inativo = "inativo"


class StatusEnvio(str, Enum):
    pendente = "pendente"
    enviado = "enviado"
    falha = "falha"
    bloqueado = "bloqueado"


class StatusTelefone(str, Enum):
    ativo = "ativo"
    inativo = "inativo"
    bloqueado = "bloqueado"


class StatusCampanha(str, Enum):
    ativo = "ativo"
    pausado = "pausado"
    concluido = "concluido"


class Modulo(str, Enum):
    pos_venda = "pos_venda"
    evento = "evento"
    comemorativo = "comemorativo"
    sumiu = "sumiu"
    expiracao = "expiracao"


class TipoEvento(str, Enum):
    pos_venda = "pos_venda"
    evento = "evento"


class TipoComemorativo(str, Enum):
    aniversario = "aniversario"
    dias_100 = "100_dias"
    dias_500 = "500_dias"
    dias_1000 = "1000_dias"
    meses_6 = "6_meses"
    ano_1 = "1_ano"


# ============================================================================
# cliente_modulos — opt-in M:N cliente↔módulo
# ============================================================================
class ClienteModulo(SQLModel, table=True):
    __tablename__ = "cliente_modulos"

    cliente_id: int = Field(foreign_key="clientes.id", primary_key=True)
    modulo: str = Field(primary_key=True)  # Enum Modulo armazenado como texto
    ativo: bool = True
    opt_in_em: datetime = Field(default_factory=utcnow)
    observacao: Optional[str] = None


# ============================================================================
# Link table (M:N cliente ↔ tag) — defined first so Relationship can reference
# ============================================================================
class ClienteTag(SQLModel, table=True):
    __tablename__ = "cliente_tags"

    cliente_id: int = Field(foreign_key="clientes.id", primary_key=True)
    tag_id: int = Field(foreign_key="tags.id", primary_key=True)
    criado_em: datetime = Field(default_factory=utcnow)


# ============================================================================
# clientes
# ============================================================================
class Cliente(SQLModel, table=True):
    __tablename__ = "clientes"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    telefone: str = Field(index=True)
    email: Optional[str] = None
    data_nascimento: Optional[date] = None
    data_inicio_parceria: date
    plano: Optional[str] = None      # legado (texto livre, mantido pra compat)
    grupo: Optional[str] = None      # legado (texto livre, mantido pra compat)
    plano_id: Optional[int] = Field(default=None, foreign_key="planos_servicos.id")
    grupo_id: Optional[int] = Field(default=None, foreign_key="grupos.id")
    status: StatusCliente = Field(default=StatusCliente.ativo, index=True)
    observacoes: Optional[str] = None
    criado_em: datetime = Field(default_factory=utcnow)
    atualizado_em: datetime = Field(default_factory=utcnow)

    eventos: List["Evento"] = Relationship(back_populates="cliente")
    comemorativos: List["Comemorativo"] = Relationship(back_populates="cliente")
    planos: List["Plano"] = Relationship(back_populates="cliente")
    envios: List["Envio"] = Relationship(back_populates="cliente")
    respostas: List["Resposta"] = Relationship(back_populates="cliente")
    tags: List["Tag"] = Relationship(back_populates="clientes", link_model=ClienteTag)


# ============================================================================
# telefones_whatsapp
# ============================================================================
class TelefoneWhatsApp(SQLModel, table=True):
    __tablename__ = "telefones_whatsapp"

    id: Optional[int] = Field(default=None, primary_key=True)
    numero: str = Field(unique=True)
    instancia_evolution: str
    nome_fantasia: Optional[str] = None
    status: StatusTelefone = Field(default=StatusTelefone.ativo, index=True)
    ultimo_envio: Optional[datetime] = None
    total_envios: int = 0
    # Anti-banimento por número (override do global)
    intervalo_min_minutos: Optional[int] = None  # None = usa Sender default
    limite_diario: Optional[int] = None           # None = ilimitado
    horario_inicio: Optional[str] = None          # 'HH:MM' (None = sem restrição)
    horario_fim: Optional[str] = None             # 'HH:MM'
    variacao_texto_ativa: bool = False
    criado_em: datetime = Field(default_factory=utcnow)
    atualizado_em: datetime = Field(default_factory=utcnow)

    envios: List["Envio"] = Relationship(back_populates="telefone_whatsapp")
    campanhas: List["Campanha"] = Relationship(back_populates="telefone_whatsapp")


# ============================================================================
# templates
# ============================================================================
class Template(SQLModel, table=True):
    __tablename__ = "templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    modulo: Modulo = Field(index=True)
    tipo_gatilho: str
    mensagem_texto: str
    caminho_imagem: Optional[str] = None
    variaveis: Optional[str] = None  # JSON string
    ativo: bool = True
    criado_em: datetime = Field(default_factory=utcnow)
    atualizado_em: datetime = Field(default_factory=utcnow)

    campanhas: List["Campanha"] = Relationship(back_populates="template")
    envios: List["Envio"] = Relationship(back_populates="template")


# ============================================================================
# campanhas
# ============================================================================
class Campanha(SQLModel, table=True):
    __tablename__ = "campanhas"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    modulo: Modulo = Field(index=True)
    template_id: int = Field(foreign_key="templates.id")
    telefone_whatsapp_id: Optional[int] = Field(
        default=None, foreign_key="telefones_whatsapp.id"
    )
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    gatilho_data: Optional[str] = None
    valor_gatilho: Optional[int] = None
    intervalo_minutos: int = 5
    status: StatusCampanha = Field(default=StatusCampanha.ativo, index=True)
    total_previsto: Optional[int] = None
    total_enviados: int = 0
    criado_em: datetime = Field(default_factory=utcnow)
    atualizado_em: datetime = Field(default_factory=utcnow)

    template: Template = Relationship(back_populates="campanhas")
    telefone_whatsapp: Optional[TelefoneWhatsApp] = Relationship(back_populates="campanhas")
    envios: List["Envio"] = Relationship(back_populates="campanha")


# ============================================================================
# envios
# ============================================================================
class Envio(SQLModel, table=True):
    __tablename__ = "envios"

    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="clientes.id", index=True)
    telefone_whatsapp_id: Optional[int] = Field(
        default=None, foreign_key="telefones_whatsapp.id"
    )
    campanha_id: Optional[int] = Field(default=None, foreign_key="campanhas.id")
    template_id: Optional[int] = Field(default=None, foreign_key="templates.id")
    modulo: Modulo
    telefone_destino: str
    mensagem_texto: str
    imagem_path: Optional[str] = None
    status: StatusEnvio = Field(index=True)
    mensagem_evolution_id: Optional[str] = None
    erro: Optional[str] = None
    enviado_em: Optional[datetime] = Field(default=None, index=True)
    criado_em: datetime = Field(default_factory=utcnow)

    cliente: Cliente = Relationship(back_populates="envios")
    telefone_whatsapp: Optional[TelefoneWhatsApp] = Relationship(back_populates="envios")
    campanha: Optional[Campanha] = Relationship(back_populates="envios")
    template: Optional[Template] = Relationship(back_populates="envios")


# ============================================================================
# respostas
# ============================================================================
class Resposta(SQLModel, table=True):
    __tablename__ = "respostas"

    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: Optional[int] = Field(default=None, foreign_key="clientes.id", index=True)
    telefone_origem: str
    telefone_destino: str
    mensagem_texto: str
    tipo_mensagem: Optional[str] = "text"
    mensagem_evolution_id: Optional[str] = None
    recebido_em: datetime = Field(default_factory=utcnow, index=True)
    processado: bool = False
    criado_em: datetime = Field(default_factory=utcnow)

    cliente: Optional[Cliente] = Relationship(back_populates="respostas")


# ============================================================================
# eventos
# ============================================================================
class Evento(SQLModel, table=True):
    __tablename__ = "eventos"

    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="clientes.id", index=True)
    nome_evento: str
    tipo_evento: TipoEvento
    data_evento: date = Field(index=True)
    data_compra: Optional[date] = None
    vespera_mensagem_enviada: bool = False
    pos_mensagem_enviada: bool = False
    observacoes: Optional[str] = None
    criado_em: datetime = Field(default_factory=utcnow)
    atualizado_em: datetime = Field(default_factory=utcnow)

    cliente: Cliente = Relationship(back_populates="eventos")


# ============================================================================
# comemorativos
# ============================================================================
class Comemorativo(SQLModel, table=True):
    __tablename__ = "comemorativos"

    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="clientes.id", index=True)
    tipo: TipoComemorativo
    data_gatilho: date = Field(index=True)
    dias_parceria: Optional[int] = None
    mensagem_enviada: bool = False
    imagem_enviada: bool = False
    caminho_imagem: Optional[str] = None
    criado_em: datetime = Field(default_factory=utcnow)
    atualizado_em: datetime = Field(default_factory=utcnow)

    cliente: Cliente = Relationship(back_populates="comemorativos")


# ============================================================================
# planos
# ============================================================================
class Plano(SQLModel, table=True):
    __tablename__ = "planos"

    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="clientes.id", index=True)
    nome_plano: str
    data_inicio: date
    data_fim: date = Field(index=True)
    dias_restantes: Optional[int] = None
    mensagem_30_dias_enviada: bool = False
    mensagem_15_dias_enviada: bool = False
    mensagem_7_dias_enviada: bool = False
    mensagem_3_dias_enviada: bool = False
    renova: bool = False
    data_renovacao: Optional[date] = None
    observacoes: Optional[str] = None
    criado_em: datetime = Field(default_factory=utcnow)
    atualizado_em: datetime = Field(default_factory=utcnow)

    cliente: Cliente = Relationship(back_populates="planos")


# ============================================================================
# tags
# ============================================================================
class Tag(SQLModel, table=True):
    __tablename__ = "tags"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(unique=True)
    cor: Optional[str] = None
    descricao: Optional[str] = None
    criado_em: datetime = Field(default_factory=utcnow)

    clientes: List[Cliente] = Relationship(back_populates="tags", link_model=ClienteTag)


# ============================================================================
# planos_servicos — catálogo
# ============================================================================
class PlanoServico(SQLModel, table=True):
    __tablename__ = "planos_servicos"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(unique=True)
    descricao: Optional[str] = None
    preco: Optional[float] = None
    periodicidade: Optional[str] = None       # 'mensal' | 'anual' | 'unico'
    duracao_dias: Optional[int] = None
    ativo: bool = True
    criado_em: datetime = Field(default_factory=utcnow)
    atualizado_em: datetime = Field(default_factory=utcnow)


# ============================================================================
# grupos — categorias de clientes
# ============================================================================
class Grupo(SQLModel, table=True):
    __tablename__ = "grupos"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(unique=True)
    cor: Optional[str] = None
    descricao: Optional[str] = None
    ativo: bool = True
    criado_em: datetime = Field(default_factory=utcnow)
    atualizado_em: datetime = Field(default_factory=utcnow)


# ============================================================================
# negocios — multi-empresa
# ============================================================================
class Negocio(SQLModel, table=True):
    __tablename__ = "negocios"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    endereco: Optional[str] = None
    telefone_contato: Optional[str] = None
    whatsapp_duvidas: Optional[str] = None
    email: Optional[str] = None
    site: Optional[str] = None
    descricao: Optional[str] = None
    is_default: bool = False
    ativo: bool = True
    criado_em: datetime = Field(default_factory=utcnow)
    atualizado_em: datetime = Field(default_factory=utcnow)


# ============================================================================
# backups (audit log)
# ============================================================================
class Backup(SQLModel, table=True):
    __tablename__ = "backups"

    id: Optional[int] = Field(default=None, primary_key=True)
    caminho_arquivo: str
    tamanho_bytes: Optional[int] = None
    descricao: Optional[str] = None
    criado_em: datetime = Field(default_factory=utcnow)
