#!/usr/bin/env python3
"""PR-12 WiX ICE64-safe GitHub Actions packaging entry point.

The frozen core build.py pipeline remains unchanged. This adapter augments only
its generated WiX file fragment with uninstall rows for per-user directories.
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import build as core


def _payload_directories(payload_root: Path) -> list[str]:
    """Return every unique non-root payload directory, including ancestors."""
    directories: set[str] = set()
    for file_path in sorted(p for p in payload_root.rglob("*") if p.is_file()):
        parent = file_path.relative_to(payload_root).parent
        while parent != Path("."):
            directories.add(parent.as_posix())
            parent = parent.parent
    return sorted(directories, key=lambda value: (value.count("/"), value.casefold(), value))


def _cleanup_component_lines(payload_root: Path) -> list[str]:
    """Create deterministic empty-folder-only uninstall authoring for ICE64."""
    cleanup: list[str] = []

    static_key = "static-profile-directories"
    cleanup.extend(
        [
            f'      <Component Id="{core._wix_id("DirCmp", static_key)}" Guid="{core._component_guid("directory:" + static_key)}" Directory="INSTALLFOLDER">',
            f'        <RemoveFolder Id="{core._wix_id("Rmf", "INSTALLFOLDER")}" Directory="INSTALLFOLDER" On="uninstall" />',
            f'        <RemoveFolder Id="{core._wix_id("Rmf", "VibToolsFolder")}" Directory="VibToolsFolder" On="uninstall" />',
            f'        <RemoveFolder Id="{core._wix_id("Rmf", "PerUserProgramFilesFolder")}" Directory="PerUserProgramFilesFolder" On="uninstall" />',
            f'        <RegistryValue Root="HKCU" Key="{core.INSTALLER_REGISTRY_KEY}" Name="{core._wix_id("dircmp", static_key)}" Type="integer" Value="1" KeyPath="yes" />',
            "      </Component>",
        ]
    )

    for relative in _payload_directories(payload_root.resolve()):
        relative_win = escape(relative.replace("/", "\\"))
        cleanup.extend(
            [
                f'      <Component Id="{core._wix_id("DirCmp", relative)}" Guid="{core._component_guid("directory:" + relative)}" Directory="INSTALLFOLDER" Subdirectory="{relative_win}">',
                f'        <RemoveFolder Id="{core._wix_id("Rmf", relative)}" On="uninstall" />',
                f'        <RegistryValue Root="HKCU" Key="{core.INSTALLER_REGISTRY_KEY}" Name="{core._wix_id("dircmp", relative)}" Type="integer" Value="1" KeyPath="yes" />',
                "      </Component>",
            ]
        )
    return cleanup


def _augment_generated_wix(payload_root: Path, generated: Path) -> Path:
    """Add ICE64 RemoveFile-table rows without deleting user/runtime content.

    WiX RemoveFolder maps to the MSI RemoveFile table with a null FileName and
    therefore removes a directory only when it is empty. No wildcard file
    removal and no recursive RemoveFolderEx authoring is used.
    """
    text = generated.read_text(encoding="utf-8")
    marker = "    </ComponentGroup>"
    if text.count(marker) != 1:
        raise core.BuildError("Unexpected generated WiX ComponentGroup structure.")
    cleanup = _cleanup_component_lines(payload_root)
    replacement = "\n".join(cleanup) + "\n" + marker
    generated.write_text(text.replace(marker, replacement, 1), encoding="utf-8", newline="\n")
    return generated


def _install_ice64_safe_generator() -> None:
    original = core.generate_wix_file_fragment

    def generate(payload_root: Path, destination: Path) -> Path:
        generated = original(payload_root, destination)
        return _augment_generated_wix(payload_root, generated)

    core.generate_wix_file_fragment = generate


def main() -> int:
    _install_ice64_safe_generator()
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
