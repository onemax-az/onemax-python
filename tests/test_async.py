from __future__ import annotations

import inspect

import httpx
import pytest

from onemax import (
    AsyncOneMaxClient,
    ConflictError,
    OneMaxClient,
    Reason,
    TransportError,
    UsageStatus,
)

from .conftest import KEY, Recorder, envelope
from .test_client import USAGE, VERIFIED


def public(kind: type) -> dict[str, inspect.Signature]:
    return {
        name: inspect.signature(member)
        for name, member in inspect.getmembers(kind, inspect.isfunction)
        if not name.startswith("_") and name not in {"close", "aclose"}
    }


def test_both_clients_offer_the_same_methods_with_the_same_arguments() -> None:
    assert public(AsyncOneMaxClient) == public(OneMaxClient)


async def test_the_async_client_runs_the_code_flow(
    async_client: AsyncOneMaxClient, recorder: Recorder
) -> None:
    recorder.reply = (200, VERIFIED)
    check = await async_client.verify_code("482915", offer_id="o-1")
    verify_body = recorder.sent
    recorder.reply = (200, USAGE)
    usage = await async_client.confirm_usage("u-1", reference="order-7")
    confirm = (recorder.last.url.path, recorder.sent)
    read = await async_client.usage("u-1")
    await async_client.void_usage("u-1")

    assert verify_body == {"code": "482915", "offer_id": "o-1"}
    assert check.reason is Reason.OK
    assert confirm == ("/v1/integration/usages/u-1/confirm", {"reference": "order-7"})
    assert usage.status is UsageStatus.CONFIRMED
    assert read.usage_id == "u-1"
    assert recorder.last.url.path == "/v1/integration/usages/u-1/void"
    assert recorder.last.headers["authorization"] == f"Bearer {KEY}"


async def test_the_async_client_runs_the_linking_flow(
    async_client: AsyncOneMaxClient, recorder: Recorder
) -> None:
    recorder.reply = (
        200,
        {"partner_name": "T", "venue_id": "v", "venue_name": "V", "daily_limit": 1},
    )
    context = await async_client.context()
    recorder.reply = (200, {"link_token": "omx_link_abc", "active": True})
    link = await async_client.exchange_code("c", code_verifier="v" * 43, redirect_uri="app://b")
    recorder.reply = (200, {"linked": True, "active": True})
    status = await async_client.link_status(link.link_token)
    recorder.reply = (200, VERIFIED)
    check = await async_client.verify_link(link.link_token)
    recorder.reply = (200, {"ok": True})
    dropped = await async_client.revoke_link(link.link_token)

    assert context.offers == ()
    assert (status.linked, status.active, check.usable) == (True, True, True)
    assert recorder.last.url.path == "/v1/integration/links/revoke"
    assert dropped is None
    assert async_client.authorize_url(
        client_id="c", redirect_uri="app://b", code_challenge="x", locale="ru"
    ).startswith("https://onemax.az/ru/baglanti?")


async def test_the_async_client_raises_the_same_errors(
    async_client: AsyncOneMaxClient, recorder: Recorder
) -> None:
    recorder.reply = (409, envelope("usage_limit_reached"))
    with pytest.raises(ConflictError) as refused:
        await async_client.confirm_usage("u-1")
    recorder.failure = httpx.ConnectError("refused")
    with pytest.raises(TransportError):
        await async_client.context()

    assert refused.value.code == "usage_limit_reached"


async def test_the_async_client_closes_what_it_opened() -> None:
    async with AsyncOneMaxClient(KEY) as client:
        pass

    with pytest.raises(RuntimeError):
        await client.context()
