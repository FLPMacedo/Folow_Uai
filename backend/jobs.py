"""Jobs MVP do FollowUai.

Funções puras: recebem `Session` + `Sender` + `today`. Sem dependência do
APScheduler — facilita teste e re-invocação manual.

MVP scope (doc 1 §9):
  - Comemorativo: aniversário + parceria 100/180/365/500/1000 dias
  - Expiração: planos com 30/15/7/3 dias restantes
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from loguru import logger
from sqlmodel import Session, select

from backend.models import (
    Cliente,
    Comemorativo,
    Envio,
    Evento,
    Modulo,
    Plano,
    StatusCliente,
    StatusEnvio,
    Template,
    TipoComemorativo,
    TipoEvento,
)
from backend.sender import Sender
from backend.templates import derive_cliente_vars, render

MARCOS_PARCERIA: dict[int, TipoComemorativo] = {
    100:  TipoComemorativo.dias_100,
    180:  TipoComemorativo.meses_6,
    365:  TipoComemorativo.ano_1,
    500:  TipoComemorativo.dias_500,
    1000: TipoComemorativo.dias_1000,
}

EXPIRACAO_GATILHOS: tuple[int, ...] = (30, 15, 7, 3)
EXPIRACAO_FLAG: dict[int, str] = {
    30: "mensagem_30_dias_enviada",
    15: "mensagem_15_dias_enviada",
    7:  "mensagem_7_dias_enviada",
    3:  "mensagem_3_dias_enviada",
}


# ============================================================================
# Comemorativo
# ============================================================================
def dispatch_comemorativo(
    session: Session,
    sender: Sender,
    *,
    template_aniversario: str = (
        "Feliz aniversário, {nome}! 🎉🎂\nObrigado pela parceria de {tempo_parceria}!"
    ),
    template_marco: str = (
        "Oi, {nome}! Chegamos a {tempo_parceria} de parceria! 🎉\nObrigado!"
    ),
    today: Optional[date] = None,
) -> dict[str, int]:
    """Roda aniversários e marcos de parceria do dia.

    Retorna stats `{enviados, falhas, pendentes, ignorados}`.
    Marca/cria registros em `comemorativos` com `mensagem_enviada=1` pra deduplicar.
    """
    today = today or date.today()
    stats = {"enviados": 0, "falhas": 0, "pendentes": 0, "ignorados": 0}

    clientes = session.exec(
        select(Cliente).where(Cliente.status == StatusCliente.ativo)
    ).all()

    for c in clientes:
        # ----- aniversário -----
        if c.data_nascimento and (
            c.data_nascimento.month == today.month
            and c.data_nascimento.day == today.day
        ):
            if not _ja_enviado_hoje(
                session, c.id, TipoComemorativo.aniversario, today
            ):
                vars_ = derive_cliente_vars(c, today=today)
                msg = render(template_aniversario, vars_)
                envio = sender.send_text(session, c, msg,
                                         modulo=Modulo.comemorativo)
                _registrar_comemorativo(
                    session, c.id, TipoComemorativo.aniversario, today,
                    enviado=envio.status == StatusEnvio.enviado,
                )
                _bump(stats, envio.status)
            else:
                stats["ignorados"] += 1

        # ----- marcos parceria -----
        if c.data_inicio_parceria:
            dias = (today - c.data_inicio_parceria).days
            tipo = MARCOS_PARCERIA.get(dias)
            if tipo and not _ja_enviado_hoje(session, c.id, tipo, today):
                vars_ = derive_cliente_vars(c, today=today, extras={
                    "dias_parceria": dias,
                })
                msg = render(template_marco, vars_)
                envio = sender.send_text(session, c, msg,
                                         modulo=Modulo.comemorativo)
                _registrar_comemorativo(session, c.id, tipo, today,
                                        dias_parceria=dias,
                                        enviado=envio.status == StatusEnvio.enviado)
                _bump(stats, envio.status)

    logger.info("dispatch_comemorativo {} → {}", today, stats)
    return stats


def _ja_enviado_hoje(
    session: Session,
    cliente_id: int,
    tipo: TipoComemorativo,
    today: date,
) -> bool:
    existing = session.exec(
        select(Comemorativo).where(
            Comemorativo.cliente_id == cliente_id,
            Comemorativo.tipo == tipo,
            Comemorativo.data_gatilho == today,
        )
    ).first()
    return bool(existing and existing.mensagem_enviada)


def _registrar_comemorativo(
    session: Session,
    cliente_id: int,
    tipo: TipoComemorativo,
    today: date,
    *,
    dias_parceria: Optional[int] = None,
    enviado: bool,
) -> None:
    existing = session.exec(
        select(Comemorativo).where(
            Comemorativo.cliente_id == cliente_id,
            Comemorativo.tipo == tipo,
            Comemorativo.data_gatilho == today,
        )
    ).first()
    if existing:
        existing.mensagem_enviada = existing.mensagem_enviada or enviado
        existing.atualizado_em = datetime.now()
        session.add(existing)
    else:
        session.add(Comemorativo(
            cliente_id=cliente_id,
            tipo=tipo,
            data_gatilho=today,
            dias_parceria=dias_parceria,
            mensagem_enviada=enviado,
        ))
    session.commit()


# ============================================================================
# Expiração de plano
# ============================================================================
def dispatch_expiracao(
    session: Session,
    sender: Sender,
    *,
    template_expiracao: str = (
        "Olá, {nome}! 👋\nSeu plano {plano} expira em {dias_restantes} dias.\n"
        "Renove com antecedência e ganhe bônus + desconto!"
    ),
    today: Optional[date] = None,
) -> dict[str, int]:
    """Para cada plano ativo, dispara mensagem nos gatilhos 30/15/7/3 dias.

    Marca a flag respectiva em `planos` pra não duplicar.
    """
    today = today or date.today()
    stats = {"enviados": 0, "falhas": 0, "pendentes": 0, "ignorados": 0}

    planos = session.exec(
        select(Plano).where(Plano.data_fim >= today)
    ).all()

    for plano in planos:
        dias_rest = (plano.data_fim - today).days
        if dias_rest not in EXPIRACAO_GATILHOS:
            continue

        flag = EXPIRACAO_FLAG[dias_rest]
        if getattr(plano, flag):
            stats["ignorados"] += 1
            continue

        cliente = session.get(Cliente, plano.cliente_id)
        if not cliente or cliente.status != StatusCliente.ativo:
            stats["ignorados"] += 1
            continue

        vars_ = derive_cliente_vars(cliente, today=today, extras={
            "dias_restantes": dias_rest,
            "data_expiracao": plano.data_fim.strftime("%d/%m/%Y"),
            "plano": plano.nome_plano,
        })
        msg = render(template_expiracao, vars_)
        envio = sender.send_text(session, cliente, msg,
                                 modulo=Modulo.expiracao)

        if envio.status == StatusEnvio.enviado:
            setattr(plano, flag, True)
            plano.dias_restantes = dias_rest
            plano.atualizado_em = datetime.now()
            session.add(plano)
            session.commit()
        _bump(stats, envio.status)

    logger.info("dispatch_expiracao {} → {}", today, stats)
    return stats


def _bump(stats: dict[str, int], status: StatusEnvio) -> None:
    if status == StatusEnvio.enviado:
        stats["enviados"] += 1
    elif status == StatusEnvio.falha:
        stats["falhas"] += 1
    elif status == StatusEnvio.pendente:
        stats["pendentes"] += 1


# ============================================================================
# Pós-Venda — 3 etapas baseado em data_compra
# ============================================================================
POS_VENDA_ETAPAS: list[tuple[int, str, str]] = [
    # (dias_apos_compra, tipo_gatilho, fallback_template)
    (0, "imediato", (
        "Obrigado pela compra, {nome}! 🛒\n"
        "Qualquer dúvida, estamos por aqui."
    )),
    (2, "questionamento_48h", (
        "Oi, {nome}! Como está sendo sua experiência? 😊\n"
        "Teve alguma dificuldade? Sua opinião conta."
    )),
    (7, "sugestoes_7d", (
        "Olá {nome}! Passando aqui com algumas dicas pra você 🚀\n"
        "Qualquer dúvida, é só responder."
    )),
]


def dispatch_pos_venda(
    session: Session,
    sender: Sender,
    *,
    today: Optional[date] = None,
) -> dict[str, int]:
    """Para cada Evento tipo=pos_venda com data_compra, dispara as etapas devidas hoje.

    Dedup por (cliente_id, template_id) na tabela `envios` — não duplica.
    Etapas usam templates do banco (modulo=pos_venda, tipo_gatilho match),
    com fallback hardcoded se template não existir/ativo.
    """
    today = today or date.today()
    stats = {"enviados": 0, "falhas": 0, "pendentes": 0, "ignorados": 0}

    pos_eventos = session.exec(
        select(Evento).where(
            Evento.tipo_evento == TipoEvento.pos_venda,
            Evento.data_compra.is_not(None),  # type: ignore[union-attr]
        )
    ).all()

    for ev in pos_eventos:
        if not ev.data_compra:
            continue
        dias = (today - ev.data_compra).days
        if dias < 0:
            continue
        cliente = session.get(Cliente, ev.cliente_id)
        if not cliente or cliente.status != StatusCliente.ativo:
            stats["ignorados"] += 1
            continue

        for etapa_dias, tipo_gatilho, fallback in POS_VENDA_ETAPAS:
            if dias != etapa_dias:
                continue
            template = _find_template(session, Modulo.pos_venda, tipo_gatilho)
            template_id = template.id if template else None
            if _ja_enviado_template(session, ev.cliente_id, template_id, fallback):
                stats["ignorados"] += 1
                continue
            texto = template.mensagem_texto if template else fallback
            vars_ = derive_cliente_vars(cliente, today=today, extras={
                "produto": ev.nome_evento or "produto",
                "data_compra": ev.data_compra.strftime("%d/%m/%Y"),
            })
            msg = render(texto, vars_)
            envio = sender.send_text(session, cliente, msg,
                                     modulo=Modulo.pos_venda,
                                     template_id=template_id)
            _bump(stats, envio.status)

    logger.info("dispatch_pos_venda {} → {}", today, stats)
    return stats


# ============================================================================
# Evento — véspera (D-1) + pós (D+1) baseado em data_evento
# ============================================================================
EVENTO_ETAPAS: list[tuple[int, str, str, str]] = [
    # (delta_dias_vs_hoje, tipo_gatilho, flag_evento, fallback)
    (1,  "vespera",  "vespera_mensagem_enviada", (
        "Oi {nome}! Amanhã é o evento {nome_evento}! 🎉\n"
        "Chegue 15 min antes. Te esperamos!"
    )),
    (-1, "pos",      "pos_mensagem_enviada", (
        "Obrigado pelo comparecimento no {nome_evento}, {nome}! 🙏\n"
        "Foi incrível ter você lá."
    )),
]


def dispatch_evento(
    session: Session,
    sender: Sender,
    *,
    today: Optional[date] = None,
) -> dict[str, int]:
    """Para Eventos tipo=evento: véspera (data_evento == hoje+1) e pós (data_evento == hoje-1).

    Dedup pelas flags `vespera_mensagem_enviada` e `pos_mensagem_enviada` da tabela Evento.
    """
    today = today or date.today()
    stats = {"enviados": 0, "falhas": 0, "pendentes": 0, "ignorados": 0}

    evs = session.exec(
        select(Evento).where(Evento.tipo_evento == TipoEvento.evento)
    ).all()

    for ev in evs:
        cliente = session.get(Cliente, ev.cliente_id)
        if not cliente or cliente.status != StatusCliente.ativo:
            stats["ignorados"] += 1
            continue

        delta = (ev.data_evento - today).days

        for etapa_delta, tipo_gatilho, flag, fallback in EVENTO_ETAPAS:
            if delta != etapa_delta:
                continue
            if getattr(ev, flag):
                stats["ignorados"] += 1
                continue
            template = _find_template(session, Modulo.evento, tipo_gatilho)
            template_id = template.id if template else None
            texto = template.mensagem_texto if template else fallback
            vars_ = derive_cliente_vars(cliente, today=today, extras={
                "nome_evento": ev.nome_evento,
                "data_evento": ev.data_evento.strftime("%d/%m/%Y"),
            })
            msg = render(texto, vars_)
            envio = sender.send_text(session, cliente, msg,
                                     modulo=Modulo.evento,
                                     template_id=template_id)
            if envio.status == StatusEnvio.enviado:
                setattr(ev, flag, True)
                ev.atualizado_em = datetime.now()
                session.add(ev)
                session.commit()
            _bump(stats, envio.status)

    logger.info("dispatch_evento {} → {}", today, stats)
    return stats


# ============================================================================
# Helpers compartilhados
# ============================================================================
def _find_template(
    session: Session,
    modulo: Modulo,
    tipo_gatilho: str,
) -> Optional[Template]:
    """Busca template ativo por (modulo, tipo_gatilho). Devolve None se não achar."""
    return session.exec(
        select(Template).where(
            Template.modulo == modulo,
            Template.tipo_gatilho == tipo_gatilho,
            Template.ativo == True,  # noqa: E712 (SQLModel field)
        )
    ).first()


def _ja_enviado_template(
    session: Session,
    cliente_id: int,
    template_id: Optional[int],
    fallback_text: str,
) -> bool:
    """Verifica se já há envio com status enviado/bloqueado pra esse cliente+template.

    Quando template_id é None (fallback hardcoded), procura um chunk estável do
    fallback (sem placeholders) usando LIKE — sobrevive ao render do {nome}.
    """
    if template_id is not None:
        existing = session.exec(
            select(Envio).where(
                Envio.cliente_id == cliente_id,
                Envio.template_id == template_id,
                Envio.status.in_(  # type: ignore[union-attr]
                    [StatusEnvio.enviado, StatusEnvio.bloqueado]
                ),
            )
        ).first()
        return existing is not None

    chunk = _stable_chunk(fallback_text)
    if not chunk:
        return False
    existing = session.exec(
        select(Envio).where(
            Envio.cliente_id == cliente_id,
            Envio.mensagem_texto.like(f"%{chunk}%"),  # type: ignore[union-attr]
            Envio.status.in_(  # type: ignore[union-attr]
                [StatusEnvio.enviado, StatusEnvio.bloqueado]
            ),
        )
    ).first()
    return existing is not None


def _stable_chunk(text: str, min_len: int = 15, max_len: int = 60) -> str:
    """Extrai a maior substring contígua sem `{placeholders}` do texto.

    Usado pra dedup quando não há template_id: o chunk sobrevive ao render.
    """
    import re
    parts = [p.strip() for p in re.split(r"\{[^}]*\}", text)]
    # pega o maior pedaço que sobreviveu, limitado a max_len
    best = max(parts, key=len, default="")
    if len(best) < min_len:
        return ""
    return best[:max_len]
