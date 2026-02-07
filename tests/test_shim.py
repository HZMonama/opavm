from __future__ import annotations

from pathlib import Path

import pytest

from opavm import config, shim


def test_ensure_shim_windows_creates_cmd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))
    monkeypatch.setattr("opavm.shim.platform.normalized_os_arch", lambda: ("windows", "amd64"))

    shim_path = shim.ensure_shim()

    assert shim_path.name == "opa.cmd"
    content = shim_path.read_text(encoding="utf-8")
    assert "opavm which" in content
    assert "%*" in content


def test_ensure_shim_posix_creates_opa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))
    monkeypatch.setattr("opavm.shim.platform.normalized_os_arch", lambda: ("linux", "amd64"))

    shim_path = shim.ensure_shim()

    assert shim_path.name == "opa"
    assert (config.shims_dir() / "opa").exists()
    content = shim_path.read_text(encoding="utf-8")
    assert "opavm which" in content
