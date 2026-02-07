from __future__ import annotations

import platform

from opavm.errors import UnsupportedPlatformError


def normalized_os_arch() -> tuple[str, str]:
    sys_name = platform.system().lower()
    machine = platform.machine().lower()

    if sys_name == "darwin":
        os_name = "darwin"
    elif sys_name == "linux":
        os_name = "linux"
    elif sys_name == "windows":
        os_name = "windows"
    else:
        raise UnsupportedPlatformError(
            f"Unsupported OS: {sys_name}.", "opavm supports macOS, Linux, and Windows."
        )

    if machine in {"x86_64", "amd64"}:
        arch = "amd64"
    elif machine in {"aarch64", "arm64"}:
        arch = "arm64"
    else:
        raise UnsupportedPlatformError(
            f"Unsupported architecture: {machine}.", "Use amd64 or arm64 hardware."
        )

    if os_name == "windows" and arch != "amd64":
        raise UnsupportedPlatformError(
            f"Unsupported architecture: {machine}.",
            "Windows support currently requires amd64.",
        )

    return os_name, arch


def asset_name(version: str, os_name: str, arch: str, binary_base: str = "opa") -> str:
    _ = version
    extension = ".exe" if os_name == "windows" else ""
    return f"{binary_base}_{os_name}_{arch}{extension}"


def asset_name_candidates(os_name: str, arch: str, binary_base: str = "opa") -> list[str]:
    primary = asset_name("latest", os_name, arch, binary_base=binary_base)
    candidates = [primary]

    # Older arm64 OPA releases expose only static assets on macOS/Linux.
    if binary_base == "opa" and os_name in {"darwin", "linux"} and arch == "arm64":
        candidates.append(f"opa_{os_name}_{arch}_static")

    return candidates


def binary_filename(os_name: str, binary_base: str = "opa") -> str:
    return f"{binary_base}.exe" if os_name == "windows" else binary_base
