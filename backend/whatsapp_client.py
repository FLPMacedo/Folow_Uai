"""Cliente HTTP para Evolution API v2 (atendai/evolution-api:latest).

MVP scope: criar instância, conectar via QR, enviar texto, enviar mídia,
checar estado de conexão. Não trata webhook (vive em webhook_server.py).

Antibanimento: o intervalo entre envios é responsabilidade do scheduler,
não do client. Rotação multi-número também é decisão de cima.

Tudo síncrono — APScheduler dispara em thread pool, FastAPI handlers
podem chamar via `run_in_threadpool`.
"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any, Optional

import httpx

from backend.config import settings


# ============================================================================
# Exceções tipadas
# ============================================================================
class EvolutionError(Exception):
    """Base — falha contra a Evolution API."""

    def __init__(self, message: str, *, status_code: Optional[int] = None,
                 payload: Optional[Any] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class EvolutionAuthError(EvolutionError):
    """401/403 — apikey inválida ou ausente."""


class EvolutionNotFound(EvolutionError):
    """404 — instância/recurso inexistente."""


class EvolutionRateLimited(EvolutionError):
    """429 — rate limit ou WhatsApp bloqueando."""


class EvolutionServerError(EvolutionError):
    """5xx — Evolution caiu ou erro interno."""


class EvolutionConnectionError(EvolutionError):
    """Network/timeout — Docker parado, porta errada, sem rede."""


# ============================================================================
# Helpers
# ============================================================================
def normalize_number(number: str) -> str:
    """`+55 (31) 99999-9999` → `5531999999999`. Evolution v2 exige só dígitos."""
    digits = "".join(c for c in number if c.isdigit())
    if not digits:
        raise ValueError(f"Número sem dígitos: {number!r}")
    return digits


def _b64_file(path: str | Path) -> tuple[str, str, str]:
    """Lê arquivo, retorna (base64, mimetype, filename)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Mídia não encontrada: {p}")
    mime, _ = mimetypes.guess_type(p.name)
    if not mime:
        mime = "application/octet-stream"
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return data, mime, p.name


# ============================================================================
# Cliente
# ============================================================================
class EvolutionClient:
    """Cliente síncrono para Evolution API v2."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.base_url = (base_url or settings.EVOLUTION_API_URL).rstrip("/")
        self.api_key = api_key or settings.EVOLUTION_API_KEY
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "apikey": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=timeout,
            transport=transport,
        )

    # ---- lifecycle ----
    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "EvolutionClient":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    # ---- low-level ----
    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict[str, Any]] = None,
    ) -> Any:
        try:
            r = self._client.request(method, path, json=json)
        except httpx.TimeoutException as e:
            raise EvolutionConnectionError(f"Timeout: {e}") from e
        except httpx.RequestError as e:
            raise EvolutionConnectionError(f"Network error: {e}") from e

        if r.is_success:
            if not r.content:
                return {}
            try:
                return r.json()
            except ValueError:
                return r.text

        text = r.text
        payload: Any = None
        try:
            payload = r.json()
        except ValueError:
            pass

        code = r.status_code
        msg = f"{method} {path} → {code}: {text[:500]}"
        if code in (401, 403):
            raise EvolutionAuthError(msg, status_code=code, payload=payload)
        if code == 404:
            raise EvolutionNotFound(msg, status_code=code, payload=payload)
        if code == 429:
            raise EvolutionRateLimited(msg, status_code=code, payload=payload)
        if code >= 500:
            raise EvolutionServerError(msg, status_code=code, payload=payload)
        raise EvolutionError(msg, status_code=code, payload=payload)

    # ---- health ----
    def ping(self) -> Any:
        """GET /. Confirma se Evolution está no ar."""
        return self._request("GET", "/")

    # ---- instances ----
    def create_instance(
        self,
        instance_name: str,
        *,
        qrcode: bool = True,
        integration: str = "WHATSAPP-BAILEYS",
    ) -> dict[str, Any]:
        """POST /instance/create. Retorna QR code base64 quando `qrcode=True`."""
        return self._request("POST", "/instance/create", json={
            "instanceName": instance_name,
            "qrcode": qrcode,
            "integration": integration,
        })

    def list_instances(self) -> Any:
        """GET /instance/fetchInstances."""
        return self._request("GET", "/instance/fetchInstances")

    def connect_instance(self, instance: str) -> dict[str, Any]:
        """GET /instance/connect/{instance}. Devolve QR code novo."""
        return self._request("GET", f"/instance/connect/{instance}")

    def connection_state(self, instance: str) -> dict[str, Any]:
        """GET /instance/connectionState/{instance}. `state`: `open`|`close`|`connecting`."""
        return self._request("GET", f"/instance/connectionState/{instance}")

    def logout_instance(self, instance: str) -> dict[str, Any]:
        """DELETE /instance/logout/{instance}."""
        return self._request("DELETE", f"/instance/logout/{instance}")

    def delete_instance(self, instance: str) -> dict[str, Any]:
        """DELETE /instance/delete/{instance}."""
        return self._request("DELETE", f"/instance/delete/{instance}")

    # ---- messaging ----
    def send_text(
        self,
        instance: str,
        number: str,
        text: str,
        *,
        delay_ms: int = 0,
        link_preview: bool = False,
    ) -> dict[str, Any]:
        """POST /message/sendText/{instance}."""
        payload: dict[str, Any] = {
            "number": normalize_number(number),
            "text": text,
        }
        if delay_ms:
            payload["delay"] = delay_ms
        if link_preview:
            payload["linkPreview"] = True
        return self._request("POST", f"/message/sendText/{instance}", json=payload)

    def send_media(
        self,
        instance: str,
        number: str,
        media_path: str | Path,
        *,
        caption: str = "",
        mediatype: Optional[str] = None,  # 'image' | 'video' | 'document' | 'audio'
        delay_ms: int = 0,
    ) -> dict[str, Any]:
        """POST /message/sendMedia/{instance}. Carrega arquivo local em base64."""
        b64, mime, filename = _b64_file(media_path)
        if mediatype is None:
            mediatype = _infer_mediatype(mime)
        payload: dict[str, Any] = {
            "number": normalize_number(number),
            "mediatype": mediatype,
            "mimetype": mime,
            "media": b64,
            "fileName": filename,
            "caption": caption,
        }
        if delay_ms:
            payload["delay"] = delay_ms
        return self._request("POST", f"/message/sendMedia/{instance}", json=payload)


def _infer_mediatype(mime: str) -> str:
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/"):
        return "audio"
    return "document"
