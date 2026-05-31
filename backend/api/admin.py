"""Endpoints administrativos: backup + dispatch manual."""
from __future__ import annotations

from datetime import date as date_t
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from backend.api.deps import get_session
from backend.backup import create_backup, list_backups
from backend.jobs import (
    dispatch_comemorativo,
    dispatch_evento,
    dispatch_expiracao,
    dispatch_pos_venda,
)
from backend.models import Backup
from backend.sender import Sender
from backend.whatsapp_client import EvolutionClient


router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================================
# Backup
# ============================================================================
@router.post("/backup", response_model=Backup, status_code=201)
def backup_now(
    descricao: Optional[str] = None,
    session: Session = Depends(get_session),
) -> Backup:
    return create_backup(session, descricao=descricao)


@router.get("/backups", response_model=list[Backup])
def list_backup_history(session: Session = Depends(get_session)) -> list[Backup]:
    return list_backups(session)


# ============================================================================
# Dispatch manual (testar jobs sem esperar o cron)
# ============================================================================
@router.post("/dispatch/comemorativo")
def dispatch_comemorativo_now(
    today: Optional[date_t] = None,
    session: Session = Depends(get_session),
) -> dict[str, int]:
    with EvolutionClient() as gateway:
        sender = Sender(gateway)
        return dispatch_comemorativo(session, sender, today=today)


@router.post("/dispatch/expiracao")
def dispatch_expiracao_now(
    today: Optional[date_t] = None,
    session: Session = Depends(get_session),
) -> dict[str, int]:
    with EvolutionClient() as gateway:
        sender = Sender(gateway)
        return dispatch_expiracao(session, sender, today=today)


@router.post("/dispatch/pos_venda")
def dispatch_pos_venda_now(
    today: Optional[date_t] = None,
    session: Session = Depends(get_session),
) -> dict[str, int]:
    with EvolutionClient() as gateway:
        sender = Sender(gateway)
        return dispatch_pos_venda(session, sender, today=today)


@router.post("/dispatch/evento")
def dispatch_evento_now(
    today: Optional[date_t] = None,
    session: Session = Depends(get_session),
) -> dict[str, int]:
    with EvolutionClient() as gateway:
        sender = Sender(gateway)
        return dispatch_evento(session, sender, today=today)
