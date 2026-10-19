from __future__ import annotations

import httpx
import pytest

from onemax import AsyncOneMaxClient, Mode, OneMaxClient

from .conftest import BASE, KEY, Recorder

TEST_KEY = "omx_test_abc"


def client_for(key: str, recorder: Recorder) -> OneMaxClient:
    transport = httpx.Client(transport=httpx.MockTransport(recorder.handle))
    return OneMaxClient(key, base_url=BASE, transport=transport)


def test_the_client_knows_the_mode_of_its_key(recorder: Recorder) -> None:
    assert client_for(TEST_KEY, recorder).mode is Mode.TEST
    assert client_for(f"  {TEST_KEY}  ", recorder).mode is Mode.TEST
    assert client_for(KEY, recorder).mode is Mode.LIVE
    assert client_for("omx_other_abc", recorder).mode is Mode.LIVE
    assert AsyncOneMaxClient(TEST_KEY, base_url=BASE).mode is Mode.TEST


def test_a_test_key_is_sent_as_it_is(recorder: Recorder) -> None:
    recorder.reply = (
        200,
        {
            "mode": "test",
            "active": True,
            "usable": True,
            "reason": "ok",
            "usage_id": "u-1",
            "daily_limit": 1,
        },
    )

    check = client_for(TEST_KEY, recorder).verify_code("000001")

    assert recorder.last.headers["Authorization"] == f"Bearer {TEST_KEY}"
    assert check.mode is Mode.TEST
    assert check.mode == "test"


@pytest.mark.parametrize(
    ("call", "body"),
    [
        (
            lambda client: client.context(),
            {"partner_name": "Taksi", "venue_id": "v", "venue_name": "V", "daily_limit": 1},
        ),
        (
            lambda client: client.usage("u-1"),
            {"usage_id": "u-1", "status": "pending", "created_at": "2026-10-19T10:00:00Z"},
        ),
        (
            lambda client: client.exchange_code("c", code_verifier="v", redirect_uri="r"),
            {"link_token": "omx_link_test_x", "active": True},
        ),
        (lambda client: client.link_status("omx_link_test_x"), {"linked": True, "active": False}),
    ],
)
def test_every_result_carries_the_mode_the_api_answered_in(
    client: OneMaxClient, recorder: Recorder, call, body
) -> None:
    recorder.reply = (200, body | {"mode": "live"})
    assert call(client).mode is Mode.LIVE

    recorder.reply = (200, body)
    assert call(client).mode is None

    recorder.reply = (200, body | {"mode": "staging"})
    assert call(client).mode == "staging"
