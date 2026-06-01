"""Consultar respostas recebidas (a gravação já é via webhook)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select

from backend.api.deps import get_session
from backend.models import Cliente, Resposta


router = APIRouter(prefix="/respostas", tags=["respostas"])


def _serialize(session: Session, r: Resposta) -> dict:
    c = session.get(Cliente, r.cliente_id) if r.cliente_id else None
    return {
        "id": r.id,
        "cliente_id": r.cliente_id,
        "cliente_nome": c.nome if c else None,
        "telefone_origem": r.telefone_origem,
        "telefone_destino": r.telefone_destino,
        "mensagem_texto": r.mensagem_texto,
        "tipo_mensagem": r.tipo_mensagem,
        "mensagem_evolution_id": r.mensagem_evolution_id,
        "processado": r.processado,
        "recebido_em": r.recebido_em.isoformat() if r.recebido_em else None,
        "criado_em": r.criado_em.isoformat() if r.criado_em else None,
    }


@router.get("")
def list_respostas(
    cliente_id: Optional[int] = None,
    processado: Optional[bool] = None,
    q: Optional[str] = Query(None, description="busca no texto da mensagem"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> list[dict]:
    stmt = select(Resposta)
    if cliente_id is not None:
        stmt = stmt.where(Resposta.cliente_id == cliente_id)
    if processado is not None:
        stmt = stmt.where(Resposta.processado == processado)
    if q:
        stmt = stmt.where(Resposta.mensagem_texto.like(f"%{q}%"))  # type: ignore[union-attr]
    stmt = stmt.order_by(Resposta.recebido_em.desc()).offset(offset).limit(limit)
    rows = session.exec(stmt).all()
    return [_serialize(session, r) for r in rows]


@router.get("/stats")
def stats(session: Session = Depends(get_session)) -> dict:
    total = len(session.exec(select(Resposta)).all())
    nao_lidas = len(session.exec(
        select(Resposta).where(Resposta.processado == False)  # noqa: E712
    ).all())
    return {"total": total, "nao_lidas": nao_lidas}


@router.post("/{resp_id}/marcar-lida")
def marcar_lida(
    resp_id: int, session: Session = Depends(get_session),
) -> dict:
    r = session.get(Resposta, resp_id)
    if not r:
        raise HTTPException(404, "Resposta não encontrada")
    r.processado = True
    session.add(r)
    session.commit()
    return {"ok": True, "resposta_id": r.id, "processado": True}


@router.post("/{resp_id}/marcar-nao-lida")
def marcar_nao_lida(
    resp_id: int, session: Session = Depends(get_session),
) -> dict:
    r = session.get(Resposta, resp_id)
    if not r:
        raise HTTPException(404, "Resposta não encontrada")
    r.processado = False
    session.add(r)
    session.commit()
    return {"ok": True, "resposta_id": r.id, "processado": False}


@router.delete("/{resp_id}", status_code=204, response_class=Response)
def delete_resposta(
    resp_id: int, session: Session = Depends(get_session),
) -> Response:
    r = session.get(Resposta, resp_id)
    if not r:
        raise HTTPException(404, "Resposta não encontrada")
    session.delete(r)
    session.commit()
    return Response(status_code=204)
