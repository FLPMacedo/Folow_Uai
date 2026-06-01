"""Routers FastAPI agrupados por recurso."""
from backend.api.admin import router as admin_router
from backend.api.agenda import router as agenda_router
from backend.api.catalogo import grupos_router, planos_router
from backend.api.clientes import router as clientes_router
from backend.api.envios import router as envios_router
from backend.api.eventos import router as eventos_router
from backend.api.fila import router as fila_router
from backend.api.negocios import router as negocios_router
from backend.api.telefones import router as telefones_router
from backend.api.templates import router as templates_router
from backend.api.webhook import router as webhook_router

all_routers = [
    negocios_router,
    planos_router,
    grupos_router,
    clientes_router,
    telefones_router,
    templates_router,
    eventos_router,
    envios_router,
    agenda_router,
    fila_router,
    webhook_router,
    admin_router,
]
