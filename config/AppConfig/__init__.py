"""Authoritative internal application metadata for VibraPilot.

Phase-02 adds public Licora Secure API v2 transport and server-signing metadata.
No shared API key or private signing material is stored in AppConfig.
"""

from . import about, app, licensing_public, social, support

__all__ = ["app", "about", "support", "social", "licensing_public"]
