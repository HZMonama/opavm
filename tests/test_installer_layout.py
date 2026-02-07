from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from opavm import config, installer


def test_install_layout_and_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))

    fake_release = mock.Mock(version="0.62.1")

    with mock.patch("opavm.installer.platform.normalized_os_arch", return_value=("linux", "amd64")), mock.patch(
        "opavm.installer.github.fetch_release", return_value=fake_release
    ), mock.patch("opavm.installer.github.pick_asset_url", return_value="https://example.test/opa"), mock.patch(
        "opavm.installer.download.download_binary"
    ) as mock_download, mock.patch("opavm.installer.verify_binary") as mock_verify:
        def fake_download(_url: str, destination: Path, on_progress=None) -> None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("bin", encoding="utf-8")
            if on_progress is not None:
                on_progress(3, 3)

        mock_download.side_effect = fake_download

        installed = installer.install("0.62.1")
        assert installed == "0.62.1"
        assert (config.versions_dir() / "0.62.1" / "opa").exists()
        assert mock_verify.call_count == 1

        installed_again = installer.install("0.62.1")
        assert installed_again == "0.62.1"
        assert mock_download.call_count == 1


def test_install_regal_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))

    fake_release = mock.Mock(version="0.38.1")

    with mock.patch("opavm.installer.platform.normalized_os_arch", return_value=("linux", "amd64")), mock.patch(
        "opavm.installer.github.configured_repo", return_value="StyraInc/regal"
    ), mock.patch("opavm.installer.github.fetch_release", return_value=fake_release), mock.patch(
        "opavm.installer.github.pick_asset_url", return_value="https://example.test/regal"
    ) as pick_mock, mock.patch("opavm.installer.download.download_binary") as mock_download, mock.patch(
        "opavm.installer.verify_binary"
    ):
        def fake_download(_url: str, destination: Path, on_progress=None) -> None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("bin", encoding="utf-8")
            if on_progress is not None:
                on_progress(3, 3)

        mock_download.side_effect = fake_download

        installed = installer.install("0.38.1", tool="regal")
        assert installed == "0.38.1"
        assert (config.base_dir() / "tools" / "regal" / "versions" / "0.38.1" / "regal").exists()
        expected_candidates = ["regal_Linux_x86_64"]
        assert pick_mock.call_args.args[1] == expected_candidates
