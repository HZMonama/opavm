from __future__ import annotations

from pathlib import Path

from opavm import config
from opavm.errors import VersionNotConfiguredError


def find_pin_file(start: Path) -> Path | None:
    current = start.resolve()
    for directory in [current, *current.parents]:
        pin = directory / ".opa-version"
        if pin.exists():
            return pin
    return None


def resolve_version(start: Path) -> tuple[str, str]:
    pin_file = find_pin_file(start)
    if pin_file:
        pinned = pin_file.read_text(encoding="utf-8").strip()
        if pinned:
            return pinned, f"pinned via {pin_file}"

    state = config.load_state()
    global_default = state.get("global_default")
    if global_default:
        return str(global_default), "global default"

    raise VersionNotConfiguredError(
        "No version configured.", "Run: opavm use <version> or create .opa-version."
    )
