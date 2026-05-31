"""Consulta de envios + relatórios."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlmodel import Session, select

from backend.api.deps import get_session
from backend.api.schemas import ModuloStats
from backend.models import Envio, Modulo, StatusEnvio


router = APIRouter(prefix="/envios", tags=["envios"])


@router.get("", response_model=list[Envio])
def list_envios(
    modulo: Optional[Modulo] = None,
    status: Optional[StatusEnvio] = None,
    cliente_id: Optional[int] = None,
    since: Optional[datetime] = None,
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> list[Envio]:
    stmt = select(Envio)
    if modulo:
        stmt = stmt.where(Envio.modulo == modulo)
    if status:
        stmt = stmt.where(Envio.status == status)
    if cliente_id:
        stmt = stmt.where(Envio.cliente_id == cliente_id)
    if since:
        stmt = stmt.where(Envio.criado_em >= since)
    stmt = stmt.order_by(Envio.criado_em.desc()).offset(offset).limit(limit)
    return list(session.exec(stmt).all())


@router.get("/stats", response_model=list[ModuloStats])
def stats(session: Session = Depends(get_session)) -> list[ModuloStats]:
    """Agregado por módulo via view `v_envios_por_modulo`."""
    rows = session.exec(text(
        "SELECT modulo, total_envios, enviados, falhas, bloqueados, pendentes "
        "FROM v_envios_por_modulo"
    )).all()
    return [
        ModuloStats(
            modulo=r[0], total_envios=r[1], enviados=r[2],
            falhas=r[3], bloqueados=r[4], pendentes=r[5],
        )
        for r in rows
    ]
