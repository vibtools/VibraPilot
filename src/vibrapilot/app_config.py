"""Validated read-only facade over ``config.AppConfig``.

Application consumers import this module rather than reaching into individual
configuration modules. Phase-01 intentionally exposes only non-secret product,
About, support and social metadata; licensing configuration remains unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from types import MappingProxyType
from urllib.parse import urlparse

from config.AppConfig import about as about_source
from config.AppConfig import app as app_source
from config.AppConfig import social as social_source
from config.AppConfig import support as support_source


_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:\.\d+)?$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"AppConfig {name} must be a non-empty string.")
    return value.strip()


def _optional_text(name: str, value: object) -> str:
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise RuntimeError(f"AppConfig {name} must be a string or blank.")
    return value.strip()


def _required_text_tuple(name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or not value:
        raise RuntimeError(f"AppConfig {name} must be a non-empty sequence.")
    return tuple(_required_text(f"{name}[{index}]", item) for index, item in enumerate(value))


def _optional_url(name: str, value: object) -> str:
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise RuntimeError(f"AppConfig {name} must be a string URL or blank.")
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError(f"AppConfig {name} must use an absolute HTTPS URL.")
    return value


def _optional_email(name: str, value: object) -> str:
    text = _optional_text(name, value)
    if text and not _EMAIL_RE.fullmatch(text):
        raise RuntimeError(f"AppConfig {name} must be a valid email address or blank.")
    return text


def _version(name: str, value: object) -> str:
    text = _required_text(name, value)
    if not _VERSION_RE.fullmatch(text):
        raise RuntimeError(f"AppConfig {name} must use a numeric x.y.z or x.y.z.w version.")
    return text


def _date(name: str, value: object) -> str:
    text = _required_text(name, value)
    if not _DATE_RE.fullmatch(text):
        raise RuntimeError(f"AppConfig {name} must use YYYY-MM-DD format.")
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise RuntimeError(f"AppConfig {name} must be a valid calendar date.") from exc
    return text


@dataclass(frozen=True)
class AppIdentity:
    app_id: str
    app_name: str
    display_name: str
    product_name: str
    short_name: str
    description: str
    tagline: str
    version: str
    created_date: str
    release_date: str
    updated_date: str
    status: str
    release_channel: str
    owner_name: str
    company_name: str
    developer_name: str
    author_name: str
    organization_domain: str
    copyright_holder: str
    copyright_year: int
    software_license: str
    license_identifier: str
    product_category: str
    platform: str
    supported_os: tuple[str, ...]
    supported_architecture: tuple[str, ...]
    python_runtime: str
    homepage_url: str
    repository_url: str
    target_features: tuple[str, ...]
    target_users: tuple[str, ...]
    primary_use_case: str
    product_scope: str
    authorized_use_notice: str


@dataclass(frozen=True)
class AboutInfo:
    page_title: str
    page_subtitle: str
    app_description: str
    company_title: str
    company_description: str
    company_legal_name: str
    company_display_name: str
    company_profile_description: str
    company_website_label: str
    support_team_name: str
    mission: str
    product_purpose: str
    maintainer_text: str
    legal_notice: str
    credits: tuple[str, ...]
    edition_label: str
    identity_badge: str
    design_contract_title: str
    design_contract_items: tuple[str, ...]
    license_session_title: str


@dataclass(frozen=True)
class SupportInfo:
    website_url: str
    developer_portal_url: str
    support_email: str
    help_center_url: str
    contact_url: str
    repository_url: str
    documentation_url: str
    getting_started_url: str
    user_guide_url: str
    faq_url: str
    troubleshooting_url: str
    issues_url: str
    bug_report_url: str
    feature_request_url: str
    releases_url: str
    changelog_url: str
    security_url: str
    license_url: str
    privacy_url: str
    terms_url: str
    about_support_links: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class SocialLink:
    platform: str
    display_name: str
    url: str
    enabled: bool


APP = AppIdentity(
    app_id=_required_text("APP_ID", app_source.APP_ID),
    app_name=_required_text("APP_NAME", app_source.APP_NAME),
    display_name=_required_text("DISPLAY_NAME", app_source.DISPLAY_NAME),
    product_name=_required_text("PRODUCT_NAME", app_source.PRODUCT_NAME),
    short_name=_required_text("SHORT_NAME", app_source.SHORT_NAME),
    description=_required_text("DESCRIPTION", app_source.DESCRIPTION),
    tagline=_required_text("TAGLINE", app_source.TAGLINE),
    version=_version("VERSION", app_source.VERSION),
    created_date=_date("CREATED_DATE", app_source.CREATED_DATE),
    release_date=_date("RELEASE_DATE", app_source.RELEASE_DATE),
    updated_date=_date("UPDATED_DATE", app_source.UPDATED_DATE),
    status=_required_text("STATUS", app_source.STATUS),
    release_channel=_required_text("RELEASE_CHANNEL", app_source.RELEASE_CHANNEL),
    owner_name=_required_text("OWNER_NAME", app_source.OWNER_NAME),
    company_name=_required_text("COMPANY_NAME", app_source.COMPANY_NAME),
    developer_name=_required_text("DEVELOPER_NAME", app_source.DEVELOPER_NAME),
    author_name=_required_text("AUTHOR_NAME", app_source.AUTHOR_NAME),
    organization_domain=_required_text("ORGANIZATION_DOMAIN", app_source.ORGANIZATION_DOMAIN),
    copyright_holder=_required_text("COPYRIGHT_HOLDER", app_source.COPYRIGHT_HOLDER),
    copyright_year=int(app_source.COPYRIGHT_YEAR),
    software_license=_required_text("SOFTWARE_LICENSE", app_source.SOFTWARE_LICENSE),
    license_identifier=_required_text("LICENSE_IDENTIFIER", app_source.LICENSE_IDENTIFIER),
    product_category=_required_text("PRODUCT_CATEGORY", app_source.PRODUCT_CATEGORY),
    platform=_required_text("PLATFORM", app_source.PLATFORM),
    supported_os=_required_text_tuple("SUPPORTED_OS", app_source.SUPPORTED_OS),
    supported_architecture=_required_text_tuple(
        "SUPPORTED_ARCHITECTURE", app_source.SUPPORTED_ARCHITECTURE
    ),
    python_runtime=_required_text("PYTHON_RUNTIME", app_source.PYTHON_RUNTIME),
    homepage_url=_optional_url("HOMEPAGE_URL", app_source.HOMEPAGE_URL),
    repository_url=_optional_url("REPOSITORY_URL", app_source.REPOSITORY_URL),
    target_features=_required_text_tuple("TARGET_FEATURES", app_source.TARGET_FEATURES),
    target_users=_required_text_tuple("TARGET_USERS", app_source.TARGET_USERS),
    primary_use_case=_required_text("PRIMARY_USE_CASE", app_source.PRIMARY_USE_CASE),
    product_scope=_required_text("PRODUCT_SCOPE", app_source.PRODUCT_SCOPE),
    authorized_use_notice=_required_text(
        "AUTHORIZED_USE_NOTICE", app_source.AUTHORIZED_USE_NOTICE
    ),
)

ABOUT = AboutInfo(
    page_title=_required_text("ABOUT_PAGE_TITLE", about_source.ABOUT_PAGE_TITLE),
    page_subtitle=_required_text("ABOUT_PAGE_SUBTITLE", about_source.ABOUT_PAGE_SUBTITLE),
    app_description=_required_text("ABOUT_APP_DESCRIPTION", about_source.ABOUT_APP_DESCRIPTION),
    company_title=_required_text("ABOUT_COMPANY_TITLE", about_source.ABOUT_COMPANY_TITLE),
    company_description=_required_text(
        "ABOUT_COMPANY_DESCRIPTION", about_source.ABOUT_COMPANY_DESCRIPTION
    ),
    company_legal_name=_optional_text("COMPANY_LEGAL_NAME", about_source.COMPANY_LEGAL_NAME),
    company_display_name=_required_text(
        "COMPANY_DISPLAY_NAME", about_source.COMPANY_DISPLAY_NAME
    ),
    company_profile_description=_required_text(
        "COMPANY_DESCRIPTION", about_source.COMPANY_DESCRIPTION
    ),
    company_website_label=_required_text(
        "COMPANY_WEBSITE_LABEL", about_source.COMPANY_WEBSITE_LABEL
    ),
    support_team_name=_optional_text("SUPPORT_TEAM_NAME", about_source.SUPPORT_TEAM_NAME),
    mission=_required_text("MISSION", about_source.MISSION),
    product_purpose=_required_text("PRODUCT_PURPOSE", about_source.PRODUCT_PURPOSE),
    maintainer_text=_required_text("MAINTAINER_TEXT", about_source.MAINTAINER_TEXT),
    legal_notice=_required_text("LEGAL_NOTICE", about_source.LEGAL_NOTICE),
    credits=_required_text_tuple("CREDITS", about_source.CREDITS),
    edition_label=_required_text("EDITION_LABEL", about_source.EDITION_LABEL),
    identity_badge=_required_text("IDENTITY_BADGE", about_source.IDENTITY_BADGE),
    design_contract_title=_required_text(
        "DESIGN_CONTRACT_TITLE", about_source.DESIGN_CONTRACT_TITLE
    ),
    design_contract_items=_required_text_tuple(
        "DESIGN_CONTRACT_ITEMS", about_source.DESIGN_CONTRACT_ITEMS
    ),
    license_session_title=_required_text(
        "LICENSE_SESSION_TITLE", about_source.LICENSE_SESSION_TITLE
    ),
)

_SUPPORT_URL_NAMES = (
    "WEBSITE_URL", "DEVELOPER_PORTAL_URL", "HELP_CENTER_URL", "CONTACT_URL",
    "REPOSITORY_URL", "DOCUMENTATION_URL", "GETTING_STARTED_URL", "USER_GUIDE_URL",
    "FAQ_URL", "TROUBLESHOOTING_URL", "ISSUES_URL", "BUG_REPORT_URL",
    "FEATURE_REQUEST_URL", "RELEASES_URL", "CHANGELOG_URL", "SECURITY_URL",
    "LICENSE_URL", "PRIVACY_URL", "TERMS_URL",
)
_support_urls = {
    name: _optional_url(name, getattr(support_source, name)) for name in _SUPPORT_URL_NAMES
}

SUPPORT = SupportInfo(
    website_url=_support_urls["WEBSITE_URL"],
    developer_portal_url=_support_urls["DEVELOPER_PORTAL_URL"],
    support_email=_optional_email("SUPPORT_EMAIL", support_source.SUPPORT_EMAIL),
    help_center_url=_support_urls["HELP_CENTER_URL"],
    contact_url=_support_urls["CONTACT_URL"],
    repository_url=_support_urls["REPOSITORY_URL"],
    documentation_url=_support_urls["DOCUMENTATION_URL"],
    getting_started_url=_support_urls["GETTING_STARTED_URL"],
    user_guide_url=_support_urls["USER_GUIDE_URL"],
    faq_url=_support_urls["FAQ_URL"],
    troubleshooting_url=_support_urls["TROUBLESHOOTING_URL"],
    issues_url=_support_urls["ISSUES_URL"],
    bug_report_url=_support_urls["BUG_REPORT_URL"],
    feature_request_url=_support_urls["FEATURE_REQUEST_URL"],
    releases_url=_support_urls["RELEASES_URL"],
    changelog_url=_support_urls["CHANGELOG_URL"],
    security_url=_support_urls["SECURITY_URL"],
    license_url=_support_urls["LICENSE_URL"],
    privacy_url=_support_urls["PRIVACY_URL"],
    terms_url=_support_urls["TERMS_URL"],
    about_support_links=tuple(
        (_required_text("support link label", label), _optional_url("support link URL", url))
        for label, url in support_source.ABOUT_SUPPORT_LINKS
    ),
)

_social_links: list[SocialLink] = []
_seen_platforms: set[str] = set()
for raw in social_source.SOCIAL_LINKS:
    if not isinstance(raw, dict):
        raise RuntimeError("AppConfig SOCIAL_LINKS entries must be dictionaries.")
    platform = _required_text("social platform", raw.get("platform"))
    key = platform.casefold()
    if key in _seen_platforms:
        raise RuntimeError(f"AppConfig duplicate social platform: {platform}")
    _seen_platforms.add(key)
    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        raise RuntimeError(f"AppConfig social enabled flag must be boolean: {platform}")
    url = _optional_url("social URL", raw.get("url"))
    if enabled and not url:
        raise RuntimeError(f"AppConfig enabled social profile requires a URL: {platform}")
    _social_links.append(
        SocialLink(
            platform=platform,
            display_name=_required_text("social display_name", raw.get("display_name")),
            url=url,
            enabled=enabled,
        )
    )
SOCIAL_LINKS = tuple(_social_links)
ENABLED_SOCIAL_LINKS = tuple(link for link in SOCIAL_LINKS if link.enabled)
SOCIAL_BY_PLATFORM = MappingProxyType({link.platform.casefold(): link for link in SOCIAL_LINKS})

__all__ = [
    "APP", "ABOUT", "SUPPORT", "SOCIAL_LINKS", "ENABLED_SOCIAL_LINKS",
    "SOCIAL_BY_PLATFORM", "AppIdentity", "AboutInfo", "SupportInfo", "SocialLink",
]
