# AppConfig Architecture

VibraPilot v1.0.6.11 keeps public application configuration under `config/AppConfig/` and validates it through the read-only `src/vibrapilot/app_config.py` facade.

## Source layout

```text
config/AppConfig/
├── __init__.py
├── app.py
├── about.py
├── support.py
├── social.py
└── licensing_public.py
```

Runtime consumers import validated facade objects (`APP`, `ABOUT`, `SUPPORT`, social collections and `LICENSING`) rather than directly owning duplicate literals.

## `app.py`

Authoritative public application identity/version/owner/license/platform metadata. Current release: **1.0.6.11**.

## `about.py`, `support.py`, `social.py`

These modules continue to own About-page copy, confirmed public support/documentation endpoints and public social/community metadata. They must not contain authentication secrets.

## `licensing_public.py`

Phase-02-Step-002 adds the public Licora Secure API v2 client configuration:

- HTTPS base URL `https://mxflow.shop`
- App ID `vibrapilot`
- activate/status/refresh/deactivate API v2 paths
- expected signing key ID
- pinned **RSA public** signing key and SHA-256 fingerprint
- clock-skew policy

This file intentionally contains no Licora API v1 shared key, server private signing key, customer license, device private key or token.

The public-key fingerprint is checked both by the runtime facade/client and by `scripts/verify_repository.py`.

## Runtime and build binding

`APP_VERSION`, display/owner identity, PyInstaller build naming, `pyproject.toml`, `CITATION.cff`, `vibproject.ygit` and the documentation manifest remain synchronized with AppConfig and are verified automatically.

## Secure licensing boundary

`src/vibrapilot/licensing_v2.py` consumes only the validated public `LICENSING` object. Sensitive per-user/session values are generated or received at runtime and are protected by Windows DPAPI before persistence. The server private signing key is never a client configuration value.

## Validation contract

The facade validates required strings/sequences, numeric versions, real ISO dates, HTTPS URLs, email/social metadata, API v2 endpoint shape, public-key PEM shape, SHA-256 fingerprint syntax, protocol/App-ID consistency and clock-skew bounds. The repository verifier additionally rejects active API v1 shared-key markers and private-key material.
