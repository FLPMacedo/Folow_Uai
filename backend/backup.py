"""Backup do SQLite + audit table.

Usa `sqlite3.Connection.backup()` (online backup API) — copia consistente mesmo
com escritores ativos. Diferente de `shutil.copy()`, que pode pegar arquivo
no meio de uma transação.
"""
from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from sqlmodel import Session, select

from backend.config import settings
from backend.models import Backup


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKUPS_DIR = PROJECT_ROOT / "backups"


def _ensure_dir() -> Path:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUPS_DIR


def create_backup(
    session: Session,
    *,
    descricao: Optional[str] = None,
    db_path: Optional[Path] = None,
    dest_dir: Optional[Path] = None,
) -> Backup:
    """Copia DB para `backups/followuai-YYYYMMDD-HHMMSS.db` e registra na tabela `backups`."""
    src = Path(db_path) if db_path else Path(settings.DB_PATH)
    if not src.exists():
        raise FileNotFoundError(f"DB ausente: {src}")

    dest_dir = Path(dest_dir) if dest_dir else _ensure_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = dest_dir / f"followuai-{ts}.db"

    src_conn = sqlite3.connect(str(src))
    try:
        dest_conn = sqlite3.connect(str(dest))
        try:
            src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        src_conn.close()

    size = dest.stat().st_size
    record = Backup(
        caminho_arquivo=str(dest),
        tamanho_bytes=size,
        descricao=descricao,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    logger.info("Backup criado: {} ({} bytes)", dest, size)
    return record


def list_backups(session: Session) -> list[Backup]:
    """Histórico mais recente primeiro."""
    return list(session.exec(
        select(Backup).order_by(Backup.criado_em.desc())
    ).all())


def restore_backup(
    backup_path: str | Path,
    *,
    db_path: Optional[Path] = None,
) -> Path:
    """Substitui DB ativo pelo backup. Não toca audit table.

    ATENÇÃO: chamar com scheduler/API parados. Em produção, mover via UI
    com confirmação irreversível.
    """
    src = Path(backup_path)
    if not src.exists():
        raise FileNotFoundError(f"Backup ausente: {src}")
    dst = Path(db_path) if db_path else Path(settings.DB_PATH)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    logger.warning("DB restaurado de {} → {}", src, dst)
    return dst
