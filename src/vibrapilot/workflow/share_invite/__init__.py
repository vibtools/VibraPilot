"""Built-in Share Invite workflow package.

PR-04 moves the verified Share Invite implementation behind the built-in
workflow boundary without enabling workflow switching or external plugins.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..contracts import WorkflowManifest

_MANIFEST_PATH = Path(__file__).with_name("manifest.json")


def load_manifest() -> WorkflowManifest:
    """Load the source-controlled Share Invite metadata from its fixed package path."""
    payload = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Share Invite manifest root must be an object")
    return WorkflowManifest(**payload)


SHARE_INVITE_MANIFEST = load_manifest()

from .workflow import ShareInviteRuntimeErrors, ShareInviteWorkflow

__all__ = [
    "SHARE_INVITE_MANIFEST",
    "ShareInviteRuntimeErrors",
    "ShareInviteWorkflow",
    "load_manifest",
]
