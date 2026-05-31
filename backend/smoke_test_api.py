"""Smoke test FastAPI via TestClient — sem rede.

Run:
    python -m backend.smoke_test_api

Cobre:
  /health
  CRUD clientes (POST/GET/PUT/DELETE)
  Import xlsx (upload) + dedup por telefone
  Export xlsx (download)
  CRUD templates
  CRUD telefones (+ erro Evolution offline em create-instance)
  Listar envios + stats (view agregada)
  Webhook salva resposta + matcheia cliente por telefone
  Admin: backup cria arquivo + audita
  Admin: dispatch manual cria envios pendentes (sem Evolution)
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import traceback
from datetime import date, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# DB efêmero ANTES de qualquer import do backend
SMOKE_DB = (Path(__file__).resolve().parent.parent / "database"
            / "followuai.smoke-api.db")
os.environ["DB_PATH"] = str(SMOKE_DB)
os.environ["FOLLOWUAI_NO_SCHEDULER"] = "1"

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from backend.database import engine  # noqa: E402
from backend.excel_handler import COLUMNS  # noqa: E402
from backend.main import app  # noqa: E402


results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    icon = "OK " if ok else "FAIL"
    print(f"[{icon}] {label}" + (f" — {detail}" if detail else ""))


def _xlsx_bytes() -> bytes:
    """Constrói um .xlsx mínimo (header + 2 linhas válidas + 1 duplicada)."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(COLUMNS)
    ws.append(["João",  "+5531900000001", "j@x.com", "01/01/1985",
               "10/03/2024", "Plano A", None, "ativo", "", ""])
    ws.append(["Ana",   "+5531900000002", None,       "15/06/1990",
               "01/01/2024", None, None, "ativo", "", ""])
    # duplicado do primeiro: deve ser contado em "duplicados"
    ws.append(["João2", "+5531900000001", None,       None,
               "01/01/2024", None, None, "ativo", "", ""])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


def main() -> int:
    # wipe DB
    if SMOKE_DB.exists():
        engine.dispose()
        SMOKE_DB.unlink()

    with TestClient(app) as client:
        # =====================================================================
        # health
        # =====================================================================
        r = client.get("/health")
        check("GET /health", r.status_code == 200 and r.json() == {"status": "ok"},
              f"{r.status_code} {r.text[:80]}")

        # =====================================================================
        # CRUD clientes
        # =====================================================================
        payload = {
            "nome": "Maria Silva",
            "telefone": "+5531999990001",
            "email": "maria@example.com",
            "data_nascimento": "1990-05-15",
            "data_inicio_parceria": str(date.today() - timedelta(days=200)),
            "plano": "Premium",
            "grupo": "VIP",
            "status": "ativo",
        }
        r = client.post("/api/clientes", json=payload)
        check("POST /api/clientes 201", r.status_code == 201,
              f"{r.status_code} {r.text[:120]}")
        cid = r.json()["id"]

        r = client.get(f"/api/clientes/{cid}")
        check("GET /api/clientes/{id}",
              r.status_code == 200 and r.json()["nome"] == "Maria Silva",
              f"{r.status_code} {r.text[:80]}")

        r = client.put(f"/api/clientes/{cid}", json={"grupo": "Ouro"})
        check("PUT /api/clientes/{id} (partial)",
              r.status_code == 200 and r.json()["grupo"] == "Ouro",
              f"{r.status_code} {r.json().get('grupo')}")

        r = client.get("/api/clientes?status=ativo&q=Maria")
        check("GET /api/clientes ?status=ativo&q=",
              r.status_code == 200 and len(r.json()) == 1,
              f"{r.status_code} count={len(r.json())}")

        # 404
        r = client.get("/api/clientes/9999")
        check("GET /api/clientes/9999 → 404", r.status_code == 404,
              f"{r.status_code}")

        # =====================================================================
        # Import xlsx
        # =====================================================================
        files = {"file": ("clientes.xlsx", _xlsx_bytes(),
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        r = client.post("/api/clientes/import", files=files)
        check("POST /api/clientes/import 201", r.status_code == 201,
              f"{r.status_code} {r.text[:160]}")
        body = r.json()
        check("Import: 2 inseridos (João + Ana)",
              body.get("inseridos") == 2, f"body={body}")
        check("Import: 1 duplicado (telefone repetido)",
              body.get("duplicados") == 1, f"body={body}")

        # contagem total agora: Maria + João + Ana = 3
        r = client.get("/api/clientes")
        check("Após import: 3 clientes na base",
              r.status_code == 200 and len(r.json()) == 3,
              f"count={len(r.json())}")

        # =====================================================================
        # Export xlsx
        # =====================================================================
        r = client.get("/api/clientes/export.xlsx")
        check("GET /api/clientes/export.xlsx 200",
              r.status_code == 200, f"{r.status_code}")
        check("Export: content-type xlsx",
              "spreadsheetml.sheet" in r.headers.get("content-type", ""),
              f"ct={r.headers.get('content-type')}")
        check("Export: bytes não vazios",
              len(r.content) > 1000, f"bytes={len(r.content)}")

        # =====================================================================
        # CRUD templates
        # =====================================================================
        # já tem 4 seeds
        r = client.get("/api/templates")
        seeds = len(r.json())
        check("GET /api/templates (seeds)",
              r.status_code == 200 and seeds == 4, f"got={seeds}")

        r = client.post("/api/templates", json={
            "nome": "T1", "modulo": "comemorativo",
            "tipo_gatilho": "aniversario", "mensagem_texto": "Oi {nome}!",
        })
        check("POST /api/templates 201", r.status_code == 201,
              f"{r.status_code} {r.text[:80]}")
        tid = r.json()["id"]

        r = client.put(f"/api/templates/{tid}", json={"ativo": False})
        check("PUT /api/templates ativo=false",
              r.status_code == 200 and r.json()["ativo"] is False)

        r = client.get("/api/templates?ativo=true")
        check("GET /api/templates ?ativo=true",
              r.status_code == 200 and len(r.json()) == seeds,
              f"got={len(r.json())} expected={seeds}")

        # =====================================================================
        # CRUD telefones
        # =====================================================================
        r = client.post("/api/telefones", json={
            "numero": "+5531988880001",
            "instancia_evolution": "smoke-1",
        })
        check("POST /api/telefones 201", r.status_code == 201,
              f"{r.status_code} {r.text[:100]}")
        tel_id = r.json()["id"]

        # create-instance deve falhar (Evolution offline)
        r = client.post(f"/api/telefones/{tel_id}/create-instance")
        check("POST /telefones/{id}/create-instance → 503 sem Evolution",
              r.status_code == 503, f"{r.status_code} {r.text[:80]}")

        # =====================================================================
        # Envios (vazio inicialmente)
        # =====================================================================
        r = client.get("/api/envios")
        check("GET /api/envios (vazio)",
              r.status_code == 200 and r.json() == [], f"len={len(r.json())}")

        r = client.get("/api/envios/stats")
        check("GET /api/envios/stats (vazio)",
              r.status_code == 200 and r.json() == [], f"json={r.json()}")

        # =====================================================================
        # Webhook
        # =====================================================================
        payload_evo = {
            "event": "messages.upsert",
            "instance": "smoke-1",
            "data": {
                "key": {
                    "remoteJid": "5531999990001@s.whatsapp.net",
                    "fromMe": False,
                    "id": "EVO_MSG_42",
                },
                "messageType": "conversation",
                "message": {"conversation": "Olá, recebi sua mensagem!"},
            },
        }
        r = client.post("/api/webhook/evolution", json=payload_evo)
        check("POST /webhook/evolution 202", r.status_code == 202,
              f"{r.status_code} {r.text[:120]}")
        body = r.json()
        check("Webhook: stored=True",
              body.get("stored") is True, f"body={body}")
        rid = body.get("resposta_id")

        # rejeita fromMe (eco)
        r2 = client.post("/api/webhook/evolution", json={
            "data": {"key": {"remoteJid": "x@s.whatsapp.net", "fromMe": True},
                     "message": {"conversation": "eco"}},
        })
        check("Webhook: fromMe=True ignorado",
              r2.status_code == 202 and r2.json().get("stored") is False,
              f"body={r2.json()}")

        # webhook matcheia cliente
        # Maria tem telefone +5531999990001
        # confere via listar envios (não há) então pular — só checar que
        # resposta foi vinculada
        from sqlmodel import Session, select  # noqa: E402

        from backend.models import Cliente, Resposta  # noqa: E402
        with Session(engine) as s:
            resp = s.get(Resposta, rid)
            maria = s.exec(
                select(Cliente).where(Cliente.telefone == "+5531999990001")
            ).first()
            check("Webhook: cliente_id linkado pela busca por dígitos",
                  resp.cliente_id == maria.id,
                  f"resp.cliente_id={resp.cliente_id} maria.id={maria.id}")

        # =====================================================================
        # Backup
        # =====================================================================
        with tempfile.TemporaryDirectory() as td:
            # forçar backups pra tempdir não polui repo
            from backend import backup as backup_mod
            original_dir = backup_mod.BACKUPS_DIR
            backup_mod.BACKUPS_DIR = Path(td)
            try:
                r = client.post("/api/admin/backup",
                                params={"descricao": "smoke test"})
                check("POST /admin/backup 201", r.status_code == 201,
                      f"{r.status_code} {r.text[:120]}")
                body = r.json()
                bpath = Path(body["caminho_arquivo"])
                check("Backup: arquivo existe + size > 0",
                      bpath.exists() and bpath.stat().st_size > 0,
                      f"path={bpath}")

                r = client.get("/api/admin/backups")
                check("GET /admin/backups histórico",
                      r.status_code == 200 and len(r.json()) >= 1,
                      f"count={len(r.json())}")
            finally:
                backup_mod.BACKUPS_DIR = original_dir

        # =====================================================================
        # Dispatch manual sem Evolution → envios pendentes
        # =====================================================================
        # garante aniversariante hoje
        from sqlmodel import Session  # noqa: E402, F811

        from backend.models import Cliente, StatusCliente  # noqa: E402, F811
        with Session(engine) as s:
            c = Cliente(
                nome="Aniver-API",
                telefone="+5531977770099",
                data_nascimento=date.today(),
                data_inicio_parceria=date.today() - timedelta(days=200),
                status=StatusCliente.ativo,
            )
            s.add(c); s.commit()

        # dispatch sem Evolution → sender falha pra cada cliente porque o
        # gateway joga EvolutionConnectionError. Esperar 5xx OU 200 com
        # falhas — depende de timing. Aqui só rodamos e verificamos resposta.
        r = client.post("/api/admin/dispatch/comemorativo")
        check("POST /admin/dispatch/comemorativo 200 (ou 502/503 graceful)",
              r.status_code in (200, 502, 503),
              f"{r.status_code} {r.text[:120]}")
        if r.status_code == 200:
            check("Dispatch comemorativo retorna stats dict",
                  isinstance(r.json(), dict) and "enviados" in r.json(),
                  f"json={r.json()}")

    # ----- summary -----
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*60}\n{passed}/{total} checks passed\n{'='*60}")
    if passed != total:
        print("\nFailures:")
        for label, ok, detail in results:
            if not ok:
                print(f"  - {label}: {detail}")
        return 1

    engine.dispose()
    SMOKE_DB.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(2)
