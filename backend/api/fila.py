"""Fila de trabalho — operações sobre envios pendentes e falhados.

Conceito:
  - status `pendente`: ainda não enviado (em cooldown, sem telefone disponível, etc.)
  - status `falha`: tentou enviar e Evolution rejeitou
  - status `enviado`: sucesso (fora da fila)
  - status `bloqueado`: WhatsApp recusou (não deve retry)

Operações:
  * GET /fila               → lista pendentes + falhas com info do cliente
  * POST /fila/{id}/retry   → falha → pendente (limpa erro, scheduler ou manual reprocessa)
  * POST /fila/{id}/marcar-enviado → operador enviou de outro jeito
  * POST /fila/{id}/enviar-agora   → tenta dispatch via Sender já
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.api.deps import get_session
from backend.models import Cliente, Envio, StatusEnvio
from backend.sender import Sender
from backend.whatsapp_client import EvolutionClient


router = APIRouter(prefix="/fila", tags=["fila"])


def _envio_dict(session: Session, e: Envio) -> dict:
    """Serializa envio + nome do cliente (otimização: 1 lookup por envio)."""
    c = session.get(Cliente, e.cliente_id) if e.cliente_id else None
    return {
        "id": e.id,
        "cliente_id": e.cliente_id,
        "cliente_nome": c.nome if c else None,
        "telefone_whatsapp_id": e.telefone_whatsapp_id,
        "telefone_destino": e.telefone_destino,
        "modulo": e.modulo,
        "mensagem_texto": e.mensagem_texto,
        "imagem_path": e.imagem_path,
        "status": e.status,
        "erro": e.erro,
        "enviado_em": e.enviado_em.isoformat() if e.enviado_em else None,
        "criado_em": e.criado_em.isoformat() if e.criado_em else None,
    }


@router.get("")
def list_fila(
    incluir_falhas: bool = True,
    incluir_pendentes: bool = True,
    incluir_bloqueados: bool = False,
    limit: int = 200,
    session: Session = Depends(get_session),
) -> dict:
    """Devolve { pendentes: [], falhas: [], bloqueados: [], total: N }."""
    out: dict = {"pendentes": [], "falhas": [], "bloqueados": []}
    if incluir_pendentes:
        rows = session.exec(
            select(Envio).where(Envio.status == StatusEnvio.pendente)
            .order_by(Envio.criado_em).limit(limit)
        ).all()
        out["pendentes"] = [_envio_dict(session, e) for e in rows]
    if incluir_falhas:
        rows = session.exec(
            select(Envio).where(Envio.status == StatusEnvio.falha)
            .order_by(Envio.criado_em.desc()).limit(limit)
        ).all()
        out["falhas"] = [_envio_dict(session, e) for e in rows]
    if incluir_bloqueados:
        rows = session.exec(
            select(Envio).where(Envio.status == StatusEnvio.bloqueado)
            .order_by(Envio.criado_em.desc()).limit(limit)
        ).all()
        out["bloqueados"] = [_envio_dict(session, e) for e in rows]
    out["total"] = (
        len(out["pendentes"]) + len(out["falhas"]) + len(out["bloqueados"])
    )
    return out


@router.post("/{envio_id}/retry")
def retry_envio(
    envio_id: int, session: Session = Depends(get_session),
) -> dict:
    """falha → pendente. Limpa erro. Scheduler/enviar-agora vai retentar."""
    e = session.get(Envio, envio_id)
    if not e:
        raise HTTPException(404, "Envio não encontrado")
    if e.status not in (StatusEnvio.falha, StatusEnvio.bloqueado):
        raise HTTPException(409, f"Status atual {e.status} não permite retry")
    e.status = StatusEnvio.pendente
    e.erro = None
    e.enviado_em = None
    e.mensagem_evolution_id = None
    session.add(e)
    session.commit()
    return {"ok": True, "envio_id": e.id, "novo_status": "pendente"}


@router.post("/{envio_id}/marcar-enviado")
def marcar_enviado(
    envio_id: int,
    nota: Optional[str] = None,
    session: Session = Depends(get_session),
) -> dict:
    """Operador enviou de outro jeito (pane da API). Marca como enviado."""
    e = session.get(Envio, envio_id)
    if not e:
        raise HTTPException(404, "Envio não encontrado")
    if e.status == StatusEnvio.enviado:
        return {"ok": True, "envio_id": e.id, "already": True}
    e.status = StatusEnvio.enviado
    e.enviado_em = datetime.now(timezone.utc)
    if nota:
        e.erro = f"(manual) {nota}"  # reuse campo erro pra anotar
    session.add(e)
    session.commit()
    return {"ok": True, "envio_id": e.id, "novo_status": "enviado"}


@router.post("/{envio_id}/enviar-agora")
def enviar_agora(
    envio_id: int, session: Session = Depends(get_session),
) -> dict:
    """Força dispatch via Sender — pula esperar scheduler."""
    e = session.get(Envio, envio_id)
    if not e:
        raise HTTPException(404, "Envio não encontrado")
    if e.status == StatusEnvio.enviado:
        raise HTTPException(409, "Já está enviado")
    cliente = session.get(Cliente, e.cliente_id)
    if not cliente:
        raise HTTPException(409, "Cliente do envio não existe mais")

    with EvolutionClient() as gw:
        sender = Sender(gw)
        if e.imagem_path:
            novo = sender.send_media(session, cliente, e.mensagem_texto,
                                     e.imagem_path, modulo=e.modulo,
                                     template_id=e.template_id)
        else:
            novo = sender.send_text(session, cliente, e.mensagem_texto,
                                    modulo=e.modulo, template_id=e.template_id)

    # marca o envio antigo como "substituído" (status fica como estava ou enviado se sucesso)
    # decisão simples: se o novo foi enviado, marca o velho como enviado também
    # (pra não duplicar na fila). Se falhou, deixa o velho lá pra retry futuro.
    if novo.status == StatusEnvio.enviado and e.status != StatusEnvio.enviado:
        e.status = StatusEnvio.enviado
        e.enviado_em = novo.enviado_em
        e.mensagem_evolution_id = novo.mensagem_evolution_id
        e.telefone_whatsapp_id = novo.telefone_whatsapp_id
        e.erro = None
        session.add(e)
        session.commit()
    return {"ok": True, "envio_id_original": e.id,
            "envio_id_novo": novo.id, "status_novo": novo.status}
