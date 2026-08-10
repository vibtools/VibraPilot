"""Authoritative VibraPilot application identity and product metadata.

This module contains public/non-secret application metadata only. Secure licensing transport is defined separately in licensing_public.py;
this identity module remains public/non-secret metadata only.
"""

APP_ID = "vibrapilot"
APP_NAME = "VibraPilot"
DISPLAY_NAME = "VibraPilot"
PRODUCT_NAME = "VibraPilot"
SHORT_NAME = "VP"
DESCRIPTION = "VibraPilot browser automation desktop application by Vib Tools."
TAGLINE = "Authorized browser automation desktop application."

VERSION = "1.0.6.24"
CREATED_DATE = "2026-08-07"
RELEASE_DATE = "2026-08-10"
UPDATED_DATE = "2026-08-10"
STATUS = "development"
RELEASE_CHANNEL = "production"

OWNER_NAME = "Vib Tools"
COMPANY_NAME = "Vib Tools"
DEVELOPER_NAME = "Vib Tools Core Team"
AUTHOR_NAME = "Vib Tools"
ORGANIZATION_DOMAIN = "vib.tools"
COPYRIGHT_HOLDER = "Vib Tools contributors"
COPYRIGHT_YEAR = 2026

SOFTWARE_LICENSE = "GNU General Public License v3.0 only"
LICENSE_IDENTIFIER = "GPL-3.0-only"
PRODUCT_CATEGORY = "desktop-application"
PLATFORM = "Windows desktop"
SUPPORTED_OS = ("Windows",)
SUPPORTED_ARCHITECTURE = ("x64",)
PYTHON_RUNTIME = "3.12"

HOMEPAGE_URL = "https://vib.tools/"
REPOSITORY_URL = "https://github.com/vibtools/VibraPilot"

TARGET_FEATURES = (
    "authorized browser automation",
    "data-driven task processing",
    "Playwright browser runtime controls",
    "task reporting and operational logs",
    "reusable workflow-framework foundation",
)
TARGET_USERS = (
    "authorized operators",
    "developers",
    "QA and testing teams",
    "workflow automation users",
)
PRIMARY_USE_CASE = "Authorized browser automation and data-driven task processing."
PRODUCT_SCOPE = (
    "Desktop automation application preserving the validated v1.0.6 automation runtime "
    "while using the Phase-02 Secure Licora API v2 device-bound licensing layer and "
    "preserving the validated automation/workflow foundation."
)
AUTHORIZED_USE_NOTICE = "Use only for authorized testing and automation workflows."
