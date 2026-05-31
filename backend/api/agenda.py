"""Agenda — disparos previstos numa janela de datas.

Não dispara nada. Apenas computa o que ACONTECERIA se os jobs rodassem
a cada dia da janela. Já filtra os que viram que ainda não foram enviados
(usando as mesmas flags/registros dos dispatchers reais).
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from backend.api.deps import get_session
from backend.jobs import (
    EXPIRACAO_FLAG, EXPIRACAO_GATILHOS,
    EVENTO_ETAPAS, MARCOS_PARCERIA, POS_VENDA_ETAPAS,
)
from backend.models import (
    Cliente, Comemorativo, Envio, Evento, Plano,
    StatusCliente, StatusEnvio, TipoComemorativo, TipoEvento,
)


router = APIRouter(prefix="/agenda", tags=["agenda"])


@router.get("")
def agenda(
    from_: date = Query(..., alias="from"),
    to: date = Query(..., alias="to"),
    session: Session = Depends(get_session),
) -> list[dict]:
    """Lista itens (date, modulo, cliente_id, cliente_nome, titulo, ja_processado).

    `ja_processado=True` significa que o item já tem registro de envio
    bem-sucedido — mostra na agenda mas marcado como "concluído".
    """
    if to < from_:
        return []

    items: list[dict] = []
    clientes = session.exec(
        select(Cliente).where(Cliente.status == StatusCliente.ativo)
    ).all()
    cliente_by_id = {c.id: c for c in clientes}

    # ----- comemorativo: aniversário + marcos parceria -----
    for c in clientes:
        if c.data_nascimento:
            for d in _iter_days(from_, to):
                if (c.data_nascimento.month == d.month
                        and c.data_nascimento.day == d.day):
                    items.append(_item(
                        d, "comemorativo", c,
                        f"Aniversário de {c.nome}",
                        ja_processado=_ja_proc_comemorativo(
                            session, c.id, TipoComemorativo.aniversario, d,
                        ),
                    ))
        if c.data_inicio_parceria:
            for d in _iter_days(from_, to):
                dias = (d - c.data_inicio_parceria).days
                tipo = MARCOS_PARCERIA.get(dias)
                if tipo:
                    items.append(_item(
                        d, "comemorativo", c,
                        f"{dias} dias de parceria — {c.nome}",
                        ja_processado=_ja_proc_comemorativo(session, c.id, tipo, d),
                    ))

    # ----- expiração: planos -----
    planos_ativos = session.exec(
        select(Plano).where(Plano.data_fim >= from_)
    ).all()
    for plano in planos_ativos:
        c = cliente_by_id.get(plano.cliente_id)
        if not c:
            continue
        for d in _iter_days(from_, to):
            dias_rest = (plano.data_fim - d).days
            if dias_rest not in EXPIRACAO_GATILHOS:
                continue
            flag_attr = EXPIRACAO_FLAG[dias_rest]
            ja = bool(getattr(plano, flag_attr))
            items.append(_item(
                d, "expiracao", c,
                f"Plano {plano.nome_plano} expira em {dias_rest}d ({c.nome})",
                ja_processado=ja,
            ))

    # ----- pós-venda: data_compra + 0/2/7 -----
    pos_eventos = session.exec(
        select(Evento).where(
            Evento.tipo_evento == TipoEvento.pos_venda,
            Evento.data_compra.is_not(None),  # type: ignore[union-attr]
        )
    ).all()
    for ev in pos_eventos:
        if not ev.data_compra:
            continue
        c = cliente_by_id.get(ev.cliente_id)
        if not c:
            continue
        for etapa_dias, tipo_gatilho, _ in POS_VENDA_ETAPAS:
            d = ev.data_compra + timedelta(days=etapa_dias)
            if not (from_ <= d <= to):
                continue
            ja = _ja_proc_pos_venda(session, ev.cliente_id, tipo_gatilho)
            items.append(_item(
                d, "pos_venda", c,
                f"{tipo_gatilho.replace('_', ' ')} — {ev.nome_evento} ({c.nome})",
                ja_processado=ja,
            ))

    # ----- evento: véspera (D-1) e pós (D+1) -----
    evs = session.exec(
        select(Evento).where(Evento.tipo_evento == TipoEvento.evento)
    ).all()
    for ev in evs:
        c = cliente_by_id.get(ev.cliente_id)
        if not c:
            continue
        for etapa_delta, tipo_gatilho, flag, _ in EVENTO_ETAPAS:
            d = ev.data_evento - timedelta(days=etapa_delta)
            if not (from_ <= d <= to):
                continue
            ja = bool(getattr(ev, flag))
            items.append(_item(
                d, "evento", c,
                f"{tipo_gatilho} — {ev.nome_evento} ({c.nome})",
                ja_processado=ja,
            ))

    items.sort(key=lambda it: (it["data"], it["modulo"], it["cliente_nome"]))
    return items


# ============================================================================
# Helpers
# ============================================================================
def _iter_days(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _item(d: date, modulo: str, cliente: Cliente,
          titulo: str, *, ja_processado: bool) -> dict:
    return {
        "data": d.isoformat(),
        "modulo": modulo,
        "cliente_id": cliente.id,
        "cliente_nome": cliente.nome,
        "telefone": cliente.telefone,
        "titulo": titulo,
        "ja_processado": ja_processado,
    }


def _ja_proc_comemorativo(
    session: Session, cliente_id: int,
    tipo: TipoComemorativo, d: date,
) -> bool:
    rec = session.exec(
        select(Comemorativo).where(
            Comemorativo.cliente_id == cliente_id,
            Comemorativo.tipo == tipo,
            Comemorativo.data_gatilho == d,
        )
    ).first()
    return bool(rec and rec.mensagem_enviada)


def _ja_proc_pos_venda(
    session: Session, cliente_id: int, tipo_gatilho: str,
) -> bool:
    """Heurística: existe envio enviado pós-venda pra esse cliente recente
    (últimos 30 dias) com texto contendo um trecho da etapa? Simplificação:
    apenas detecta existência de qualquer envio enviado pós-venda do cliente
    nos últimos 14 dias. Suficiente pra UI."""
    cutoff = date.today() - timedelta(days=14)
    existing = session.exec(
        select(Envio).where(
            Envio.cliente_id == cliente_id,
            Envio.modulo == "pos_venda",
            Envio.status == StatusEnvio.enviado,
            Envio.criado_em >= cutoff,
        )
    ).first()
    return existing is not None
