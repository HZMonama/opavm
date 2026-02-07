from __future__ import annotations

import json
from pathlib import Path

import pytest

from opavm import config


def test_load_state_defaults_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))
    assert config.load_state() == {"global_default": None}


def test_save_state_is_atomic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))

    config.save_state({"global_default": "0.62.1"})

    path = config.state_path()
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["global_default"] == "0.62.1"

    leftovers = list(path.parent.glob("state.*.tmp"))
    assert leftovers == []
