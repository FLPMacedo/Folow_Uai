"""Gerenciar opt-in cliente↔módulo (M:N).

Cliente sem nenhuma entry = legado, aceita todos os módulos.
Ao criar a 1ª entry, o cliente vira "explícito" e só dispara nos opt-in.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.api.deps import get_session
from backend.models import Cliente, ClienteModulo, Modulo, StatusCliente

router = APIRouter(prefix="/modulos", tags=["modulos"])

ALL_MODULOS = [m.value for m in Modulo]


@router.get("/{modulo}/clientes")
def list_clientes_do_modulo(
    modulo: Modulo, session: Session = Depends(get_session),
) -> list[dict]:
    """Lista clientes ATIVOS que recebem esse módulo (opt-in ou legado)."""
    clientes = session.exec(
        select(Cliente).where(Cliente.status == StatusCliente.ativo)
    ).all()
    out: list[dict] = []
    for c in clientes:
        entries = session.exec(
            select(ClienteModulo).where(ClienteModulo.cliente_id == c.id)
        ).all()
        explicito = bool(entries)
        if not explicito:
            # legado: aceita todos
            out.append({
                "id": c.id, "nome": c.nome, "telefone": c.telefone,
                "origem": "legado",
            })
            continue
        for e in entries:
            if e.modulo == modulo.value and e.ativo:
                out.append({
                    "id": c.id, "nome": c.nome, "telefone": c.telefone,
                    "origem": "opt-in",
                    "opt_in_em": e.opt_in_em.isoformat() if e.opt_in_em else None,
                })
                break
    return out


@router.get("/cliente/{cliente_id}")
def get_opt_ins_do_cliente(
    cliente_id: int, session: Session = Depends(get_session),
) -> dict:
    """Retorna { modulo: { ativo, opt_in_em, observacao } } pra UI."""
    cliente = session.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente não encontrado")
    entries = session.exec(
        select(ClienteModulo).where(ClienteModulo.cliente_id == cliente_id)
    ).all()
    explicito = bool(entries)
    by_mod = {e.modulo: e for e in entries}
    out: dict = {"explicito": explicito, "modulos": {}}
    for m in ALL_MODULOS:
        e = by_mod.get(m)
        if e:
            out["modulos"][m] = {
                "ativo": e.ativo,
                "opt_in_em": e.opt_in_em.isoformat() if e.opt_in_em else None,
                "observacao": e.observacao,
            }
        else:
            # sem entry: legado → ativo=True implícito
            out["modulos"][m] = {
                "ativo": not explicito,  # se já tem outras entries, esse vira explícito-off
                "opt_in_em": None,
                "observacao": None,
                "legado": True,
            }
    return out


@router.put("/cliente/{cliente_id}")
def set_opt_ins_do_cliente(
    cliente_id: int,
    payload: dict,  # { modulos: { "comemorativo": true, ... } }
    session: Session = Depends(get_session),
) -> dict:
    """Substitui as opt-ins do cliente. Cria entry pra cada módulo conhecido."""
    cliente = session.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente não encontrado")
    modulos_dict = payload.get("modulos") or {}
    if not isinstance(modulos_dict, dict):
        raise HTTPException(400, "payload.modulos deve ser dict { modulo: bool }")

    existentes = {
        e.modulo: e for e in session.exec(
            select(ClienteModulo).where(ClienteModulo.cliente_id == cliente_id)
        ).all()
    }
    for m in ALL_MODULOS:
        ativo = bool(modulos_dict.get(m, False))
        if m in existentes:
            existentes[m].ativo = ativo
            session.add(existentes[m])
        else:
            session.add(ClienteModulo(
                cliente_id=cliente_id, modulo=m, ativo=ativo,
            ))
    session.commit()
    return get_opt_ins_do_cliente(cliente_id, session)


@router.post("/{modulo}/importar")
def importar_clientes_para_modulo(
    modulo: Modulo,
    payload: dict,  # { cliente_ids: [1,2,3], ativo: true }
    session: Session = Depends(get_session),
) -> dict:
    """Marca um conjunto de clientes como opt-in pro módulo."""
    cliente_ids: list[int] = payload.get("cliente_ids") or []
    ativo: bool = bool(payload.get("ativo", True))
    if not cliente_ids:
        raise HTTPException(400, "Forneça cliente_ids: list[int]")

    adicionados = 0
    atualizados = 0
    for cid in cliente_ids:
        existing = session.exec(
            select(ClienteModulo).where(
                ClienteModulo.cliente_id == cid,
                ClienteModulo.modulo == modulo.value,
            )
        ).first()
        if existing:
            existing.ativo = ativo
            session.add(existing)
            atualizados += 1
        else:
            session.add(ClienteModulo(
                cliente_id=cid, modulo=modulo.value, ativo=ativo,
            ))
            adicionados += 1
    session.commit()
    return {
        "modulo": modulo.value,
        "adicionados": adicionados,
        "atualizados": atualizados,
    }
