# Changelog

## 0.1.0

First release.

- Check a member by the code on their card and record the usage: `verify_code`, `confirm_usage`,
  `void_usage`, `usage`.
- Account linking with PKCE: `generate_pkce`, `authorize_url`, `exchange_code`, `link_status`,
  `verify_link`, `revoke_link`.
- `context` to check a key and list the venue's offers.
- Sync `OneMaxClient` and async `AsyncOneMaxClient` with the same methods.
- Typed results and one error class per kind of failure.
