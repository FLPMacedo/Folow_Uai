"""CRUD de Negócios (multi-empresa).

Apenas 1 negócio pode ter `is_default=true`. Toggling automático: ao salvar
um novo default, os outros são rebaixados.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select

from backend.api.deps import get_session
from backend.api.schemas import NegocioCreate, NegocioUpdate
from backend.models import Negocio


router = APIRouter(prefix="/negocios", tags=["negocios"])


def _clear_other_defaults(session: Session, except_id: Optional[int]) -> None:
    others = session.exec(
        select(Negocio).where(Negocio.is_default == True)  # noqa: E712
    ).all()
    for n in others:
        if n.id != except_id and n.is_default:
            n.is_default = False
            n.atualizado_em = datetime.now()
            session.add(n)


@router.post("", response_model=Negocio, status_code=201)
def create_negocio(
    payload: NegocioCreate,
    session: Session = Depends(get_session),
) -> Negocio:
    neg = Negocio.model_validate(payload.model_dump())
    if neg.is_default:
        _clear_other_defaults(session, except_id=None)
    session.add(neg)
    session.commit()
    session.refresh(neg)
    return neg


@router.get("", response_model=list[Negocio])
def list_negocios(
    ativo: Optional[bool] = None,
    session: Session = Depends(get_session),
) -> list[Negocio]:
    stmt = select(Negocio)
    if ativo is not None:
        stmt = stmt.where(Negocio.ativo == ativo)
    stmt = stmt.order_by(Negocio.is_default.desc(), Negocio.nome)
    return list(session.exec(stmt).all())


@router.get("/default", response_model=Optional[Negocio])
def get_default(session: Session = Depends(get_session)) -> Optional[Negocio]:
    """Retorna o negócio default, ou o primeiro ativo, ou None."""
    return get_default_negocio(session)


def get_default_negocio(session: Session) -> Optional[Negocio]:
    """Util importável por jobs.py."""
    default = session.exec(
        select(Negocio).where(
            Negocio.is_default == True,  # noqa: E712
            Negocio.ativo == True,        # noqa: E712
        )
    ).first()
    if default:
        return default
    return session.exec(
        select(Negocio).where(Negocio.ativo == True)  # noqa: E712
        .order_by(Negocio.id)
    ).first()


@router.get("/{neg_id}", response_model=Negocio)
def get_negocio(neg_id: int, session: Session = Depends(get_session)) -> Negocio:
    n = session.get(Negocio, neg_id)
    if not n:
        raise HTTPException(404, "Negócio não encontrado")
    return n


@router.put("/{neg_id}", response_model=Negocio)
def update_negocio(
    neg_id: int,
    payload: NegocioUpdate,
    session: Session = Depends(get_session),
) -> Negocio:
    n = session.get(Negocio, neg_id)
    if not n:
        raise HTTPException(404, "Negócio não encontrado")
    data = payload.model_dump(exclude_unset=True)
    is_default_new = data.get("is_default")
    for k, v in data.items():
        setattr(n, k, v)
    n.atualizado_em = datetime.now()
    if is_default_new is True:
        _clear_other_defaults(session, except_id=n.id)
    session.add(n)
    session.commit()
    session.refresh(n)
    return n


@router.delete("/{neg_id}", status_code=204, response_class=Response)
def delete_negocio(neg_id: int, session: Session = Depends(get_session)) -> Response:
    n = session.get(Negocio, neg_id)
    if not n:
        raise HTTPException(404, "Negócio não encontrado")
    session.delete(n)
    session.commit()
    return Response(status_code=204)
