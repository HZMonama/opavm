from __future__ import annotations

from pathlib import Path

from opavm import catalog, config
from opavm.errors import VersionNotConfiguredError


def pin_filename(tool: str = "opa") -> str:
    spec = catalog.get_tool(tool)
    return spec.pin_filename


def find_pin_file(start: Path, tool: str = "opa") -> Path | None:
    current = start.resolve()
    filename = pin_filename(tool)
    for directory in [current, *current.parents]:
        pin = directory / filename
        if pin.exists():
            return pin
    return None


def resolve_version(start: Path, tool: str = "opa") -> tuple[str, str]:
    spec = catalog.get_tool(tool)
    pin_file = find_pin_file(start, tool=spec.name)
    if pin_file:
        pinned = pin_file.read_text(encoding="utf-8").strip()
        if pinned:
            return pinned, f"pinned via {pin_file}"

    global_default = config.get_global_default(spec.name)
    if global_default:
        return global_default, "global default"

    use_hint = "Run: opavm use <version>"
    pin_hint = f"create {spec.pin_filename}"
    if spec.name != "opa":
        use_hint = f"Run: opavm use <version> --tool {spec.name}"

    raise VersionNotConfiguredError(
        "No version configured.",
        f"{use_hint} or {pin_hint}.",
    )
