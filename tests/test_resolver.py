from __future__ import annotations

from pathlib import Path

import pytest

from opavm import config
from opavm.errors import VersionNotConfiguredError
from opavm.resolver import find_pin_file, resolve_version


def test_find_pin_file_walks_parents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    project = tmp_path / "a" / "b" / "c"
    project.mkdir(parents=True)
    pin = tmp_path / "a" / ".opa-version"
    pin.write_text("0.62.1\n", encoding="utf-8")

    found = find_pin_file(project)
    assert found == pin


def test_find_pin_file_walks_parents_for_regal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    project = tmp_path / "a" / "b" / "c"
    project.mkdir(parents=True)
    pin = tmp_path / "a" / ".regal-version"
    pin.write_text("0.38.1\n", encoding="utf-8")

    found = find_pin_file(project, tool="regal")
    assert found == pin


def test_resolve_prefers_pin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))
    config.set_global_default("opa", "0.60.0")

    pin = tmp_path / ".opa-version"
    pin.write_text("0.62.1\n", encoding="utf-8")

    version, reason = resolve_version(tmp_path)
    assert version == "0.62.1"
    assert ".opa-version" in reason


def test_resolve_regal_prefers_pin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))
    config.set_global_default("regal", "0.37.0")

    pin = tmp_path / ".regal-version"
    pin.write_text("0.38.1\n", encoding="utf-8")

    version, reason = resolve_version(tmp_path, tool="regal")
    assert version == "0.38.1"
    assert ".regal-version" in reason


def test_resolve_falls_back_to_global(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))
    config.set_global_default("opa", "0.61.0")

    version, reason = resolve_version(tmp_path)
    assert version == "0.61.0"
    assert reason == "global default"


def test_resolve_regal_falls_back_to_global(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))
    config.set_global_default("regal", "0.38.1")

    version, reason = resolve_version(tmp_path, tool="regal")
    assert version == "0.38.1"
    assert reason == "global default"


def test_resolve_errors_when_unconfigured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))

    with pytest.raises(VersionNotConfiguredError):
        resolve_version(tmp_path)
