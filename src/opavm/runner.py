from __future__ import annotations

from pathlib import Path

from opavm import catalog, installer, resolver
from opavm.errors import VersionNotInstalledError


def resolved_binary_path(start: Path, tool: str = "opa") -> tuple[str, str, Path]:
    spec = catalog.get_tool(tool)
    version, reason = resolver.resolve_version(start, tool=spec.name)
    binary = installer.binary_path(version, tool=spec.name)
    if not binary.exists():
        install_hint = (
            f"Run: opavm install {version}"
            if spec.name == "opa"
            else f"Run: opavm install {spec.name} {version}"
        )
        raise VersionNotInstalledError(
            "Version not installed.",
            install_hint,
        )
    return version, reason, binary
