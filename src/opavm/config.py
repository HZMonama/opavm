from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from opavm.errors import OpavmError

DEFAULT_BASE_DIR = Path.home() / ".opavm"


def base_dir() -> Path:
    return Path(os.environ.get("OPAVM_HOME", DEFAULT_BASE_DIR)).expanduser()


def versions_dir() -> Path:
    return base_dir() / "versions"


def tool_versions_dir(tool: str) -> Path:
    if tool == "opa":
        return versions_dir()
    return base_dir() / "tools" / tool / "versions"


def shims_dir() -> Path:
    return base_dir() / "shims"


def state_path() -> Path:
    return base_dir() / "state.json"


def ensure_layout() -> None:
    versions_dir().mkdir(parents=True, exist_ok=True)
    shims_dir().mkdir(parents=True, exist_ok=True)


def _default_state() -> dict[str, Any]:
    return {"global_default": None, "global_defaults": {}}


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        return _default_state()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OpavmError("Corrupt state file.", "Delete ~/.opavm/state.json and retry.") from exc
    if not isinstance(raw, dict):
        return _default_state()

    state = _default_state()
    state["global_default"] = raw.get("global_default")

    global_defaults = raw.get("global_defaults")
    if isinstance(global_defaults, dict):
        state["global_defaults"] = {
            str(tool): str(version)
            for tool, version in global_defaults.items()
            if isinstance(tool, str) and isinstance(version, str)
        }
    else:
        state["global_defaults"] = {}
    return state


def save_state(data: dict[str, Any]) -> None:
    ensure_layout()
    path = state_path()
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix="state.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def get_global_default(tool: str = "opa") -> str | None:
    state = load_state()
    global_defaults = state.get("global_defaults")
    if isinstance(global_defaults, dict):
        value = global_defaults.get(tool)
        if isinstance(value, str) and value.strip():
            return value

    if tool == "opa":
        legacy = state.get("global_default")
        if isinstance(legacy, str) and legacy.strip():
            return legacy
    return None


def set_global_default(tool: str, version: str) -> None:
    state = load_state()
    global_defaults = state.get("global_defaults")
    if not isinstance(global_defaults, dict):
        global_defaults = {}
    global_defaults[tool] = version
    state["global_defaults"] = global_defaults
    if tool == "opa":
        state["global_default"] = version
    save_state(state)
