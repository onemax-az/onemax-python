from __future__ import annotations

from types import TracebackType
from typing import Any

import httpx

from . import _endpoints as ep
from . import _transport
from ._transport import API_URL, DEFAULT_TIMEOUT, SITE_URL
from .errors import TransportError
from .models import Context, LinkStatus, LinkToken, Usage, Verification


class OneMaxClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = API_URL,
        site_url: str = SITE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        transport: httpx.Client | None = None,
    ) -> None:
        self._headers = _transport.headers(_transport.checked_key(api_key))
        self.base_url = base_url.rstrip("/")
        self.site_url = site_url.rstrip("/")
        self._http = transport or httpx.Client(timeout=timeout)

    def __enter__(self) -> OneMaxClient:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def _send(self, call: ep.Call) -> dict[str, Any]:
        try:
            response = self._http.request(
                call.method, f"{self.base_url}{call.path}", json=call.body, headers=self._headers
            )
        except httpx.HTTPError as error:
            raise TransportError(str(error) or type(error).__name__) from error
        return _transport.read(response.status_code, response.text)

    def context(self) -> Context:
        return Context.parse(self._send(ep.context()))

    def verify_code(self, code: str, *, offer_id: str | None = None) -> Verification:
        return Verification.parse(self._send(ep.verify_code(code, offer_id)))

    def usage(self, usage_id: str) -> Usage:
        return Usage.parse(self._send(ep.usage(usage_id)))

    def confirm_usage(self, usage_id: str, *, reference: str | None = None) -> Usage:
        return Usage.parse(self._send(ep.confirm_usage(usage_id, reference)))

    def void_usage(self, usage_id: str) -> Usage:
        return Usage.parse(self._send(ep.void_usage(usage_id)))

    def exchange_code(self, code: str, *, code_verifier: str, redirect_uri: str) -> LinkToken:
        return LinkToken.parse(self._send(ep.exchange_code(code, code_verifier, redirect_uri)))

    def link_status(self, link_token: str) -> LinkStatus:
        return LinkStatus.parse(self._send(ep.link_status(link_token)))

    def verify_link(self, link_token: str, *, offer_id: str | None = None) -> Verification:
        return Verification.parse(self._send(ep.verify_link(link_token, offer_id)))

    def revoke_link(self, link_token: str) -> None:
        self._send(ep.revoke_link(link_token))

    def authorize_url(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        state: str | None = None,
        locale: str | None = None,
    ) -> str:
        return ep.authorize_url(
            self.site_url,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            state=state,
            locale=locale,
        )
