from __future__ import annotations

from pathlib import Path

from opavm import installer, resolver
from opavm.errors import VersionNotInstalledError


def resolved_binary_path(start: Path) -> tuple[str, str, Path]:
    version, reason = resolver.resolve_version(start)
    binary = installer.binary_path(version)
    if not binary.exists():
        raise VersionNotInstalledError(
            "Version not installed.", f"Run: opavm install {version}"
        )
    return version, reason, binary
