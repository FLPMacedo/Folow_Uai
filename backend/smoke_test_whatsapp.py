"""Smoke test offline para whatsapp_client. Sem rede.

Run:
    python -m backend.smoke_test_whatsapp

Usa httpx.MockTransport para capturar requests sem rede. Verifica:
  1. apikey header injetada em toda chamada
  2. URL path correto (com instância na URL onde devido)
  3. JSON payload shape correto
  4. normalize_number tira não-dígitos
  5. send_media monta base64+mime+filename
  6. Erros HTTP mapeiam para classes tipadas (401→Auth, 404→NotFound, etc)
  7. Network error (host inalcançável) → EvolutionConnectionError
  8. ping/list_instances/create/connect/state/logout/delete fluxo completo
"""
from __future__ import annotations

import base64
import json
import sys
import tempfile
import traceback
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from backend.whatsapp_client import (  # noqa: E402
    EvolutionAuthError,
    EvolutionClient,
    EvolutionConnectionError,
    EvolutionError,
    EvolutionNotFound,
    EvolutionRateLimited,
    EvolutionServerError,
    normalize_number,
)


results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    icon = "OK " if ok else "FAIL"
    print(f"[{icon}] {label}" + (f" — {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# helpers: handler factory
# ---------------------------------------------------------------------------
def handler_recording(
    captures: list[httpx.Request],
    status: int = 200,
    body: dict | None = None,
):
    """Retorna handler MockTransport que captura requests + responde como configurado."""
    def _h(request: httpx.Request) -> httpx.Response:
        captures.append(request)
        return httpx.Response(status, json=body if body is not None else {"ok": True})
    return _h


def handler_status(status: int, body: dict | None = None):
    def _h(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body or {"error": f"http {status}"})
    return _h


def main() -> int:
    # =====================================================================
    # 1. normalize_number
    # =====================================================================
    cases = [
        ("+55 (31) 99999-9999", "5531999999999"),
        ("5531988887777",       "5531988887777"),
        (" 31 9 8888-7777 ",    "31988887777"),
    ]
    for raw, expected in cases:
        got = normalize_number(raw)
        check(f"normalize_number({raw!r})", got == expected, f"got={got!r}")

    try:
        normalize_number("abc---")
    except ValueError:
        check("normalize_number raises on no-digit", True)
    else:
        check("normalize_number raises on no-digit", False, "no ValueError")

    # =====================================================================
    # 2. apikey header + base URL
    # =====================================================================
    captures: list[httpx.Request] = []
    transport = httpx.MockTransport(handler_recording(captures, 200, {"status": "up"}))
    with EvolutionClient("http://test.local:8080", "MY_KEY", transport=transport) as c:
        c.ping()
    last = captures[-1]
    check("ping → GET /", last.method == "GET" and last.url.path == "/", f"url={last.url}")
    check("apikey header presente", last.headers.get("apikey") == "MY_KEY",
          f"apikey={last.headers.get('apikey')}")
    check("Content-Type JSON", last.headers.get("content-type") == "application/json")

    # =====================================================================
    # 3. create_instance — path + payload
    # =====================================================================
    captures.clear()
    transport = httpx.MockTransport(handler_recording(captures, 201, {
        "instance": {"instanceName": "test1", "status": "created"},
        "qrcode": {"base64": "data:image/png;base64,iVBORw0K…"},
    }))
    with EvolutionClient("http://x:8080", "K", transport=transport) as c:
        out = c.create_instance("test1")
    req = captures[-1]
    body = json.loads(req.content)
    check("create_instance path", req.url.path == "/instance/create")
    check("create_instance method POST", req.method == "POST")
    check("create_instance body.instanceName",
          body.get("instanceName") == "test1", f"body={body}")
    check("create_instance body.qrcode true", body.get("qrcode") is True)
    check("create_instance body.integration default",
          body.get("integration") == "WHATSAPP-BAILEYS")
    check("create_instance retorna dict",
          isinstance(out, dict) and "qrcode" in out, f"keys={list(out.keys())}")

    # =====================================================================
    # 4. send_text — número normalizado + payload
    # =====================================================================
    captures.clear()
    transport = httpx.MockTransport(handler_recording(captures, 200,
        {"key": {"id": "MSG_ID_123"}, "status": "PENDING"}))
    with EvolutionClient("http://x:8080", "K", transport=transport) as c:
        c.send_text("inst1", "+55 (31) 99999-9999", "Olá, Maria!", delay_ms=1200)
    req = captures[-1]
    body = json.loads(req.content)
    check("send_text path com instância",
          req.url.path == "/message/sendText/inst1", f"path={req.url.path}")
    check("send_text number normalizado",
          body.get("number") == "5531999999999", f"body={body}")
    check("send_text text passthrough", body.get("text") == "Olá, Maria!")
    check("send_text delay aplicado", body.get("delay") == 1200)

    # =====================================================================
    # 5. send_media — base64 + filename + mime
    # =====================================================================
    captures.clear()
    transport = httpx.MockTransport(handler_recording(captures, 200,
        {"key": {"id": "MEDIA_ID_999"}}))
    with tempfile.TemporaryDirectory() as td:
        fpath = Path(td) / "feliz.png"
        fpath.write_bytes(b"\x89PNG\r\n\x1a\nFAKEFAKE")
        with EvolutionClient("http://x:8080", "K", transport=transport) as c:
            c.send_media("inst1", "5531999990001", str(fpath),
                         caption="Feliz aniversário!", delay_ms=0)
        req = captures[-1]
        body = json.loads(req.content)
        check("send_media path", req.url.path == "/message/sendMedia/inst1")
        check("send_media mediatype=image (png)", body.get("mediatype") == "image")
        check("send_media mimetype=image/png", body.get("mimetype") == "image/png")
        check("send_media fileName preserved", body.get("fileName") == "feliz.png")
        decoded = base64.b64decode(body["media"])
        check("send_media base64 bate com bytes", decoded == b"\x89PNG\r\n\x1a\nFAKEFAKE")
        check("send_media caption", body.get("caption") == "Feliz aniversário!")
        check("send_media omite delay quando 0", "delay" not in body)

    # =====================================================================
    # 6. Mapeamento de erro HTTP → exceção tipada
    # =====================================================================
    cases_err = [
        (401, EvolutionAuthError),
        (403, EvolutionAuthError),
        (404, EvolutionNotFound),
        (429, EvolutionRateLimited),
        (500, EvolutionServerError),
        (502, EvolutionServerError),
        (418, EvolutionError),  # genérico cai no base
    ]
    for code, exc_cls in cases_err:
        transport = httpx.MockTransport(handler_status(code))
        with EvolutionClient("http://x:8080", "K", transport=transport) as c:
            raised: type | None = None
            try:
                c.ping()
            except EvolutionError as e:
                raised = type(e)
                ok = isinstance(e, exc_cls) and e.status_code == code
                check(f"HTTP {code} → {exc_cls.__name__}", ok,
                      f"got={raised.__name__} sc={e.status_code}")
            else:
                check(f"HTTP {code} → {exc_cls.__name__}", False, "no exception")

    # =====================================================================
    # 7. Erro de rede → EvolutionConnectionError
    # =====================================================================
    def _boom(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("ECONNREFUSED")
    transport = httpx.MockTransport(_boom)
    with EvolutionClient("http://x:8080", "K", transport=transport) as c:
        try:
            c.ping()
        except EvolutionConnectionError:
            check("Network error → EvolutionConnectionError", True)
        except Exception as e:
            check("Network error → EvolutionConnectionError", False, f"got {type(e).__name__}")
        else:
            check("Network error → EvolutionConnectionError", False, "no exception")

    # Timeout também cai em ConnectionError
    def _slow(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timeout")
    transport = httpx.MockTransport(_slow)
    with EvolutionClient("http://x:8080", "K", transport=transport) as c:
        try:
            c.ping()
        except EvolutionConnectionError:
            check("Timeout → EvolutionConnectionError", True)
        else:
            check("Timeout → EvolutionConnectionError", False, "no exception")

    # =====================================================================
    # 8. fluxo completo de instância
    # =====================================================================
    captures.clear()
    seq_responses = iter([
        (201, {"instance": {"instanceName": "smk"}, "qrcode": {"base64": "..."}}),
        (200, [{"name": "smk", "status": "connecting"}]),
        (200, {"base64": "...new-qr..."}),
        (200, {"instance": {"state": "open"}}),
        (200, {"key": {"id": "msg1"}}),
        (200, {"status": "logged_out"}),
        (200, {"status": "deleted"}),
    ])

    def _h(req: httpx.Request) -> httpx.Response:
        captures.append(req)
        status, body = next(seq_responses)
        return httpx.Response(status, json=body)

    transport = httpx.MockTransport(_h)
    with EvolutionClient("http://x:8080", "K", transport=transport) as c:
        c.create_instance("smk")
        c.list_instances()
        c.connect_instance("smk")
        c.connection_state("smk")
        c.send_text("smk", "5531999990001", "hi")
        c.logout_instance("smk")
        c.delete_instance("smk")

    paths_methods = [(r.method, r.url.path) for r in captures]
    expected = [
        ("POST",   "/instance/create"),
        ("GET",    "/instance/fetchInstances"),
        ("GET",    "/instance/connect/smk"),
        ("GET",    "/instance/connectionState/smk"),
        ("POST",   "/message/sendText/smk"),
        ("DELETE", "/instance/logout/smk"),
        ("DELETE", "/instance/delete/smk"),
    ]
    check("Fluxo completo de instância (7 ops)",
          paths_methods == expected,
          f"got={paths_methods}")

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
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(2)
