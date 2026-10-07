from __future__ import annotations

from urllib.parse import parse_qsl, urlsplit

import pytest

from onemax import OneMaxClient, Pkce, challenge_for, generate_pkce

from .conftest import KEY

RETURN = "https://taksi.example/onemax/geri?kanal=veb&x=a b"


def test_the_challenge_matches_the_reference_vector() -> None:
    assert (
        challenge_for("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk")
        == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    )


def test_a_generated_pair_is_fresh_well_formed_and_consistent() -> None:
    first, second = generate_pkce(), generate_pkce()

    assert isinstance(first, Pkce)
    assert len(first.verifier) == 43
    assert len(first.challenge) == 43
    assert set(first.verifier + first.challenge) <= set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    )
    assert first.challenge == challenge_for(first.verifier)
    assert first.verifier != second.verifier


@pytest.mark.parametrize(
    ("locale", "page"),
    [
        (None, "https://onemax.az/baglanti"),
        ("az", "https://onemax.az/baglanti"),
        ("ru", "https://onemax.az/ru/baglanti"),
        ("en", "https://onemax.az/en/baglanti"),
    ],
)
def test_the_permission_page_address_is_built_per_language(locale: str | None, page: str) -> None:
    client = OneMaxClient(KEY)

    url = client.authorize_url(
        client_id="omx_client_abc",
        redirect_uri=RETURN,
        code_challenge="the-challenge",
        state="s 1&2",
        locale=locale,
    )

    parts = urlsplit(url)
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == page
    assert parse_qsl(parts.query) == [
        ("response_type", "code"),
        ("client_id", "omx_client_abc"),
        ("redirect_uri", RETURN),
        ("code_challenge", "the-challenge"),
        ("code_challenge_method", "S256"),
        ("state", "s 1&2"),
    ]
    assert " " not in url


def test_state_is_left_out_when_not_given_and_an_unknown_language_is_refused() -> None:
    client = OneMaxClient(KEY, site_url="https://site.test")

    url = client.authorize_url(client_id="c", redirect_uri="app://back", code_challenge="x")

    assert url.startswith("https://site.test/baglanti?response_type=code&client_id=c&")
    assert "state" not in dict(parse_qsl(urlsplit(url).query))
    assert dict(parse_qsl(urlsplit(url).query))["redirect_uri"] == "app://back"
    with pytest.raises(ValueError, match="locale"):
        client.authorize_url(
            client_id="c", redirect_uri="app://back", code_challenge="x", locale="de"
        )
