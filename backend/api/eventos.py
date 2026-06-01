"""CRUD de Eventos — pós-venda (compras) + eventos agendados."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select

from backend.api.deps import get_session
from backend.api.schemas import EventoBroadcastCreate, EventoCreate, EventoUpdate
from backend.models import Cliente, ClienteGrupo, Evento, StatusCliente, TipoEvento


router = APIRouter(prefix="/eventos", tags=["eventos"])


@router.post("", response_model=Evento, status_code=201)
def create_evento(
    payload: EventoCreate,
    session: Session = Depends(get_session),
) -> Evento:
    cliente = session.get(Cliente, payload.cliente_id)
    if not cliente:
        raise HTTPException(400, f"Cliente {payload.cliente_id} não encontrado")
    ev = Evento.model_validate(payload.model_dump())
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


def _clientes_do_grupo(session: Session, grupo_id: int) -> list[Cliente]:
    """Lista clientes ativos no grupo via M:N OU via legado grupo_id.

    Política: linhas em cliente_grupos têm prioridade. Se um cliente NÃO
    tem nenhuma linha em cliente_grupos mas tem grupo_id == grupo_id,
    também entra (compat com cadastros antigos do dropdown single).
    """
    # via M:N
    via_mn = session.exec(
        select(Cliente).join(
            ClienteGrupo, ClienteGrupo.cliente_id == Cliente.id,
        ).where(
            ClienteGrupo.grupo_id == grupo_id,
            Cliente.status == StatusCliente.ativo,
        )
    ).all()
    ids_mn = {c.id for c in via_mn}
    # legado: clientes que TÊM grupo_id == este E não estão em cliente_grupos
    legados = session.exec(
        select(Cliente).where(
            Cliente.grupo_id == grupo_id,
            Cliente.status == StatusCliente.ativo,
            Cliente.id.notin_(  # type: ignore[union-attr]
                select(ClienteGrupo.cliente_id)
            ),
        )
    ).all()
    return list(via_mn) + [c for c in legados if c.id not in ids_mn]


@router.get("/preview-broadcast/{grupo_id}")
def preview_broadcast(
    grupo_id: int, session: Session = Depends(get_session),
) -> dict:
    """Quantos clientes ATIVOS serão alvo se o evento for criado pra esse grupo."""
    clientes = _clientes_do_grupo(session, grupo_id)
    return {
        "grupo_id": grupo_id,
        "total_clientes_ativos": len(clientes),
        "amostra_nomes": [c.nome for c in clientes[:10]],
    }


@router.post("/broadcast", status_code=201)
def create_evento_broadcast(
    payload: EventoBroadcastCreate,
    session: Session = Depends(get_session),
) -> dict:
    """Cria 1 Evento por cliente ATIVO do grupo. Retorna contagem + IDs criados.

    Útil pra ações em massa: "festa pra todo grupo VIP" → cria N eventos
    em uma transação, cada um vinculado a 1 cliente real.
    """
    clientes = _clientes_do_grupo(session, payload.grupo_id)
    if not clientes:
        raise HTTPException(
            400,
            f"Grupo {payload.grupo_id} sem clientes ativos. "
            "Cadastre clientes nesse grupo primeiro."
        )

    criados: list[Evento] = []
    base_data = payload.model_dump(exclude={"grupo_id"})
    for c in clientes:
        data = {**base_data, "cliente_id": c.id}
        ev = Evento.model_validate(data)
        session.add(ev)
        criados.append(ev)
    session.commit()
    for ev in criados:
        session.refresh(ev)

    return {
        "criados": len(criados),
        "grupo_id": payload.grupo_id,
        "evento_ids": [ev.id for ev in criados],
    }


@router.get("", response_model=list[Evento])
def list_eventos(
    cliente_id: Optional[int] = None,
    tipo_evento: Optional[TipoEvento] = None,
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> list[Evento]:
    stmt = select(Evento)
    if cliente_id is not None:
        stmt = stmt.where(Evento.cliente_id == cliente_id)
    if tipo_evento is not None:
        stmt = stmt.where(Evento.tipo_evento == tipo_evento)
    stmt = stmt.order_by(Evento.data_evento.desc()).offset(offset).limit(limit)
    return list(session.exec(stmt).all())


@router.get("/{evento_id}", response_model=Evento)
def get_evento(evento_id: int, session: Session = Depends(get_session)) -> Evento:
    ev = session.get(Evento, evento_id)
    if not ev:
        raise HTTPException(404, "Evento não encontrado")
    return ev


@router.put("/{evento_id}", response_model=Evento)
def update_evento(
    evento_id: int,
    payload: EventoUpdate,
    session: Session = Depends(get_session),
) -> Evento:
    ev = session.get(Evento, evento_id)
    if not ev:
        raise HTTPException(404, "Evento não encontrado")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(ev, k, v)
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


@router.delete("/{evento_id}", status_code=204, response_class=Response)
def delete_evento(evento_id: int, session: Session = Depends(get_session)) -> Response:
    ev = session.get(Evento, evento_id)
    if not ev:
        raise HTTPException(404, "Evento não encontrado")
    session.delete(ev)
    session.commit()
    return Response(status_code=204)
