from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from opavm import download, github, installer
from opavm.errors import OpavmError


def test_parse_checksum_text() -> None:
    text = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824  opa_linux_amd64\n"
    parsed = download.parse_checksum_text(text)
    assert parsed == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_sha256_file(tmp_path: Path) -> None:
    file_path = tmp_path / "bin"
    file_path.write_bytes(b"hello")
    assert download.sha256_file(file_path) == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_installer_checksum_mismatch_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))
    release = github.ReleaseInfo(
        version="0.62.1",
        tag="v0.62.1",
        assets=[
            github.ReleaseAsset(name="opa_linux_amd64", url="https://example.test/opa"),
            github.ReleaseAsset(name="opa_linux_amd64.sha256", url="https://example.test/opa.sha256"),
        ],
    )
    with mock.patch("opavm.installer.platform.normalized_os_arch", return_value=("linux", "amd64")), mock.patch(
        "opavm.installer.github.fetch_release", return_value=release
    ) as fetch_release_mock, mock.patch(
        "opavm.installer.github.pick_asset_url", return_value="https://example.test/opa"
    ), mock.patch("opavm.installer.download.fetch_text", return_value="0" * 64), mock.patch(
        "opavm.installer.verify_binary"
    ):
        def fake_download(_url: str, destination: Path, on_progress=None) -> None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"different-content")
            if on_progress is not None:
                on_progress(17, 17)

        with mock.patch("opavm.installer.download.download_binary", side_effect=fake_download):
            with pytest.raises(OpavmError, match="Checksum verification failed"):
                installer.install("0.62.1")
    assert fetch_release_mock.call_args.kwargs["repo"] == "open-policy-agent/opa"


def test_installer_checksum_match_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))
    release = github.ReleaseInfo(
        version="0.62.1",
        tag="v0.62.1",
        assets=[
            github.ReleaseAsset(name="opa_linux_amd64", url="https://example.test/opa"),
            github.ReleaseAsset(name="opa_linux_amd64.sha256", url="https://example.test/opa.sha256"),
        ],
    )
    with mock.patch("opavm.installer.platform.normalized_os_arch", return_value=("linux", "amd64")), mock.patch(
        "opavm.installer.github.fetch_release", return_value=release
    ) as fetch_release_mock, mock.patch(
        "opavm.installer.github.pick_asset_url", return_value="https://example.test/opa"
    ), mock.patch("opavm.installer.verify_binary") as verify_mock:
        def fake_download(_url: str, destination: Path, on_progress=None) -> None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"trusted")
            if on_progress is not None:
                on_progress(7, 7)

        expected_checksum = "a9a089195c68d2adeee23beaa2c3a93b1d4cdf09046e7a9e520b3b166dff3e6a"
        with mock.patch("opavm.installer.download.download_binary", side_effect=fake_download), mock.patch(
            "opavm.installer.download.fetch_text", return_value=f"{expected_checksum}  opa_linux_amd64\n"
        ):
            installed = installer.install("0.62.1")

    assert installed == "0.62.1"
    assert fetch_release_mock.call_args.kwargs["repo"] == "open-policy-agent/opa"
    verify_mock.assert_called_once()
