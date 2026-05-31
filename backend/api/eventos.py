"""CRUD de Eventos — pós-venda (compras) + eventos agendados."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select

from backend.api.deps import get_session
from backend.api.schemas import EventoCreate, EventoUpdate
from backend.models import Cliente, Evento, TipoEvento


router = APIRouter(prefix="/eventos", tags=["eventos"])


@router.post("", response_model=Evento, status_code=201)
def create_evento(
    payload: EventoCreate,
    session: Session = Depends(get_session),
) -> Evento:
    cliente = session.get(Cliente, payload.cliente_id)
    if not cliente:
        raise HTTPException(400, f"Cliente {payload.cliente_id} não encontrado")
    ev = Evento.model_validate(payload.model_dump())
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


@router.get("", response_model=list[Evento])
def list_eventos(
    cliente_id: Optional[int] = None,
    tipo_evento: Optional[TipoEvento] = None,
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> list[Evento]:
    stmt = select(Evento)
    if cliente_id is not None:
        stmt = stmt.where(Evento.cliente_id == cliente_id)
    if tipo_evento is not None:
        stmt = stmt.where(Evento.tipo_evento == tipo_evento)
    stmt = stmt.order_by(Evento.data_evento.desc()).offset(offset).limit(limit)
    return list(session.exec(stmt).all())


@router.get("/{evento_id}", response_model=Evento)
def get_evento(evento_id: int, session: Session = Depends(get_session)) -> Evento:
    ev = session.get(Evento, evento_id)
    if not ev:
        raise HTTPException(404, "Evento não encontrado")
    return ev


@router.put("/{evento_id}", response_model=Evento)
def update_evento(
    evento_id: int,
    payload: EventoUpdate,
    session: Session = Depends(get_session),
) -> Evento:
    ev = session.get(Evento, evento_id)
    if not ev:
        raise HTTPException(404, "Evento não encontrado")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(ev, k, v)
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


@router.delete("/{evento_id}", status_code=204, response_class=Response)
def delete_evento(evento_id: int, session: Session = Depends(get_session)) -> Response:
    ev = session.get(Evento, evento_id)
    if not ev:
        raise HTTPException(404, "Evento não encontrado")
    session.delete(ev)
    session.commit()
    return Response(status_code=204)
