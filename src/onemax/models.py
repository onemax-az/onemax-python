from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar


class Reason(str, Enum):
    OK = "ok"
    NOT_SUBSCRIBED = "not_subscribed"
    LIMIT_REACHED = "limit_reached"
    OFFER_UNAVAILABLE = "offer_unavailable"
    INVALID_CODE = "invalid_code"
    NOT_LINKED = "not_linked"

    def __str__(self) -> str:
        return self.value


class UsageStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    VOIDED = "voided"

    def __str__(self) -> str:
        return self.value


Known = TypeVar("Known", bound=Enum)


def _known(kind: type[Known], value: Any) -> Known | str:
    text = str(value)
    try:
        return kind(text)
    except ValueError:
        return text


def _moment(value: Any) -> datetime:
    text = str(value)
    return datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)


def _maybe_moment(value: Any) -> datetime | None:
    return None if value is None else _moment(value)


def _maybe_text(value: Any) -> str | None:
    return None if value is None else str(value)


@dataclass(frozen=True)
class Offer:
    id: str
    headline: str
    title: str
    open_now: bool

    @classmethod
    def parse(cls, body: dict[str, Any]) -> Offer:
        return cls(
            id=str(body["id"]),
            headline=str(body["headline"]),
            title=str(body["title"]),
            open_now=bool(body["open_now"]),
        )


@dataclass(frozen=True)
class Context:
    partner_name: str
    venue_id: str
    venue_name: str
    daily_limit: int
    offers: tuple[Offer, ...]

    @classmethod
    def parse(cls, body: dict[str, Any]) -> Context:
        return cls(
            partner_name=str(body["partner_name"]),
            venue_id=str(body["venue_id"]),
            venue_name=str(body["venue_name"]),
            daily_limit=int(body["daily_limit"]),
            offers=tuple(Offer.parse(item) for item in body.get("offers") or ()),
        )


@dataclass(frozen=True)
class Verification:
    active: bool
    usable: bool
    reason: Reason | str
    usage_id: str | None
    daily_limit: int

    @classmethod
    def parse(cls, body: dict[str, Any]) -> Verification:
        return cls(
            active=bool(body["active"]),
            usable=bool(body["usable"]),
            reason=_known(Reason, body["reason"]),
            usage_id=_maybe_text(body.get("usage_id")),
            daily_limit=int(body["daily_limit"]),
        )


@dataclass(frozen=True)
class Usage:
    usage_id: str
    status: UsageStatus | str
    reference: str | None
    created_at: datetime
    confirmed_at: datetime | None
    voided_at: datetime | None

    @classmethod
    def parse(cls, body: dict[str, Any]) -> Usage:
        return cls(
            usage_id=str(body["usage_id"]),
            status=_known(UsageStatus, body["status"]),
            reference=_maybe_text(body.get("reference")),
            created_at=_moment(body["created_at"]),
            confirmed_at=_maybe_moment(body.get("confirmed_at")),
            voided_at=_maybe_moment(body.get("voided_at")),
        )


@dataclass(frozen=True)
class LinkToken:
    link_token: str
    active: bool

    @classmethod
    def parse(cls, body: dict[str, Any]) -> LinkToken:
        return cls(link_token=str(body["link_token"]), active=bool(body["active"]))


@dataclass(frozen=True)
class LinkStatus:
    linked: bool
    active: bool

    @classmethod
    def parse(cls, body: dict[str, Any]) -> LinkStatus:
        return cls(linked=bool(body["linked"]), active=bool(body["active"]))
