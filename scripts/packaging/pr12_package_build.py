#!/usr/bin/env python3
"""PR-12 Cycle-2 WiX ICE64-safe GitHub Actions packaging entry point.

The frozen core build.py pipeline remains unchanged. This adapter replaces only
its generated WiX payload fragment so every packaged file component and its
uninstall cleanup component reference the exact same explicit Directory Id.
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


def _directory_id(relative: str) -> str:
    """Return the deterministic WiX Directory Id for one payload directory."""
    return core._wix_id("Dir", relative)


def _directory_tree_lines(payload_root: Path) -> list[str]:
    """Author one explicit deterministic WiX Directory tree below INSTALLFOLDER."""
    directories = _payload_directories(payload_root)
    if not directories:
        return []

    children: dict[tuple[str, ...], set[str]] = {}
    for relative in directories:
        parts = tuple(Path(relative).parts)
        for index, name in enumerate(parts):
            parent = parts[:index]
            children.setdefault(parent, set()).add(name)

    lines = ['    <DirectoryRef Id="INSTALLFOLDER">']

    def emit(parent: tuple[str, ...], indent: str) -> None:
        for name in sorted(children.get(parent, set()), key=lambda value: (value.casefold(), value)):
            current = parent + (name,)
            relative = "/".join(current)
            lines.append(
                f'{indent}<Directory Id="{_directory_id(relative)}" Name="{escape(name)}">'
            )
            emit(current, indent + "  ")
            lines.append(f"{indent}</Directory>")

    emit((), "      ")
    lines.append("    </DirectoryRef>")
    return lines


def _file_component_lines(payload_root: Path) -> list[str]:
    """Author file components against explicit Directory identities only."""
    payload_root = payload_root.resolve()
    files = sorted(p for p in payload_root.rglob("*") if p.is_file())
    if not files:
        raise core.BuildError("MSI payload is empty.")

    lines: list[str] = []
    for file_path in files:
        rel = file_path.relative_to(payload_root).as_posix()
        rel_win = escape(rel.replace("/", "\\"))
        parent = Path(rel).parent.as_posix()
        directory_id = "INSTALLFOLDER" if parent == "." else _directory_id(parent)
        cid = core._wix_id("Cmp", rel)
        fid = core._wix_id("Fil", rel)
        reg_name = core._wix_id("cmp", rel)
        lines.extend(
            [
                f'      <Component Id="{cid}" Guid="{core._component_guid(rel)}" Directory="{directory_id}">',
                f'        <File Id="{fid}" Source="!(bindpath.PayloadRoot)\\{rel_win}" />',
                f'        <RegistryValue Root="HKCU" Key="{core.INSTALLER_REGISTRY_KEY}" Name="{reg_name}" Type="integer" Value="1" KeyPath="yes" />',
                "      </Component>",
            ]
        )
    return lines


def _cleanup_component_lines(payload_root: Path) -> list[str]:
    """Author empty-folder-only uninstall rows against those exact Directory Ids."""
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
        directory_id = _directory_id(relative)
        cleanup.extend(
            [
                f'      <Component Id="{core._wix_id("DirCmp", relative)}" Guid="{core._component_guid("directory:" + relative)}" Directory="{directory_id}">',
                f'        <RemoveFolder Id="{core._wix_id("Rmf", relative)}" On="uninstall" />',
                f'        <RegistryValue Root="HKCU" Key="{core.INSTALLER_REGISTRY_KEY}" Name="{core._wix_id("dircmp", relative)}" Type="integer" Value="1" KeyPath="yes" />',
                "      </Component>",
            ]
        )
    return cleanup


def generate_explicit_wix_file_fragment(payload_root: Path, destination: Path) -> Path:
    """Generate the payload fragment without any inline Subdirectory authoring."""
    payload_root = payload_root.resolve()
    if not any(p.is_file() for p in payload_root.rglob("*")):
        raise core.BuildError("MSI payload is empty.")

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">',
        "  <Fragment>",
    ]
    lines.extend(_directory_tree_lines(payload_root))
    lines.extend(
        [
            '    <ComponentGroup Id="ApplicationFiles">',
            *_file_component_lines(payload_root),
            *_cleanup_component_lines(payload_root),
            "    </ComponentGroup>",
            "  </Fragment>",
            "</Wix>",
            "",
        ]
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return destination


def _install_ice64_safe_generator() -> None:
    core.generate_wix_file_fragment = generate_explicit_wix_file_fragment


def main() -> int:
    _install_ice64_safe_generator()
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
