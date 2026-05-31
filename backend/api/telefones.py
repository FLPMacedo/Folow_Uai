"""CRUD telefones WhatsApp + integração Evolution (criar instância + QR)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from backend.api.deps import get_session
from backend.api.schemas import TelefoneCreate, TelefoneUpdate
from backend.models import TelefoneWhatsApp
from backend.whatsapp_client import (
    EvolutionClient,
    EvolutionConnectionError,
    EvolutionError,
)


router = APIRouter(prefix="/telefones", tags=["telefones"])


@router.post("", response_model=TelefoneWhatsApp, status_code=201)
def create_telefone(
    payload: TelefoneCreate,
    session: Session = Depends(get_session),
) -> TelefoneWhatsApp:
    tel = TelefoneWhatsApp.model_validate(payload.model_dump())
    session.add(tel)
    session.commit()
    session.refresh(tel)
    return tel


@router.get("", response_model=list[TelefoneWhatsApp])
def list_telefones(session: Session = Depends(get_session)) -> list[TelefoneWhatsApp]:
    return list(session.exec(select(TelefoneWhatsApp)).all())


@router.get("/{tel_id}", response_model=TelefoneWhatsApp)
def get_telefone(tel_id: int, session: Session = Depends(get_session)) -> TelefoneWhatsApp:
    tel = session.get(TelefoneWhatsApp, tel_id)
    if not tel:
        raise HTTPException(404, "Telefone não encontrado")
    return tel


@router.put("/{tel_id}", response_model=TelefoneWhatsApp)
def update_telefone(
    tel_id: int,
    payload: TelefoneUpdate,
    session: Session = Depends(get_session),
) -> TelefoneWhatsApp:
    tel = session.get(TelefoneWhatsApp, tel_id)
    if not tel:
        raise HTTPException(404, "Telefone não encontrado")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(tel, k, v)
    session.add(tel)
    session.commit()
    session.refresh(tel)
    return tel


@router.delete("/{tel_id}", status_code=204, response_class=Response)
def delete_telefone(tel_id: int, session: Session = Depends(get_session)) -> Response:
    tel = session.get(TelefoneWhatsApp, tel_id)
    if not tel:
        raise HTTPException(404, "Telefone não encontrado")
    session.delete(tel)
    session.commit()
    return Response(status_code=204)


# ============================================================================
# Evolution integration
# ============================================================================
@router.post("/{tel_id}/create-instance")
def create_instance(tel_id: int, session: Session = Depends(get_session)) -> dict:
    """Cria instância na Evolution e devolve QR code para parear."""
    tel = session.get(TelefoneWhatsApp, tel_id)
    if not tel:
        raise HTTPException(404, "Telefone não encontrado")
    try:
        with EvolutionClient() as ev:
            out = ev.create_instance(tel.instancia_evolution)
    except EvolutionConnectionError as e:
        raise HTTPException(503, f"Evolution offline: {e}") from e
    except EvolutionError as e:
        raise HTTPException(502, f"Evolution: {e}") from e
    return out


@router.get("/{tel_id}/state")
def state(tel_id: int, session: Session = Depends(get_session)) -> dict:
    tel = session.get(TelefoneWhatsApp, tel_id)
    if not tel:
        raise HTTPException(404, "Telefone não encontrado")
    try:
        with EvolutionClient() as ev:
            return ev.connection_state(tel.instancia_evolution)
    except EvolutionConnectionError as e:
        raise HTTPException(503, f"Evolution offline: {e}") from e
    except EvolutionError as e:
        raise HTTPException(502, f"Evolution: {e}") from e
