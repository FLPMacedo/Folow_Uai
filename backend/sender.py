"""Camada de envio com rotação multi-número + intervalo anti-banimento.

Decide qual TelefoneWhatsApp usar (rotação por `ultimo_envio` mais antigo),
respeita intervalo mínimo, dispara via EvolutionClient, persiste Envio.

Se nenhum telefone disponível no momento (todos enviaram <intervalo atrás),
o Envio é criado com status `pendente` — próximo tick do scheduler pega.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Protocol

from loguru import logger
from sqlmodel import Session, select

from backend.config import settings
from backend.models import (
    Cliente,
    Envio,
    Modulo,
    StatusEnvio,
    StatusTelefone,
    TelefoneWhatsApp,
)


class WhatsAppGateway(Protocol):
    """Subset da Evolution usado pelo Sender (facilita mock no teste)."""

    def send_text(
        self, instance: str, number: str, text: str, *, delay_ms: int = 0,
        link_preview: bool = False,
    ) -> dict: ...

    def send_media(
        self, instance: str, number: str, media_path, *,
        caption: str = "", mediatype: Optional[str] = None, delay_ms: int = 0,
    ) -> dict: ...


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class Sender:
    """Despacha mensagens respeitando rotação + intervalo anti-banimento."""

    def __init__(
        self,
        gateway: WhatsAppGateway,
        *,
        intervalo_min: Optional[int] = None,
    ) -> None:
        self.gateway = gateway
        self.intervalo_min = (
            intervalo_min
            if intervalo_min is not None
            else settings.INTERVALO_MIN_ENVIO_MINUTOS
        )

    # ---- escolha de número ----
    def pick_telefone(
        self,
        session: Session,
        *,
        now: Optional[datetime] = None,
    ) -> Optional[TelefoneWhatsApp]:
        """Devolve telefone ativo com `ultimo_envio` mais antigo respeitando
        intervalo mínimo, ou None se todos estão em cooldown."""
        now = now or _utcnow()
        cutoff = now - timedelta(minutes=self.intervalo_min)

        ativos = session.exec(
            select(TelefoneWhatsApp)
            .where(TelefoneWhatsApp.status == StatusTelefone.ativo)
        ).all()
        if not ativos:
            return None

        # disponíveis: nunca enviou OU enviou antes do cutoff
        disponiveis = [
            t for t in ativos
            if t.ultimo_envio is None or _ensure_aware(t.ultimo_envio) <= cutoff
        ]
        if not disponiveis:
            return None

        # rotação: ordena por (ultimo_envio asc), NULL primeiro, depois total_envios asc
        disponiveis.sort(key=lambda t: (
            _ensure_aware(t.ultimo_envio) or datetime.min.replace(tzinfo=timezone.utc),
            t.total_envios,
        ))
        return disponiveis[0]

    # ---- envio ----
    def send_text(
        self,
        session: Session,
        cliente: Cliente,
        mensagem: str,
        *,
        modulo: Modulo,
        template_id: Optional[int] = None,
        campanha_id: Optional[int] = None,
        now: Optional[datetime] = None,
    ) -> Envio:
        now = now or _utcnow()
        envio = Envio(
            cliente_id=cliente.id,
            template_id=template_id,
            campanha_id=campanha_id,
            modulo=modulo,
            telefone_destino=cliente.telefone,
            mensagem_texto=mensagem,
            status=StatusEnvio.pendente,
        )
        tel = self.pick_telefone(session, now=now)
        if tel is None:
            session.add(envio)
            session.commit()
            session.refresh(envio)
            logger.info("Envio {} adiado: sem telefone disponível", envio.id)
            return envio

        envio.telefone_whatsapp_id = tel.id
        try:
            resp = self.gateway.send_text(
                tel.instancia_evolution, cliente.telefone, mensagem,
            )
        except Exception as e:  # noqa: BLE001
            envio.status = StatusEnvio.falha
            envio.erro = f"{type(e).__name__}: {e}"[:500]
            logger.warning("Envio falhou cliente={} tel={}: {}",
                           cliente.id, tel.id, envio.erro)
        else:
            envio.status = StatusEnvio.enviado
            envio.enviado_em = now
            envio.mensagem_evolution_id = _extract_msg_id(resp)
            tel.ultimo_envio = now
            tel.total_envios = (tel.total_envios or 0) + 1
            tel.atualizado_em = now
            session.add(tel)
            logger.debug("Envio cliente={} via tel={} ok", cliente.id, tel.id)

        session.add(envio)
        session.commit()
        session.refresh(envio)
        return envio

    def send_media(
        self,
        session: Session,
        cliente: Cliente,
        mensagem: str,
        media_path: str | Path,
        *,
        modulo: Modulo,
        template_id: Optional[int] = None,
        campanha_id: Optional[int] = None,
        now: Optional[datetime] = None,
    ) -> Envio:
        now = now or _utcnow()
        envio = Envio(
            cliente_id=cliente.id,
            template_id=template_id,
            campanha_id=campanha_id,
            modulo=modulo,
            telefone_destino=cliente.telefone,
            mensagem_texto=mensagem,
            imagem_path=str(media_path),
            status=StatusEnvio.pendente,
        )
        tel = self.pick_telefone(session, now=now)
        if tel is None:
            session.add(envio)
            session.commit()
            session.refresh(envio)
            return envio

        envio.telefone_whatsapp_id = tel.id
        try:
            resp = self.gateway.send_media(
                tel.instancia_evolution, cliente.telefone, media_path,
                caption=mensagem,
            )
        except Exception as e:  # noqa: BLE001
            envio.status = StatusEnvio.falha
            envio.erro = f"{type(e).__name__}: {e}"[:500]
        else:
            envio.status = StatusEnvio.enviado
            envio.enviado_em = now
            envio.mensagem_evolution_id = _extract_msg_id(resp)
            tel.ultimo_envio = now
            tel.total_envios = (tel.total_envios or 0) + 1
            tel.atualizado_em = now
            session.add(tel)

        session.add(envio)
        session.commit()
        session.refresh(envio)
        return envio


def _extract_msg_id(resp: dict) -> Optional[str]:
    """Tolera schemas variantes da Evolution: {key:{id}} ou {messageId} ou {id}."""
    if not isinstance(resp, dict):
        return None
    key = resp.get("key")
    if isinstance(key, dict) and "id" in key:
        return str(key["id"])
    for k in ("messageId", "id"):
        if k in resp:
            return str(resp[k])
    return None
