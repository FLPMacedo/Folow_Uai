"""Smoke test live contra Evolution API real (precisa Docker rodando).

Run:
    cd Folow_Uai/docker && docker compose up -d
    cd ..
    .venv/Scripts/python -m backend.smoke_test_evolution_live

Não destrutivo na conta WhatsApp: cria instância descartável, não vincula
número, deleta no fim. Se Evolution não responder, pula com mensagem.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import settings  # noqa: E402
from backend.whatsapp_client import (  # noqa: E402
    EvolutionClient,
    EvolutionConnectionError,
    EvolutionError,
    EvolutionNotFound,
)


SMOKE_INSTANCE = f"followuai-smoke-{int(time.time())}"

results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    icon = "OK  " if ok else "FAIL"
    print(f"[{icon}] {label}" + (f" — {detail}" if detail else ""))


def main() -> int:
    print(f"Evolution URL: {settings.EVOLUTION_API_URL}")
    print(f"Smoke instance: {SMOKE_INSTANCE}")

    client = EvolutionClient()
    # ---- reachability ----
    try:
        info = client.ping()
        check("Evolution reachable", True,
              f"resp={str(info)[:120]}")
    except EvolutionConnectionError as e:
        print(f"\n[SKIP] Evolution não responde em {settings.EVOLUTION_API_URL}")
        print(f"       Causa: {e}")
        print("       Suba o Docker primeiro:")
        print("         cd Folow_Uai/docker && docker compose up -d")
        client.close()
        return 0  # skip = sucesso (não há o que testar)
    except EvolutionError as e:
        check("Evolution reachable", False, f"{e}")
        client.close()
        return 1

    created = False
    try:
        # ---- listar instâncias antes ----
        before = client.list_instances()
        check("list_instances retornou", isinstance(before, (list, dict)),
              f"type={type(before).__name__}")

        # ---- criar instância descartável ----
        out = client.create_instance(SMOKE_INSTANCE)
        created = True
        has_qr = isinstance(out, dict) and (
            "qrcode" in out or "qr" in out
            or (isinstance(out.get("instance"), dict) and "qrcode" in out["instance"])
        )
        check("create_instance retornou (com QR esperado)", has_qr,
              f"keys={list(out.keys()) if isinstance(out, dict) else type(out).__name__}")

        # ---- connection state (esperado: connecting/close, NÃO open) ----
        time.sleep(1)
        state = client.connection_state(SMOKE_INSTANCE)
        state_str = str(state).lower()
        check("connection_state respondeu",
              state is not None,
              f"state={str(state)[:120]}")
        check("Estado não está 'open' (esperado: sem WhatsApp pareado)",
              "open" not in state_str or "connecting" in state_str or "close" in state_str,
              f"state={str(state)[:120]}")

        # ---- listar de novo, esperar nova instância presente ----
        after = client.list_instances()
        names = _extract_instance_names(after)
        check("Nova instância aparece em fetchInstances",
              SMOKE_INSTANCE in names,
              f"found={[n for n in names if 'smoke' in n.lower()]}")

    finally:
        # ---- cleanup ----
        if created:
            try:
                client.delete_instance(SMOKE_INSTANCE)
                check("delete_instance cleanup", True)
            except EvolutionNotFound:
                check("delete_instance cleanup", True, "já não existia")
            except EvolutionError as e:
                check("delete_instance cleanup", False, f"{e}")
        client.close()

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*60}\n{passed}/{total} checks passed\n{'='*60}")
    if passed != total:
        print("\nFailures:")
        for label, ok, detail in results:
            if not ok:
                print(f"  - {label}: {detail}")
        return 1
    return 0


def _extract_instance_names(payload) -> list[str]:
    """Tolera schemas variantes da Evolution (list[dict] ou dict aninhado)."""
    out: list[str] = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                for key in ("name", "instanceName"):
                    if key in item:
                        out.append(item[key])
                        break
                inst = item.get("instance")
                if isinstance(inst, dict):
                    for key in ("name", "instanceName"):
                        if key in inst:
                            out.append(inst[key])
                            break
    elif isinstance(payload, dict):
        for v in payload.values():
            out.extend(_extract_instance_names(v))
    return out


if __name__ == "__main__":
    raise SystemExit(main())
