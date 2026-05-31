"""CRUD clientes + import/export Excel."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from backend.api.deps import get_session
from backend.api.schemas import ClienteCreate, ClienteUpdate
from backend.excel_handler import (
    export_clientes_xlsx,
    import_clientes_xlsx,
)
from backend.models import Cliente, StatusCliente


router = APIRouter(prefix="/clientes", tags=["clientes"])


# ============================================================================
# CRUD
# ============================================================================
@router.post("", response_model=Cliente, status_code=201)
def create_cliente(
    payload: ClienteCreate,
    session: Session = Depends(get_session),
) -> Cliente:
    cliente = Cliente.model_validate(payload.model_dump())
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return cliente


@router.get("", response_model=list[Cliente])
def list_clientes(
    status: Optional[StatusCliente] = None,
    grupo: Optional[str] = None,
    q: Optional[str] = Query(None, description="busca em nome ou telefone"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> list[Cliente]:
    stmt = select(Cliente)
    if status:
        stmt = stmt.where(Cliente.status == status)
    if grupo:
        stmt = stmt.where(Cliente.grupo == grupo)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Cliente.nome.like(like)) | (Cliente.telefone.like(like))
        )
    stmt = stmt.offset(offset).limit(limit)
    return list(session.exec(stmt).all())


# ----------------------------------------------------------------------------
# Rotas estáticas (registrar ANTES das dinâmicas /{cliente_id})
# ----------------------------------------------------------------------------
@router.get("/export.xlsx")
def export_xlsx(
    status: Optional[StatusCliente] = None,
    session: Session = Depends(get_session),
) -> FileResponse:
    stmt = select(Cliente)
    if status:
        stmt = stmt.where(Cliente.status == status)
    clientes = list(session.exec(stmt).all())

    tmp = Path(tempfile.gettempdir()) / "followuai-clientes.xlsx"
    export_clientes_xlsx(clientes, tmp)
    return FileResponse(
        tmp,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="followuai-clientes.xlsx",
    )


@router.post("/import", status_code=201)
async def import_xlsx(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> dict:
    """Upload .xlsx → cria clientes, devolve relatório.

    Linhas com erro são reportadas mas não abortam o import.
    Telefone duplicado retorna erro pra essa linha.
    """
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(400, "Arquivo precisa ser .xlsx")

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        rows, errors = import_clientes_xlsx(tmp_path)

        inseridos = 0
        duplicados = 0
        for row in rows:
            row.pop("tags", None)
            tel = row.get("telefone")
            existing = session.exec(
                select(Cliente).where(Cliente.telefone == tel)
            ).first()
            if existing:
                duplicados += 1
                continue
            session.add(Cliente.model_validate(row))
            inseridos += 1
        session.commit()

        return {
            "inseridos": inseridos,
            "duplicados": duplicados,
            "erros": [
                {"row": e.row, "column": e.column, "message": e.message}
                for e in errors
            ],
        }
    finally:
        tmp_path.unlink(missing_ok=True)


# ----------------------------------------------------------------------------
# Rotas dinâmicas
# ----------------------------------------------------------------------------
@router.get("/{cliente_id}", response_model=Cliente)
def get_cliente(cliente_id: int, session: Session = Depends(get_session)) -> Cliente:
    cliente = session.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente não encontrado")
    return cliente


@router.put("/{cliente_id}", response_model=Cliente)
def update_cliente(
    cliente_id: int,
    payload: ClienteUpdate,
    session: Session = Depends(get_session),
) -> Cliente:
    cliente = session.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente não encontrado")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(cliente, k, v)
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return cliente


@router.delete("/{cliente_id}", status_code=204, response_class=Response)
def delete_cliente(
    cliente_id: int,
    force: bool = Query(False, description="Se true, apaga em cascata envios/respostas/comemorativos/eventos/planos vinculados."),
    session: Session = Depends(get_session),
) -> Response:
    cliente = session.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente não encontrado")

    # Detecta dependências (FK sem CASCADE no schema)
    from backend.models import Comemorativo, Envio, Evento, Plano, Resposta
    deps = {
        "envios":        session.exec(select(Envio).where(Envio.cliente_id == cliente_id)).all(),
        "respostas":     session.exec(select(Resposta).where(Resposta.cliente_id == cliente_id)).all(),
        "comemorativos": session.exec(select(Comemorativo).where(Comemorativo.cliente_id == cliente_id)).all(),
        "eventos":       session.exec(select(Evento).where(Evento.cliente_id == cliente_id)).all(),
        "planos":        session.exec(select(Plano).where(Plano.cliente_id == cliente_id)).all(),
    }
    counts = {k: len(v) for k, v in deps.items() if v}

    if counts and not force:
        raise HTTPException(409, {
            "message": "Cliente tem registros vinculados. Use ?force=true para apagar em cascata.",
            "dependencies": counts,
        })

    # cascade manual
    for items in deps.values():
        for item in items:
            session.delete(item)
    session.delete(cliente)
    session.commit()
    return Response(status_code=204)


