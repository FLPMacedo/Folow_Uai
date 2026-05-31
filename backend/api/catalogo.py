"""CRUD de Planos & Serviços e Grupos — catálogos do negócio."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from backend.api.deps import get_session
from backend.api.schemas import (
    GrupoCreate, GrupoUpdate,
    PlanoServicoCreate, PlanoServicoUpdate,
)
from backend.models import Grupo, PlanoServico


# ============================================================================
# Planos & Serviços
# ============================================================================
planos_router = APIRouter(prefix="/planos-servicos", tags=["planos-servicos"])


@planos_router.post("", response_model=PlanoServico, status_code=201)
def create_plano(
    payload: PlanoServicoCreate,
    session: Session = Depends(get_session),
) -> PlanoServico:
    if session.exec(select(PlanoServico).where(PlanoServico.nome == payload.nome)).first():
        raise HTTPException(409, f"Já existe plano com nome '{payload.nome}'")
    p = PlanoServico.model_validate(payload.model_dump())
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


@planos_router.get("", response_model=list[PlanoServico])
def list_planos(
    ativo: Optional[bool] = None,
    session: Session = Depends(get_session),
) -> list[PlanoServico]:
    stmt = select(PlanoServico)
    if ativo is not None:
        stmt = stmt.where(PlanoServico.ativo == ativo)
    stmt = stmt.order_by(PlanoServico.nome)
    return list(session.exec(stmt).all())


@planos_router.get("/{plano_id}", response_model=PlanoServico)
def get_plano(plano_id: int, session: Session = Depends(get_session)) -> PlanoServico:
    p = session.get(PlanoServico, plano_id)
    if not p:
        raise HTTPException(404, "Plano não encontrado")
    return p


@planos_router.put("/{plano_id}", response_model=PlanoServico)
def update_plano(
    plano_id: int,
    payload: PlanoServicoUpdate,
    session: Session = Depends(get_session),
) -> PlanoServico:
    p = session.get(PlanoServico, plano_id)
    if not p:
        raise HTTPException(404, "Plano não encontrado")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    p.atualizado_em = datetime.now()
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


@planos_router.delete("/{plano_id}", status_code=204, response_class=Response)
def delete_plano(plano_id: int, session: Session = Depends(get_session)) -> Response:
    p = session.get(PlanoServico, plano_id)
    if not p:
        raise HTTPException(404, "Plano não encontrado")
    session.delete(p)
    session.commit()
    return Response(status_code=204)


# ============================================================================
# Grupos
# ============================================================================
grupos_router = APIRouter(prefix="/grupos", tags=["grupos"])


@grupos_router.post("", response_model=Grupo, status_code=201)
def create_grupo(
    payload: GrupoCreate,
    session: Session = Depends(get_session),
) -> Grupo:
    if session.exec(select(Grupo).where(Grupo.nome == payload.nome)).first():
        raise HTTPException(409, f"Já existe grupo com nome '{payload.nome}'")
    g = Grupo.model_validate(payload.model_dump())
    session.add(g)
    session.commit()
    session.refresh(g)
    return g


@grupos_router.get("", response_model=list[Grupo])
def list_grupos(
    ativo: Optional[bool] = None,
    session: Session = Depends(get_session),
) -> list[Grupo]:
    stmt = select(Grupo)
    if ativo is not None:
        stmt = stmt.where(Grupo.ativo == ativo)
    stmt = stmt.order_by(Grupo.nome)
    return list(session.exec(stmt).all())


@grupos_router.get("/{grupo_id}", response_model=Grupo)
def get_grupo(grupo_id: int, session: Session = Depends(get_session)) -> Grupo:
    g = session.get(Grupo, grupo_id)
    if not g:
        raise HTTPException(404, "Grupo não encontrado")
    return g


@grupos_router.put("/{grupo_id}", response_model=Grupo)
def update_grupo(
    grupo_id: int,
    payload: GrupoUpdate,
    session: Session = Depends(get_session),
) -> Grupo:
    g = session.get(Grupo, grupo_id)
    if not g:
        raise HTTPException(404, "Grupo não encontrado")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(g, k, v)
    g.atualizado_em = datetime.now()
    session.add(g)
    session.commit()
    session.refresh(g)
    return g


@grupos_router.delete("/{grupo_id}", status_code=204, response_class=Response)
def delete_grupo(grupo_id: int, session: Session = Depends(get_session)) -> Response:
    g = session.get(Grupo, grupo_id)
    if not g:
        raise HTTPException(404, "Grupo não encontrado")
    session.delete(g)
    session.commit()
    return Response(status_code=204)
