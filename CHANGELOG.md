# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-02

### Added
- Initial release of the official Hellio Messaging Python SDK.
- `Hellio` client with Bearer-token auth, configurable base URL and timeout,
  and environment-variable fallbacks (`HELLIO_API_TOKEN`, `HELLIO_BASE_URL`,
  `HELLIO_DEFAULT_SENDER`).
- Methods: `balance`, `pricing`, `sms`, `message`, `campaign`, `otp`,
  `verify_otp`, `verify`, `voice`, `voice_status`, `lookup`, `lookups`,
  `lookup_result`, `verify_email`, `webhooks`, `create_webhook`,
  `delete_webhook`.
- Recipient normalization (string, comma-separated string, or list).
- Typed exception hierarchy mapped by HTTP status: `HellioError`,
  `InvalidApiTokenError` (401), `InsufficientBalanceError` (402),
  `ValidationError` (422), `RateLimitError` (429).
- Injectable `httpx.Client` for testing.
- Full type hints and a `py.typed` marker.
