"""Smoke ponta-a-ponta — Docker → Evolution → uvicorn → API → dispatch.

Usado quando o ambiente já tem Docker Desktop instalado.

Run:
    cd Folow_Uai
    python installer/smoke_test_e2e.py

Flags:
    --skip-docker        usa Docker já rodando, não sobe nem derruba
    --teardown           docker compose down -v no fim (apaga dados)
    --interactive        pausa pra escanear QR antes de dispatch (envio real)
    --keep-data          não deleta cliente/telefone/instância criados
    --port-backend N     porta uvicorn (default 8000)

Comportamento:
  1. Detecta Docker. Se ausente → SKIP exit 0 (não fail).
  2. docker compose up -d em Folow_Uai/docker
  3. Espera http://localhost:8080 responder (Evolution)
  4. Sobe uvicorn em background
  5. Espera http://localhost:8000/health responder
  6. POST /api/clientes (Maria com aniversário hoje)
  7. POST /api/telefones (instância followuai-smoke-{ts})
  8. POST /api/telefones/{id}/create-instance → pega QR
  9. Em --interactive: pausa pra você escanear no WhatsApp
 10. POST /api/admin/dispatch/comemorativo
 11. GET /api/envios → confirma envio (status enviado SE escaneou QR, senão falha)
 12. Cleanup: deleta cliente, instância Evolution, telefone (a menos que --keep-data)
 13. Para uvicorn (sempre); docker compose down (apenas em --teardown)
"""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCKER_DIR   = PROJECT_ROOT / "docker"
VENV_PY      = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
HEALTH_URL   = "http://localhost:{port}/health"
EVO_URL      = "http://localhost:8080"

# Cores ANSI básicas (mesmo terminal Windows moderno suporta)
def C(code, msg): return f"\x1b[{code}m{msg}\x1b[0m"
def info(msg):    print(C("36", f"[..] {msg}"))
def ok(msg):      print(C("32", f"[OK] {msg}"))
def warn(msg):    print(C("33", f"[!!] {msg}"))
def fail(msg):    print(C("31", f"[!!] {msg}"))
def step(desc):   print(C("1;36", f"\n>>> {desc}"))


# =============================================================================
# Detectores
# =============================================================================
def detect_docker() -> tuple[bool, str]:
    if not shutil.which("docker"):
        return False, "docker CLI ausente"
    try:
        out = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return False, f"docker daemon parado: {out.stderr.strip()[:120]}"
        return True, f"daemon v{out.stdout.strip()}"
    except subprocess.TimeoutExpired:
        return False, "docker info timeout"


def port_listening(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            return True
        except OSError:
            return False


def wait_http(url: str, timeout_s: int, label: str) -> bool:
    """Aguarda HTTP 200 até timeout."""
    import httpx
    deadline = time.time() + timeout_s
    last_err = ""
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code < 500:
                ok(f"{label} respondeu HTTP {r.status_code}")
                return True
        except Exception as e:
            last_err = str(e)
        time.sleep(1)
    fail(f"{label} não respondeu em {timeout_s}s. Último erro: {last_err[:120]}")
    return False


# =============================================================================
# Docker stack
# =============================================================================
def docker_compose_up() -> bool:
    step("docker compose up -d")
    try:
        r = subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=str(DOCKER_DIR), capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            fail(f"compose up falhou rc={r.returncode}: {r.stderr[:400]}")
            return False
        ok("compose up ok")
        return True
    except subprocess.TimeoutExpired:
        fail("compose up timeout 120s")
        return False


def docker_compose_down(remove_volumes: bool) -> None:
    step("docker compose down" + (" -v" if remove_volumes else ""))
    args = ["docker", "compose", "down"]
    if remove_volumes:
        args.append("-v")
    subprocess.run(args, cwd=str(DOCKER_DIR), capture_output=True, text=True, timeout=60)


# =============================================================================
# Uvicorn lifecycle
# =============================================================================
@contextmanager
def uvicorn_bg(port: int):
    step(f"Subindo uvicorn em :{port}")
    if not VENV_PY.exists():
        raise RuntimeError(f"venv ausente: {VENV_PY}. Rode installer\\install.ps1.")
    env = os.environ.copy()
    env["FOLLOWUAI_NO_SCHEDULER"] = "1"   # sem cron durante smoke
    proc = subprocess.Popen(
        [str(VENV_PY), "-m", "uvicorn", "backend.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(PROJECT_ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    try:
        yield proc
    finally:
        step("Parando uvicorn")
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        ok("uvicorn parado")


# =============================================================================
# Scenario via API REST
# =============================================================================
def run_scenario(port: int, interactive: bool, keep_data: bool) -> int:
    import httpx
    base = f"http://localhost:{port}/api"
    # Timeout alto: dispatch chama Evolution real e Baileys pode segurar
    # ~30s quando WhatsApp não está pareado.
    client = httpx.Client(base_url=base, timeout=120.0)

    created_cliente_id: int | None = None
    created_telefone_id: int | None = None
    instance_name: str | None = None
    failures: list[str] = []

    def assert_ok(label: str, cond: bool, detail: str = ""):
        if cond:
            ok(f"{label}" + (f" — {detail}" if detail else ""))
        else:
            failures.append(label + (f" — {detail}" if detail else ""))
            fail(f"{label}" + (f" — {detail}" if detail else ""))

    try:
        # 1. health
        step("/health")
        r = client.get("/../health")
        assert_ok("backend /health 200", r.status_code == 200, r.text[:80])

        # 2. cria cliente aniversariante hoje
        step("POST /api/clientes (aniversariante hoje)")
        from datetime import date, timedelta
        payload = {
            "nome": "E2E Smoke",
            "telefone": "+5531900000999",
            "data_nascimento": date.today().isoformat(),
            "data_inicio_parceria": (date.today() - timedelta(days=200)).isoformat(),
            "status": "ativo",
        }
        r = client.post("/clientes", json=payload)
        assert_ok("cliente criado", r.status_code == 201, f"rc={r.status_code} {r.text[:120]}")
        if r.status_code == 201:
            created_cliente_id = r.json()["id"]

        # 3. cria telefone
        ts = int(time.time())
        instance_name = f"followuai-smoke-{ts}"
        step(f"POST /api/telefones (instância={instance_name})")
        r = client.post("/telefones", json={
            "numero": f"+553188888{ts % 10000:04d}",
            "instancia_evolution": instance_name,
        })
        assert_ok("telefone criado", r.status_code == 201, f"rc={r.status_code} {r.text[:120]}")
        if r.status_code == 201:
            created_telefone_id = r.json()["id"]

        # 4. cria instância Evolution → recebe QR
        if created_telefone_id:
            step(f"POST /api/telefones/{created_telefone_id}/create-instance")
            r = client.post(f"/telefones/{created_telefone_id}/create-instance")
            assert_ok("create-instance Evolution",
                      r.status_code in (200, 201),
                      f"rc={r.status_code} {r.text[:160]}")
            if r.status_code in (200, 201):
                body = r.json()
                qr_present = (
                    "qrcode" in body or
                    isinstance(body.get("instance"), dict)
                )
                assert_ok("instância retornou QR/info", qr_present,
                          f"keys={list(body.keys()) if isinstance(body, dict) else type(body).__name__}")

        # 5. interactive pause
        if interactive:
            step("PAUSA INTERATIVA")
            warn("Abra http://localhost:8080 e escaneie o QR da instância:")
            warn(f"    {instance_name}")
            input("Pressione ENTER quando o WhatsApp estiver pareado...")

        # 6. dispatch comemorativo
        step("POST /api/admin/dispatch/comemorativo")
        r = client.post("/admin/dispatch/comemorativo")
        assert_ok("dispatch retornou stats",
                  r.status_code == 200,
                  f"rc={r.status_code} {r.text[:200]}")
        if r.status_code == 200:
            stats = r.json()
            warn(f"stats={stats}")
            # Sem QR escaneado: esperar falhas (Evolution rejeita)
            # Com QR escaneado: esperar enviados >= 1
            total_acoes = stats["enviados"] + stats["falhas"] + stats["pendentes"]
            assert_ok("alguma ação foi tentada (envio + falha + pendente >= 1)",
                      total_acoes >= 1, f"stats={stats}")

        # 7. lista envios do cliente
        if created_cliente_id:
            step(f"GET /api/envios?cliente_id={created_cliente_id}")
            r = client.get("/envios", params={"cliente_id": created_cliente_id})
            assert_ok("envios listou", r.status_code == 200,
                      f"rc={r.status_code}")
            if r.status_code == 200:
                envios = r.json()
                assert_ok(f"≥1 envio para esse cliente ({len(envios)})",
                          len(envios) >= 1)
                if envios:
                    e = envios[0]
                    warn(f"último envio: status={e['status']} erro={e.get('erro')}")

        # 8. stats
        step("GET /api/envios/stats")
        r = client.get("/envios/stats")
        assert_ok("stats listou", r.status_code == 200)
        if r.status_code == 200:
            warn(f"agregado: {r.json()}")

    finally:
        if not keep_data:
            step("Cleanup")
            if created_telefone_id and instance_name:
                # tenta deletar instância Evolution direto
                try:
                    httpx.delete(
                        f"{EVO_URL}/instance/delete/{instance_name}",
                        headers={"apikey": "FOLLOWUAI_API_KEY_SEGURA_2026"},
                        timeout=10.0,
                    )
                except Exception:
                    pass
            try:
                if created_telefone_id is not None:
                    client.delete(f"/telefones/{created_telefone_id}")
                    ok(f"telefone {created_telefone_id} removido")
            except Exception as e:
                warn(f"falha ao deletar telefone: {e}")
            try:
                if created_cliente_id is not None:
                    client.delete(f"/clientes/{created_cliente_id}")
                    ok(f"cliente {created_cliente_id} removido")
            except Exception as e:
                warn(f"falha ao deletar cliente: {e}")
        client.close()

    print()
    if failures:
        fail(f"{len(failures)} falhas:")
        for f in failures:
            print(f"  - {f}")
        return 1
    ok("Cenário E2E passou.")
    return 0


# =============================================================================
# Main
# =============================================================================
def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--skip-docker", action="store_true")
    p.add_argument("--teardown", action="store_true")
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--keep-data", action="store_true")
    p.add_argument("--port-backend", type=int, default=8000)
    args = p.parse_args()

    print(C("1;37", "=" * 60))
    print(C("1;37", "  FollowUai — Smoke E2E (Docker + Evolution + API)"))
    print(C("1;37", "=" * 60))

    # ----- 0. pré-reqs locais -----
    step("Verificando pré-requisitos")
    if not VENV_PY.exists():
        fail(f"venv ausente: {VENV_PY}. Rode installer\\install.ps1 antes.")
        return 2
    ok(f"venv: {VENV_PY}")

    docker_ok, docker_info = detect_docker()
    if not docker_ok:
        warn(f"Docker indisponível: {docker_info}")
        warn("Esse smoke exige Docker Desktop rodando.")
        warn("Pulando (exit 0 — não é falha de código).")
        return 0
    ok(f"Docker: {docker_info}")

    # ----- 1. Docker stack -----
    if not args.skip_docker:
        if not docker_compose_up():
            return 3

    if not wait_http(EVO_URL, 90, "Evolution :8080"):
        if not args.skip_docker:
            docker_compose_down(remove_volumes=False)
        return 4

    # ----- 2. backend uvicorn + cenário -----
    if port_listening(args.port_backend):
        warn(f"Porta {args.port_backend} ocupada — assumindo backend já rodando.")
        backend_owned = False
    else:
        backend_owned = True

    try:
        if backend_owned:
            with uvicorn_bg(args.port_backend) as _proc:
                if not wait_http(
                    HEALTH_URL.format(port=args.port_backend), 30, "uvicorn /health",
                ):
                    return 5
                rc = run_scenario(
                    args.port_backend, args.interactive, args.keep_data,
                )
        else:
            rc = run_scenario(
                args.port_backend, args.interactive, args.keep_data,
            )
    finally:
        if args.teardown and not args.skip_docker:
            docker_compose_down(remove_volumes=True)
        elif not args.skip_docker:
            warn("Containers seguem de pé (use --teardown pra derrubar).")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
