"""CRUD templates de mensagem."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select

from backend.api.deps import get_session
from backend.api.schemas import TemplateCreate, TemplateUpdate
from backend.models import Modulo, Template


router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("", response_model=Template, status_code=201)
def create_template(
    payload: TemplateCreate,
    session: Session = Depends(get_session),
) -> Template:
    tmpl = Template.model_validate(payload.model_dump())
    session.add(tmpl)
    session.commit()
    session.refresh(tmpl)
    return tmpl


@router.get("", response_model=list[Template])
def list_templates(
    modulo: Optional[Modulo] = None,
    ativo: Optional[bool] = None,
    session: Session = Depends(get_session),
) -> list[Template]:
    stmt = select(Template)
    if modulo:
        stmt = stmt.where(Template.modulo == modulo)
    if ativo is not None:
        stmt = stmt.where(Template.ativo == ativo)
    return list(session.exec(stmt).all())


@router.get("/{tmpl_id}", response_model=Template)
def get_template(tmpl_id: int, session: Session = Depends(get_session)) -> Template:
    tmpl = session.get(Template, tmpl_id)
    if not tmpl:
        raise HTTPException(404, "Template não encontrado")
    return tmpl


@router.put("/{tmpl_id}", response_model=Template)
def update_template(
    tmpl_id: int,
    payload: TemplateUpdate,
    session: Session = Depends(get_session),
) -> Template:
    tmpl = session.get(Template, tmpl_id)
    if not tmpl:
        raise HTTPException(404, "Template não encontrado")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(tmpl, k, v)
    session.add(tmpl)
    session.commit()
    session.refresh(tmpl)
    return tmpl


@router.delete("/{tmpl_id}", status_code=204, response_class=Response)
def delete_template(tmpl_id: int, session: Session = Depends(get_session)) -> Response:
    tmpl = session.get(Template, tmpl_id)
    if not tmpl:
        raise HTTPException(404, "Template não encontrado")
    session.delete(tmpl)
    session.commit()
    return Response(status_code=204)
