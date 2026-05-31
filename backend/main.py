"""FastAPI app FollowUai — entry point.

Run dev:
    cd Folow_Uai
    .venv/Scripts/uvicorn backend.main:app --reload --port 8000

Swagger docs: http://localhost:8000/docs
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.api import all_routers
from backend.database import init_db


def _start_scheduler() -> bool:
    """Liga scheduler em BackgroundScheduler. Pulado se FOLLOWUAI_NO_SCHEDULER=1."""
    if os.environ.get("FOLLOWUAI_NO_SCHEDULER") == "1":
        logger.info("Scheduler desativado por env var")
        return False
    try:
        from backend.scheduler import build_scheduler

        sched = build_scheduler(blocking=False)
        sched.start()
        logger.info("Scheduler iniciado: {}", [j.id for j in sched.get_jobs()])
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Scheduler falhou ao iniciar")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    init_db()
    logger.info("Schema OK")
    _start_scheduler()
    yield


app = FastAPI(
    title="FollowUai",
    version="0.1.0",
    description="Follow-up automático WhatsApp via Evolution API",
    lifespan=lifespan,
)

# CORS pro Electron/React local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


for router in all_routers:
    app.include_router(router, prefix="/api")
