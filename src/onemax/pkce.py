from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass

VERIFIER_BYTES = 32


@dataclass(frozen=True)
class Pkce:
    verifier: str
    challenge: str


def _base64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def challenge_for(verifier: str) -> str:
    return _base64url(hashlib.sha256(verifier.encode("ascii")).digest())


def generate_pkce() -> Pkce:
    verifier = _base64url(secrets.token_bytes(VERIFIER_BYTES))
    return Pkce(verifier=verifier, challenge=challenge_for(verifier))
