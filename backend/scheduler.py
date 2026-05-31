"""APScheduler wiring — registra jobs MVP rodando diariamente.

Uso standalone (sem FastAPI):
    python -m backend.scheduler

Uso embedded (FastAPI lifespan):
    from backend.scheduler import build_scheduler
    sched = build_scheduler()
    sched.start()
    ...
    sched.shutdown()
"""
from __future__ import annotations

import signal
from contextlib import contextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from sqlmodel import Session

from backend.database import engine, init_db
from backend.jobs import (
    dispatch_comemorativo,
    dispatch_evento,
    dispatch_expiracao,
    dispatch_pos_venda,
)
from backend.sender import Sender
from backend.whatsapp_client import EvolutionClient


# ============================================================================
# Job wrappers — abrem sessão própria, isolam falhas
# ============================================================================
def _run_comemorativo() -> None:
    logger.info("[job] comemorativo iniciando")
    try:
        with _session_scope() as (session, sender):
            stats = dispatch_comemorativo(session, sender)
            logger.info("[job] comemorativo done {}", stats)
    except Exception:  # noqa: BLE001
        logger.exception("[job] comemorativo falhou")


def _run_expiracao() -> None:
    logger.info("[job] expiracao iniciando")
    try:
        with _session_scope() as (session, sender):
            stats = dispatch_expiracao(session, sender)
            logger.info("[job] expiracao done {}", stats)
    except Exception:  # noqa: BLE001
        logger.exception("[job] expiracao falhou")


def _run_pos_venda() -> None:
    logger.info("[job] pos_venda iniciando")
    try:
        with _session_scope() as (session, sender):
            stats = dispatch_pos_venda(session, sender)
            logger.info("[job] pos_venda done {}", stats)
    except Exception:  # noqa: BLE001
        logger.exception("[job] pos_venda falhou")


def _run_evento() -> None:
    logger.info("[job] evento iniciando")
    try:
        with _session_scope() as (session, sender):
            stats = dispatch_evento(session, sender)
            logger.info("[job] evento done {}", stats)
    except Exception:  # noqa: BLE001
        logger.exception("[job] evento falhou")


@contextmanager
def _session_scope():
    with Session(engine) as session:
        with EvolutionClient() as gateway:
            yield session, Sender(gateway)


# ============================================================================
# Builder
# ============================================================================
def build_scheduler(*, blocking: bool = False):
    """Cria scheduler com jobs registrados, não iniciado."""
    sched = BlockingScheduler() if blocking else BackgroundScheduler()

    # Comemorativo: todo dia 09:00 local
    sched.add_job(
        _run_comemorativo,
        CronTrigger(hour=9, minute=0),
        id="comemorativo",
        replace_existing=True,
    )
    # Expiração: todo dia 09:30 local
    sched.add_job(
        _run_expiracao,
        CronTrigger(hour=9, minute=30),
        id="expiracao",
        replace_existing=True,
    )
    # Pós-Venda: todo dia 09:15 local
    sched.add_job(
        _run_pos_venda,
        CronTrigger(hour=9, minute=15),
        id="pos_venda",
        replace_existing=True,
    )
    # Evento (véspera/pós): todo dia 09:45 local
    sched.add_job(
        _run_evento,
        CronTrigger(hour=9, minute=45),
        id="evento",
        replace_existing=True,
    )
    return sched


# ============================================================================
# Entrypoint standalone
# ============================================================================
def main() -> None:
    init_db()
    logger.info("Schema inicializado em {}", engine.url)

    sched = build_scheduler(blocking=True)
    logger.info("Jobs registrados: {}", [j.id for j in sched.get_jobs()])

    def _stop(_signum, _frame):
        logger.warning("Shutdown solicitado")
        sched.shutdown(wait=False)

    signal.signal(signal.SIGINT, _stop)
    try:
        signal.signal(signal.SIGTERM, _stop)
    except (AttributeError, ValueError):
        pass  # Windows sem SIGTERM em main thread

    sched.start()


if __name__ == "__main__":
    main()
