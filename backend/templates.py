"""Render de templates de mensagem + variáveis derivadas do cliente.

Variáveis suportadas (qualquer subconjunto, ausentes ficam `{var}` literal
quando `strict=False` ou levantam KeyError quando `strict=True`):

    {nome} {telefone} {email}
    {plano} {grupo}
    {dias_parceria} {tempo_parceria}
    {dias_restantes} {data_expiracao}
    {dias_inativo}
    {data_nascimento}

Datas formatadas como DD/MM/AAAA. `tempo_parceria` em "X dias" | "X meses" | "X anos".
"""
from __future__ import annotations

from datetime import date
from string import Formatter
from typing import Any, Mapping, Optional


# ============================================================================
# Render
# ============================================================================
class _SafeDict(dict):
    """dict que devolve `{key}` literal pra chaves ausentes (não levanta KeyError)."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render(text: str, variables: Mapping[str, Any], *, strict: bool = False) -> str:
    """Substitui `{var}` no texto.

    `strict=False` (default): chaves ausentes ficam literais.
    `strict=True`: KeyError em ausentes (útil pra validação pré-envio).
    """
    if strict:
        return Formatter().vformat(text, (), dict(variables))
    return Formatter().vformat(text, (), _SafeDict(variables))


def required_variables(text: str) -> set[str]:
    """Extrai placeholders `{var}` declarados no texto."""
    return {
        field_name
        for _, field_name, _, _ in Formatter().parse(text)
        if field_name
    }


# ============================================================================
# Variáveis derivadas
# ============================================================================
def _fmt_date(d: Optional[date]) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


def _tempo_parceria(dias: int) -> str:
    if dias < 0:
        dias = 0
    if dias < 30:
        return f"{dias} dia{'s' if dias != 1 else ''}"
    if dias < 365:
        meses = dias // 30
        return f"{meses} {'mês' if meses == 1 else 'meses'}"
    anos = dias // 365
    return f"{anos} ano{'s' if anos != 1 else ''}"


def derive_cliente_vars(
    cliente: Any,
    *,
    today: Optional[date] = None,
    extras: Optional[Mapping[str, Any]] = None,
    negocio: Any = None,
) -> dict[str, Any]:
    """Calcula variáveis comuns a partir de Cliente SQLModel ou dict.

    `extras` mescla por cima (ex: dias_restantes do plano específico).
    `negocio` (opcional) adiciona {empresa_*}. Quando None, jobs decidem
    se buscam o negócio default — não force aqui pra evitar I/O surpresa.
    """
    today = today or date.today()
    get = (lambda k: cliente.get(k)) if isinstance(cliente, dict) \
        else (lambda k: getattr(cliente, k, None))

    inicio = get("data_inicio_parceria")
    dias_parc = (today - inicio).days if isinstance(inicio, date) else 0

    out: dict[str, Any] = {
        "nome":            get("nome") or "",
        "telefone":        get("telefone") or "",
        "email":           get("email") or "",
        "plano":           get("plano") or "",
        "grupo":           get("grupo") or "",
        "data_nascimento": _fmt_date(get("data_nascimento")),
        "dias_parceria":   dias_parc,
        "tempo_parceria":  _tempo_parceria(dias_parc),
    }
    if negocio is not None:
        out.update(derive_negocio_vars(negocio))
    if extras:
        out.update(extras)
    return out


def derive_negocio_vars(negocio: Any) -> dict[str, str]:
    """Variáveis de empresa pra usar em templates.

    Aceita SQLModel Negocio, dict ou None. None → todas vazias.
    """
    if negocio is None:
        return {
            "empresa_nome": "", "empresa_endereco": "",
            "empresa_telefone": "", "empresa_whatsapp": "",
            "empresa_email": "", "empresa_site": "",
        }
    get = (lambda k: negocio.get(k)) if isinstance(negocio, dict) \
        else (lambda k: getattr(negocio, k, None))
    return {
        "empresa_nome":     get("nome") or "",
        "empresa_endereco": get("endereco") or "",
        "empresa_telefone": get("telefone_contato") or "",
        "empresa_whatsapp": get("whatsapp_duvidas") or "",
        "empresa_email":    get("email") or "",
        "empresa_site":     get("site") or "",
    }
