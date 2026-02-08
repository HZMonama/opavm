from __future__ import annotations

import json
from pathlib import Path

import pytest

from opavm import config


def test_load_state_defaults_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))
    assert config.load_state() == {"global_default": None, "global_defaults": {}}


def test_save_state_is_atomic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))

    config.save_state({"global_default": "0.62.1"})

    path = config.state_path()
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["global_default"] == "0.62.1"

    leftovers = list(path.parent.glob("state.*.tmp"))
    assert leftovers == []


def test_set_get_global_default_by_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))

    config.set_global_default("opa", "0.62.1")
    config.set_global_default("regal", "0.38.1")

    assert config.get_global_default("opa") == "0.62.1"
    assert config.get_global_default("regal") == "0.38.1"


def test_get_global_default_opa_falls_back_to_legacy_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))
    config.save_state({"global_default": "0.60.0"})

    assert config.get_global_default("opa") == "0.60.0"
