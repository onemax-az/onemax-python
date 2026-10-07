from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode

LOCALE_PREFIXES = {"az": "", "ru": "/ru", "en": "/en"}


@dataclass(frozen=True)
class Call:
    method: str
    path: str
    body: dict[str, Any] | None = None


def _given(**fields: Any) -> dict[str, Any]:
    return {key: value for key, value in fields.items() if value is not None}


def _usage_path(usage_id: str, action: str = "") -> str:
    return f"/integration/usages/{quote(usage_id, safe='')}{action}"


def context() -> Call:
    return Call("GET", "/integration/context")


def verify_code(code: str, offer_id: str | None) -> Call:
    return Call("POST", "/integration/members/verify", _given(code=code, offer_id=offer_id))


def usage(usage_id: str) -> Call:
    return Call("GET", _usage_path(usage_id))


def confirm_usage(usage_id: str, reference: str | None) -> Call:
    return Call("POST", _usage_path(usage_id, "/confirm"), _given(reference=reference))


def void_usage(usage_id: str) -> Call:
    return Call("POST", _usage_path(usage_id, "/void"))


def exchange_code(code: str, code_verifier: str, redirect_uri: str) -> Call:
    return Call(
        "POST",
        "/integration/links/token",
        {"code": code, "code_verifier": code_verifier, "redirect_uri": redirect_uri},
    )


def link_status(link_token: str) -> Call:
    return Call("POST", "/integration/links/status", {"link_token": link_token})


def verify_link(link_token: str, offer_id: str | None) -> Call:
    return Call(
        "POST", "/integration/links/verify", _given(link_token=link_token, offer_id=offer_id)
    )


def revoke_link(link_token: str) -> Call:
    return Call("POST", "/integration/links/revoke", {"link_token": link_token})


def authorize_url(
    site_url: str,
    *,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    state: str | None,
    locale: str | None,
) -> str:
    prefix = LOCALE_PREFIXES.get(locale or "az")
    if prefix is None:
        raise ValueError(f"locale must be one of az, ru or en, not {locale!r}")
    query = _given(
        response_type="code",
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method="S256",
        state=state,
    )
    return f"{site_url}{prefix}/baglanti?{urlencode(query)}"
