"""Authoritative internal application metadata for VibraPilot.

Phase-01 contains public/non-secret product, About, support and social metadata.
Licensing transport/security configuration is intentionally reserved for Phase-02.
"""

from . import about, app, social, support

__all__ = ["app", "about", "support", "social"]
