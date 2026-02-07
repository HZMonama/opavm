from __future__ import annotations

from unittest import mock

import pytest

from opavm.errors import UnsupportedPlatformError
from opavm.platform import asset_name, asset_name_candidates, binary_filename, normalized_os_arch


@pytest.mark.parametrize(
    ("sys_name", "machine", "expected"),
    [
        ("Darwin", "x86_64", ("darwin", "amd64")),
        ("Darwin", "arm64", ("darwin", "arm64")),
        ("Linux", "amd64", ("linux", "amd64")),
        ("Linux", "aarch64", ("linux", "arm64")),
        ("Windows", "x86_64", ("windows", "amd64")),
    ],
)
def test_normalized_os_arch_supported(sys_name: str, machine: str, expected: tuple[str, str]) -> None:
    with mock.patch("platform.system", return_value=sys_name), mock.patch(
        "platform.machine", return_value=machine
    ):
        assert normalized_os_arch() == expected


def test_normalized_os_arch_rejects_windows_arm64() -> None:
    with mock.patch("platform.system", return_value="Windows"), mock.patch(
        "platform.machine", return_value="arm64"
    ):
        with pytest.raises(UnsupportedPlatformError):
            normalized_os_arch()


def test_asset_name() -> None:
    assert asset_name("0.62.1", "linux", "amd64") == "opa_linux_amd64"
    assert asset_name("0.62.1", "windows", "amd64") == "opa_windows_amd64.exe"
    assert asset_name("0.38.1", "linux", "amd64", binary_base="regal") == "regal_linux_amd64"


def test_asset_name_candidates_arm64_static_fallback() -> None:
    assert asset_name_candidates("linux", "arm64") == ["opa_linux_arm64", "opa_linux_arm64_static"]


def test_binary_filename() -> None:
    assert binary_filename("linux") == "opa"
    assert binary_filename("windows") == "opa.exe"
    assert binary_filename("windows", binary_base="regal") == "regal.exe"
