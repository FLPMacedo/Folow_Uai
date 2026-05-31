"""Webhook receptivo Evolution → persiste em `respostas`.

Configurar URL no Evolution (depois do MVP):
    POST {ENVIRONMENT_WEBHOOK_URL}/api/webhook/evolution
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from loguru import logger
from sqlmodel import Session, select

from backend.api.deps import get_session
from backend.models import Cliente, Resposta


router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/evolution", status_code=202)
async def receive(
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    """Aceita qualquer payload Evolution. Extrai best-effort campos da mensagem.

    Schema Evolution v2 varia — esse handler tolera ausências e loga raw em
    caso de schema novo. Devolve 202 sempre que parsear sem crash.
    """
    payload: dict[str, Any] = await request.json()
    logger.debug("Webhook recebido: {}", payload)

    msg = _extract_message(payload)
    if not msg:
        logger.warning("Webhook sem campo de mensagem identificável: {}", payload)
        return {"accepted": True, "stored": False, "reason": "no_message_field"}

    cliente_id = _find_cliente_by_phone(session, msg["from"])

    resp = Resposta(
        cliente_id=cliente_id,
        telefone_origem=msg["from"],
        telefone_destino=msg.get("to", ""),
        mensagem_texto=msg.get("text", ""),
        tipo_mensagem=msg.get("type", "text"),
        mensagem_evolution_id=msg.get("id"),
    )
    session.add(resp)
    session.commit()
    session.refresh(resp)
    return {"accepted": True, "stored": True, "resposta_id": resp.id}


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _extract_message(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Tolera schemas v2: {data: {key:{remoteJid,fromMe,id}, message:{conversation}}}.
    Também aceita formato achatado {from, text, type, id}.
    """
    if not isinstance(payload, dict):
        return None

    # formato achatado para testes
    if "from" in payload and "text" in payload:
        return payload

    data = payload.get("data") or payload
    if not isinstance(data, dict):
        return None

    key = data.get("key") or {}
    remote = key.get("remoteJid") or data.get("from")
    if not remote:
        return None

    # ignora mensagens que NÓS enviamos (fromMe=True)
    if key.get("fromMe") is True:
        return None

    # extrai texto: pode estar em data.message.conversation OU
    # data.message.extendedTextMessage.text OU data.text
    text = ""
    msg = data.get("message") or {}
    if isinstance(msg, dict):
        if "conversation" in msg:
            text = msg["conversation"] or ""
        elif "extendedTextMessage" in msg and isinstance(msg["extendedTextMessage"], dict):
            text = msg["extendedTextMessage"].get("text", "")
    if not text:
        text = data.get("text", "") or ""

    return {
        "from": _strip_jid(remote),
        "to": _strip_jid(payload.get("instance") or ""),
        "text": text,
        "type": data.get("messageType") or data.get("type") or "text",
        "id": key.get("id") or data.get("id"),
    }


def _strip_jid(value: str) -> str:
    """`5531999999999@s.whatsapp.net` → `5531999999999`."""
    if not value:
        return ""
    return value.split("@", 1)[0]


def _find_cliente_by_phone(session: Session, phone: str) -> int | None:
    if not phone:
        return None
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return None
    # tenta match exato com `+` removido
    rows = session.exec(select(Cliente)).all()
    for c in rows:
        c_digits = "".join(ch for ch in c.telefone if ch.isdigit())
        if c_digits == digits:
            return c.id
    return None
