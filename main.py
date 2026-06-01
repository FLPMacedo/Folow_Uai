"""FollowUai — entrypoint local (1 comando para subir tudo).

Uso (do diretório Folow_Uai/):
    python main.py                      # docker + backend (foreground)
    python main.py --frontend           # docker + backend + Electron
    python main.py --no-docker          # só backend (Docker manual)
    python main.py --no-docker --frontend
    python main.py --port 8001

Ctrl+C derruba tudo (uvicorn + Electron).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


# ============================================================================
# Re-exec no venv — DEVE ser o PRIMEIRO bloco, antes de importar uvicorn etc.
# ============================================================================
def _ensure_venv() -> None:
    """Se ainda não estamos no venv, re-exec com .venv/Scripts/python.exe."""
    if os.environ.get("FOLLOWUAI_VENV_ACTIVE") == "1":
        return  # já reexecutado neste run
    venv_py = ROOT / (
        ".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python"
    )
    if not venv_py.exists():
        return  # sem venv — deixa cair no erro claro mais adiante
    try:
        if Path(sys.executable).resolve() == venv_py.resolve():
            return  # já é o venv python
    except OSError:
        pass
    print(f"[..] Re-executando no venv: {venv_py}", flush=True)
    env = os.environ.copy()
    env["FOLLOWUAI_VENV_ACTIVE"] = "1"
    result = subprocess.run([str(venv_py), *sys.argv], env=env, cwd=str(ROOT))
    sys.exit(result.returncode)


_ensure_venv()  # noqa: E402


# ============================================================================
# Imports após garantir venv
# ============================================================================
import argparse
import shutil
import signal
import socket
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

DOCKER_DIR   = ROOT / "docker"
FRONTEND_DIR = ROOT / "frontend"


# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------
def _c(code: str, msg: str) -> str:
    if os.environ.get("NO_COLOR"):
        return msg
    return f"\x1b[{code}m{msg}\x1b[0m"


def info(msg: str) -> None:  print(_c("36",   f"[..] {msg}"))
def ok(msg: str)   -> None:  print(_c("32",   f"[OK] {msg}"))
def warn(msg: str) -> None:  print(_c("33",   f"[!!] {msg}"))
def fail(msg: str) -> None:  print(_c("31",   f"[!!] {msg}"))
def head(msg: str) -> None:  print(_c("1;36", f"\n>>> {msg}"))


# ---------------------------------------------------------------------------
# Detectores
# ---------------------------------------------------------------------------
def find_docker() -> str | None:
    """Acha docker mesmo quando PATH não atualizou nessa sessão."""
    on_path = shutil.which("docker")
    if on_path:
        return on_path
    candidates = [
        r"C:\Program Files\Docker\Docker\resources\bin\docker.exe",
        os.path.expandvars(r"%LocalAppData%\Docker\Docker\resources\bin\docker.exe"),
        "/usr/local/bin/docker",
        "/usr/bin/docker",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def port_listening(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            return True
        except OSError:
            return False


def wait_port(port: int, label: str, timeout_s: int = 60) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if port_listening(port):
            ok(f"{label} ouvindo em :{port}")
            return True
        time.sleep(1)
    fail(f"{label} não respondeu em {timeout_s}s")
    return False


# ---------------------------------------------------------------------------
# Stack Docker
# ---------------------------------------------------------------------------
def ensure_docker_stack(docker_bin: str) -> None:
    head("Subindo Evolution + Postgres + Redis (docker compose up -d)")
    proc = subprocess.run(
        [docker_bin, "compose", "up", "-d"],
        cwd=str(DOCKER_DIR), capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0:
        fail("docker compose up falhou:")
        print(proc.stderr)
        sys.exit(2)
    ok("Containers requisitados")
    if not wait_port(8080, "Evolution :8080", timeout_s=120):
        warn("Stack subiu mas Evolution não respondeu em 120s — confira `docker compose logs`")


# ---------------------------------------------------------------------------
# Frontend (Electron)
# ---------------------------------------------------------------------------
def launch_electron() -> subprocess.Popen | None:
    bin_name = "electron.cmd" if os.name == "nt" else "electron"
    bin_path = FRONTEND_DIR / "node_modules" / ".bin" / bin_name
    if not bin_path.exists():
        warn(f"Electron não instalado em {FRONTEND_DIR}. Pulando painel.")
        warn("  Pra ativar: cd frontend && npm install")
        return None
    head("Lançando painel Electron em paralelo")
    return subprocess.Popen([str(bin_path), "."], cwd=str(FRONTEND_DIR))


# ---------------------------------------------------------------------------
# Backend (uvicorn em foreground)
# ---------------------------------------------------------------------------
def run_uvicorn(host: str, port: int) -> None:
    # Garante sys.path correto pra importar backend.main
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    try:
        import uvicorn  # noqa: WPS433
    except ImportError:
        fail("uvicorn ausente — esse main.py precisa do venv ativado.")
        fail("Rode antes:  .venv\\Scripts\\activate")
        sys.exit(3)

    head(f"Backend FastAPI em http://{host}:{port}")
    print(f"     Swagger:  http://{host}:{port}/docs")
    print(f"     Health:   http://{host}:{port}/health")
    print(f"     API base: http://{host}:{port}/api")
    print(f"\n     {_c('1;33', 'Ctrl+C pra parar')}\n")
    uvicorn.run(
        "backend.main:app",
        host=host, port=port,
        reload=False, log_level="info",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="FollowUai — entrypoint local",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--no-docker",   action="store_true",
                    help="não sobe Evolution/Postgres/Redis")
    ap.add_argument("--no-frontend", action="store_true",
                    help="só backend (sem painel) — default liga Electron se instalado")
    ap.add_argument("--frontend",    action="store_true",
                    help="(legado, mantido por compat) — frontend já é default")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    print(_c("1;37", "=" * 60))
    print(_c("1;37", "  FollowUai — o follow-up que seu negócio merece"))
    print(_c("1;37", "=" * 60))

    # 1. Docker stack
    if not args.no_docker:
        docker_bin = find_docker()
        if not docker_bin:
            fail("Docker não encontrado. Use --no-docker ou instale Docker Desktop.")
            return 1
        ensure_docker_stack(docker_bin)
    else:
        warn("Docker pulado (--no-docker) — Evolution precisa estar de pé manualmente")

    # 2. Painel Electron — default ON, desliga com --no-frontend
    electron_proc: subprocess.Popen | None = None
    if not args.no_frontend:
        electron_proc = launch_electron()

    # 3. Backend foreground
    def _cleanup(*_a):
        if electron_proc and electron_proc.poll() is None:
            try:
                electron_proc.terminate()
            except Exception:
                pass

    signal.signal(signal.SIGINT, lambda *_: (_cleanup(), sys.exit(130)))
    try:
        signal.signal(signal.SIGTERM, lambda *_: (_cleanup(), sys.exit(143)))
    except (AttributeError, ValueError):
        pass

    try:
        run_uvicorn(args.host, args.port)
    finally:
        _cleanup()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
