from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

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


def load_state() -> dict[str, str | None]:
    path = state_path()
    if not path.exists():
        return {"global_default": None}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OpavmError("Corrupt state file.", "Delete ~/.opavm/state.json and retry.") from exc
    return {"global_default": raw.get("global_default")}


def save_state(data: dict[str, str | None]) -> None:
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
