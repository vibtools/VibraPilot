# AppConfig Architecture

VibraPilot Phase-01 centralizes public, non-secret application metadata under `config/AppConfig/`.
The objective is to provide one authoritative source for product identity, About-page content,
public support/documentation URLs and social/community links without changing the validated
browser-automation, task-processing, safety or Licora licensing behavior.

## Source layout

```text
config/
├── AppConfig/
│   ├── __init__.py
│   ├── app.py
│   ├── about.py
│   ├── support.py
│   └── social.py
├── settings.defaults.json
└── verification/
```

`src/vibrapilot/app_config.py` is the validated read-only application facade. Runtime consumers
should import `APP`, `ABOUT`, `SUPPORT` and the validated social-link collections from that facade
instead of importing individual configuration modules directly.

## `app.py`

`app.py` is the authoritative source for public application identity and product metadata,
including:

- application ID, product/display/short names;
- description and tagline;
- current version and documented lifecycle dates;
- owner, company, developer and organization identity;
- software-license metadata;
- platform/runtime metadata;
- homepage and repository URLs; and
- target features, target users, primary use case and authorized-use notice.

The verified Phase-01 configuration baseline is `1.0.6.2`. This release completes and validates the configuration layer without changing the validated automation runtime behavior.

## `about.py`

`about.py` owns About-page presentation copy and the existing Vib Tools design-contract summary.
Application identity is not duplicated there; the UI combines About content with the authoritative
identity from `app.py` through the central facade.

## `support.py`

`support.py` contains public, confirmed product/company support and documentation endpoints. The official Vib Tools support address and contact page are configured; fields without an authoritative endpoint remain blank. The project does not invent placeholder support URLs or addresses.

## `social.py`

`social.py` contains public social/community profile metadata only. It must never contain OAuth
secrets, API tokens, passwords, webhook credentials or other private authentication material.
Only enabled and validated entries are exposed to the About page. The v1.0.6.2 baseline includes the public profiles linked by the official Vib Tools website: GitHub, X, Facebook, Instagram, Reddit, TikTok and GitLab.

## Runtime and build binding

The runtime keeps its established compatibility constants (`APP_NAME`, `APP_VERSION`,
`DISPLAY_APP_NAME`, `APP_AUTHOR`, `RELEASE_DATE`), but those names are aliases to `APP` rather than
independent hard-coded sources. The Windows builder similarly imports application name/version from
`config.AppConfig.app`.

Static packaging/documentation metadata such as `pyproject.toml`, `CITATION.cff`,
`vibproject.ygit` and `docs/docs.manifest.ygit` cannot all consume Python runtime objects directly.
They therefore remain static mirrors, and repository verification enforces identity/version/license
consistency against the authoritative AppConfig values.

## Licensing boundary

Phase-01 does **not** move or redesign licensing configuration. The current Licora URL/API-key
contract and all `LicenseManager` request/validation behavior remain unchanged. Secure public
licensing configuration and Licora API v2 are explicitly reserved for Phase-02.

No Licora API key, API base URL or verification endpoint is stored in `config/AppConfig/` during
Phase-01.

## Repository documentation policy

Public configuration documentation belongs under `docs/`. Private baseline freezes,
implementation notes and forensic development records belong under the gitignored `project/`
workspace and are never required by CI.

## Validation contract

`src/vibrapilot/app_config.py` fails closed for malformed Phase-01 configuration. It validates required strings and string sequences, numeric three/four-segment versions, real ISO calendar dates, absolute HTTPS URLs, optional support email format, duplicate social platforms, strict boolean social enabled flags and required URLs for enabled social profiles.

The repository verifier additionally enforces static metadata parity and confirms that Phase-02 licensing transport constants do not enter `config/AppConfig/`.
