# Changelog

## 0.2.0

- Test mode. A key that starts with `omx_test_` works against OneMax test members on the same
  address, so an integration can be built and tried before a real member is involved.
- `client.mode` says whether the client holds a live or a test key, as a `Mode`.
- `Context`, `Verification`, `Usage`, `LinkToken` and `LinkStatus` carry `mode`, the mode the API
  answered in. It is `None` when talking to a server that does not send it.

## 0.1.1

Packaging only, no library changes since 0.1.0. First release published through trusted
publishing, with no token stored in the repository.

## 0.1.0

First release.

- Check a member by the code on their card and record the usage: `verify_code`, `confirm_usage`,
  `void_usage`, `usage`.
- Account linking with PKCE: `generate_pkce`, `authorize_url`, `exchange_code`, `link_status`,
  `verify_link`, `revoke_link`.
- `context` to check a key and list the venue's offers.
- Sync `OneMaxClient` and async `AsyncOneMaxClient` with the same methods.
- Typed results and one error class per kind of failure.
