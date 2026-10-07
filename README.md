# onemax

Python client for the [OneMax](https://onemax.az) partner API.

OneMax is a 1+1 membership club in Baku. Members pay for a plan and show a code at the counter to
use a partner's offer. This library lets a partner's own system do what the counter does: check
that someone is a member and record that they used the offer.

Sync and async, fully typed, one dependency.

```bash
pip install onemax
```

## Getting a key

1. OneMax switches API access on for your business.
2. The owner opens the partner panel, goes to API and creates a key.
3. The key is shown once. It belongs to one venue and acts there like a cashier.

Keep the key on your server. It must never reach a browser or a mobile app.

## Quick start: a member's code

A member opens their OneMax card and reads you the six digit code.

```python
from onemax import OneMaxClient

client = OneMaxClient("omx_live_...")

check = client.verify_code("482915")
if not check.usable:
    print("No discount:", check.reason)
else:
    order = place_order(discounted=True)
    client.confirm_usage(check.usage_id, reference=order.id)
```

`verify_code` only answers the question. Nothing counts against the member until you call
`confirm_usage`. If the order falls through, call `void_usage(check.usage_id)` instead.

Pass your own order id as `reference`. Confirming again with the same reference returns the same
usage, so a retried request is safe.

## Account linking

A member links their OneMax account to your app once. After that you check them without a code.
Linking is the OAuth 2.0 authorization code flow with PKCE, so the same steps work for a website
and a mobile app.

Register the addresses your app may return to in the partner panel, under API, Account linking.
Your client id is shown there.

**1. Send the member to the permission page.**

```python
from onemax import generate_pkce

pkce = generate_pkce()
session["onemax_verifier"] = pkce.verifier

url = client.authorize_url(
    client_id="omx_client_...",
    redirect_uri="https://example.az/onemax/return",
    code_challenge=pkce.challenge,
    state=session_id,
)
```

In a mobile app, open `url` in the system browser and use your app link as the `redirect_uri`,
for example `taksi://onemax/return`.

**2. The member returns to your address** with `code` and `state`, or with `error=access_denied`
if they declined. Check that `state` is the one you sent.

**3. Exchange the code on your server and store the token.**

```python
link = client.exchange_code(
    code,
    code_verifier=session["onemax_verifier"],
    redirect_uri="https://example.az/onemax/return",
)
save(user_id, link.link_token)
```

The code works once and for five minutes.

**4. Check the member whenever you need to.**

```python
status = client.link_status(link_token)
if not status.linked:
    forget(user_id)

check = client.verify_link(link_token)
if check.usable:
    client.confirm_usage(check.usage_id, reference=order.id)
```

A member can unlink at any time in their OneMax profile. From then on `link_status` answers
`linked=False` and `verify_link` answers `reason="not_linked"`. Neither raises.

You learn only whether the subscription is active. The member's name, email, phone and photo are
never shared.

## Async

`AsyncOneMaxClient` has the same methods, awaited:

```python
from onemax import AsyncOneMaxClient

async with AsyncOneMaxClient("omx_live_...") as client:
    check = await client.verify_code("482915")
```

## Results

`verify_code` and `verify_link` return a `Verification`:

| Field | Meaning |
| --- | --- |
| `active` | The member has a subscription that works today |
| `usable` | They may use the offer right now |
| `reason` | Why, as a `Reason` |
| `usage_id` | Set when `usable` is true. Confirm it or void it |
| `daily_limit` | How many times a day a member may use this venue |

| `Reason` | Meaning |
| --- | --- |
| `OK` | Go ahead |
| `NOT_SUBSCRIBED` | No subscription, or it has ended |
| `LIMIT_REACHED` | The member already used today's allowance at this venue |
| `OFFER_UNAVAILABLE` | The venue or the offer is not open right now |
| `INVALID_CODE` | The code is wrong, expired or already used |
| `NOT_LINKED` | The link token no longer works |

`Reason` and `UsageStatus` are string enums, so `check.reason == "ok"` works as well. A value this
version does not know is returned as a plain string.

If a venue has several offers open, pass `offer_id`. `client.context()` lists them.

## Errors

Everything the library raises is a `OneMaxError`.

| Class | When |
| --- | --- |
| `TransportError` | No usable answer: a connection failure, a timeout, or a body that is not JSON |
| `ApiError` | The API answered with an error. Has `status`, `code`, `message`, `details`, `request_id` |
| `AuthenticationError` | 401. The key is missing, wrong or switched off |
| `AccessDisabledError` | 403. API access is switched off for the partner |
| `NotFoundError` | 404. No such usage for this key |
| `ConflictError` | 409. For example `usage_limit_reached`, `already_applied`, `reference_used` |
| `InvalidRequestError` | 400 or 422. For example `offer_required`, `link_code_invalid` |
| `RateLimitError` | 429. Has `retry_after` in seconds |
| `ServerError` | 500 and above |

```python
from onemax import ConflictError, OneMaxError

try:
    client.confirm_usage(usage_id, reference=order.id)
except ConflictError as error:
    if error.code == "usage_limit_reached":
        charge_full_price(order)
    else:
        raise
except OneMaxError:
    retry_later(order)
```

`message` is in Azerbaijani and meant for your logs. Decide on `code`.

## Limits

- The member's daily limit applies exactly as it does at a counter.
- 120 requests a minute per key.
- The library never retries by itself. `confirm_usage` with a `reference` is safe to retry.

## Development

```bash
uv sync
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
```

## License

MIT
