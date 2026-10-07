from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest

from onemax import (
    AccessDisabledError,
    ApiError,
    AuthenticationError,
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    OneMaxClient,
    OneMaxError,
    RateLimitError,
    Reason,
    ServerError,
    TransportError,
    UsageStatus,
    __version__,
)

from .conftest import BASE, KEY, Recorder, envelope

VERIFIED = {
    "active": True,
    "usable": True,
    "reason": "ok",
    "usage_id": "u-1",
    "daily_limit": 2,
    "something_new": 1,
}
USAGE = {
    "usage_id": "u-1",
    "status": "confirmed",
    "reference": "order-7",
    "created_at": "2026-10-07T17:16:11.906636Z",
    "confirmed_at": "2026-10-07T21:16:12+04:00",
    "voided_at": None,
}


def test_every_request_carries_the_key_and_says_who_is_calling(
    client: OneMaxClient, recorder: Recorder
) -> None:
    recorder.reply = (
        200,
        {
            "partner_name": "Taksi",
            "venue_id": "v-1",
            "venue_name": "Taksi Mərkəz",
            "daily_limit": 1,
            "offers": [
                {"id": "o-1", "headline": "1+1", "title": "İkinci pulsuz", "open_now": True}
            ],
        },
    )

    context = client.context()

    assert (recorder.last.method, str(recorder.last.url)) == ("GET", f"{BASE}/integration/context")
    assert recorder.last.headers["authorization"] == f"Bearer {KEY}"
    assert recorder.last.headers["accept"] == "application/json"
    assert recorder.last.headers["user-agent"] == f"onemax-python/{__version__}"
    assert recorder.last.content == b""
    assert (context.partner_name, context.venue_name, context.daily_limit) == (
        "Taksi",
        "Taksi Mərkəz",
        1,
    )
    assert [(offer.id, offer.headline, offer.open_now) for offer in context.offers] == [
        ("o-1", "1+1", True)
    ]


def test_a_code_check_sends_only_what_was_given(client: OneMaxClient, recorder: Recorder) -> None:
    recorder.reply = (200, VERIFIED)

    plain = client.verify_code("482915")
    plain_body = recorder.sent
    client.verify_code("482915", offer_id="o-9")

    assert recorder.last.url.path == "/v1/integration/members/verify"
    assert recorder.last.headers["content-type"] == "application/json"
    assert plain_body == {"code": "482915"}
    assert recorder.sent == {"code": "482915", "offer_id": "o-9"}
    assert (plain.active, plain.usable, plain.usage_id, plain.daily_limit) == (True, True, "u-1", 2)
    assert plain.reason is Reason.OK
    assert plain.reason == "ok"


def test_a_refusal_has_no_usage_and_an_unknown_reason_is_kept(
    client: OneMaxClient, recorder: Recorder
) -> None:
    recorder.reply = (
        200,
        {
            "active": True,
            "usable": False,
            "reason": "limit_reached",
            "usage_id": None,
            "daily_limit": 1,
        },
    )
    refused = client.verify_code("482915")
    recorder.reply = (
        200,
        {"active": False, "usable": False, "reason": "paused_by_partner", "daily_limit": 1},
    )
    unknown = client.verify_code("482915")

    assert (refused.reason, refused.usage_id) == (Reason.LIMIT_REACHED, None)
    assert unknown.reason == "paused_by_partner"
    assert not isinstance(unknown.reason, Reason)
    assert unknown.usage_id is None


def test_a_usage_is_read_confirmed_and_voided(client: OneMaxClient, recorder: Recorder) -> None:
    recorder.reply = (200, USAGE)

    read = client.usage("u-1")
    read_request = recorder.last
    client.confirm_usage("u-1", reference="order-7")
    with_reference = (recorder.last.method, recorder.last.url.path, recorder.sent)
    client.confirm_usage("u-1")
    without_reference = recorder.sent
    client.void_usage("u-1")

    assert (read_request.method, read_request.url.path) == ("GET", "/v1/integration/usages/u-1")
    assert with_reference == (
        "POST",
        "/v1/integration/usages/u-1/confirm",
        {"reference": "order-7"},
    )
    assert without_reference == {}
    assert (recorder.last.method, recorder.last.url.path) == (
        "POST",
        "/v1/integration/usages/u-1/void",
    )
    assert recorder.last.content == b""
    assert read.status is UsageStatus.CONFIRMED
    assert read.reference == "order-7"
    assert read.created_at == datetime(2026, 10, 7, 17, 16, 11, 906636, tzinfo=timezone.utc)
    assert read.confirmed_at == datetime(
        2026, 10, 7, 21, 16, 12, tzinfo=timezone(timedelta(hours=4))
    )
    assert read.voided_at is None


def test_an_unknown_status_is_kept_and_a_usage_id_is_escaped(
    client: OneMaxClient, recorder: Recorder
) -> None:
    recorder.reply = (200, USAGE | {"status": "held", "reference": None, "confirmed_at": None})

    usage = client.usage("a/b c?d")

    assert recorder.last.url.raw_path == b"/v1/integration/usages/a%2Fb%20c%3Fd"
    assert usage.status == "held"
    assert not isinstance(usage.status, UsageStatus)
    assert (usage.reference, usage.confirmed_at) == (None, None)


def test_a_linking_code_is_exchanged_for_a_token(client: OneMaxClient, recorder: Recorder) -> None:
    recorder.reply = (200, {"link_token": "omx_link_abc", "active": True})

    link = client.exchange_code("the-code", code_verifier="v" * 43, redirect_uri="app://back")

    assert recorder.last.url.path == "/v1/integration/links/token"
    assert recorder.sent == {
        "code": "the-code",
        "code_verifier": "v" * 43,
        "redirect_uri": "app://back",
    }
    assert (link.link_token, link.active) == ("omx_link_abc", True)


def test_a_linked_member_is_checked_verified_and_dropped(
    client: OneMaxClient, recorder: Recorder
) -> None:
    recorder.reply = (200, {"linked": True, "active": False})
    status = client.link_status("omx_link_abc")
    status_request = (recorder.last.url.path, recorder.sent)
    recorder.reply = (200, VERIFIED | {"reason": "not_linked", "usable": False, "usage_id": None})
    verified = client.verify_link("omx_link_abc")
    plain_body = recorder.sent
    client.verify_link("omx_link_abc", offer_id="o-2")
    with_offer = (recorder.last.url.path, recorder.sent)
    recorder.reply = (200, {"ok": True})
    dropped = client.revoke_link("omx_link_abc")

    assert status_request == ("/v1/integration/links/status", {"link_token": "omx_link_abc"})
    assert (status.linked, status.active) == (True, False)
    assert plain_body == {"link_token": "omx_link_abc"}
    assert with_offer == (
        "/v1/integration/links/verify",
        {"link_token": "omx_link_abc", "offer_id": "o-2"},
    )
    assert verified.reason is Reason.NOT_LINKED
    assert (recorder.last.url.path, recorder.sent) == (
        "/v1/integration/links/revoke",
        {"link_token": "omx_link_abc"},
    )
    assert dropped is None


@pytest.mark.parametrize(
    ("status", "kind"),
    [
        (400, InvalidRequestError),
        (401, AuthenticationError),
        (403, AccessDisabledError),
        (404, NotFoundError),
        (409, ConflictError),
        (422, InvalidRequestError),
        (429, RateLimitError),
        (500, ServerError),
        (503, ServerError),
        (418, ApiError),
    ],
)
def test_each_status_raises_its_own_error(
    client: OneMaxClient, recorder: Recorder, status: int, kind: type[ApiError]
) -> None:
    recorder.reply = (status, envelope("some_code", usage_id="u-2"))

    with pytest.raises(ApiError) as caught:
        client.context()

    error = caught.value
    assert type(error) is kind
    assert isinstance(error, OneMaxError)
    assert (error.status, error.code, error.message, error.request_id) == (
        status,
        "some_code",
        "Xəta",
        "req-1",
    )
    assert error.details == {"usage_id": "u-2"}
    assert str(error) == f"{status} some_code: Xəta"


def test_a_rate_limit_says_how_long_to_wait(client: OneMaxClient, recorder: Recorder) -> None:
    recorder.reply = (429, envelope("rate_limited", retry_after=60))
    with pytest.raises(RateLimitError) as timed:
        client.context()
    recorder.reply = (429, envelope("rate_limited"))
    with pytest.raises(RateLimitError) as untimed:
        client.context()

    assert timed.value.retry_after == 60
    assert untimed.value.retry_after is None


@pytest.mark.parametrize(
    ("status", "body", "kind", "message"),
    [
        (502, "<html>Bad Gateway</html>", ServerError, "<html>Bad Gateway</html>"),
        (404, "", NotFoundError, "HTTP 404"),
        (409, '{"detail": "no envelope"}', ConflictError, '{"detail": "no envelope"}'),
        (500, "x" * 500, ServerError, "x" * 200),
    ],
)
def test_an_error_that_is_not_the_envelope_still_raises_by_status(
    client: OneMaxClient,
    recorder: Recorder,
    status: int,
    body: str,
    kind: type[ApiError],
    message: str,
) -> None:
    recorder.reply = (status, body)

    with pytest.raises(kind) as caught:
        client.context()

    assert (caught.value.code, caught.value.message) == ("unknown_error", message)
    assert caught.value.details == {}
    assert caught.value.request_id is None


@pytest.mark.parametrize(
    "failure",
    [httpx.ConnectError("refused"), httpx.ReadTimeout("slow"), httpx.ConnectTimeout("")],
)
def test_no_answer_is_a_transport_error(
    client: OneMaxClient, recorder: Recorder, failure: Exception
) -> None:
    recorder.failure = failure

    with pytest.raises(TransportError) as caught:
        client.context()

    assert caught.value.__cause__ is failure
    assert str(caught.value)
    assert not isinstance(caught.value, ApiError)


@pytest.mark.parametrize("body", ["not json", "[1, 2]", '"text"'])
def test_a_success_that_is_not_a_json_object_is_a_transport_error(
    client: OneMaxClient, recorder: Recorder, body: str
) -> None:
    recorder.reply = (200, body)

    with pytest.raises(TransportError):
        client.context()


@pytest.mark.parametrize("key", ["", "   "])
def test_an_empty_key_is_refused_at_once(key: str) -> None:
    with pytest.raises(ValueError, match="api_key"):
        OneMaxClient(key)


def test_a_trailing_slash_on_the_address_does_not_double_up(recorder: Recorder) -> None:
    recorder.reply = (200, VERIFIED)
    transport = httpx.Client(transport=httpx.MockTransport(recorder.handle))
    client = OneMaxClient(
        KEY, base_url=f"{BASE}/", site_url="https://site.test/", transport=transport
    )

    client.verify_code("482915")

    assert str(recorder.last.url) == f"{BASE}/integration/members/verify"
    assert client.authorize_url(client_id="c", redirect_uri="r", code_challenge="x").startswith(
        "https://site.test/baglanti?"
    )


def test_the_client_closes_what_it_opened() -> None:
    seen: list[Any] = []
    with OneMaxClient(KEY) as client:
        seen.append(client)

    with pytest.raises(RuntimeError):
        client.context()
    assert seen == [client]
