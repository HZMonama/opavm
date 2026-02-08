from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from opavm import catalog, config, download, github, platform
from opavm.errors import OpavmError, VersionNotInstalledError

StatusCallback = Callable[[str], None]
DownloadProgressCallback = Callable[[int | None, int], None]


def _tool_versions_dir(tool: str) -> Path:
    return config.tool_versions_dir(tool)


def _asset_candidates(tool: str, os_name: str, arch: str) -> list[str]:
    if tool == "opa":
        return platform.asset_name_candidates(os_name, arch, binary_base="opa")

    if tool == "regal":
        os_token = {"darwin": "Darwin", "linux": "Linux", "windows": "Windows"}[os_name]
        arch_token = {"amd64": "x86_64", "arm64": "arm64"}[arch]
        suffix = ".exe" if os_name == "windows" else ""
        return [f"regal_{os_token}_{arch_token}{suffix}"]

    raise OpavmError("Unknown tool.", f"Supported tools: {', '.join(sorted(catalog.SUPPORTED_TOOLS))}")


def installed_versions(tool: str = "opa") -> list[str]:
    spec = catalog.get_tool(tool)
    root = _tool_versions_dir(spec.name)
    if not root.exists():
        return []
    versions: list[str] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if (entry / spec.binary_base).exists() or (entry / f"{spec.binary_base}.exe").exists():
            versions.append(entry.name)
    return sorted(versions)


def _platform_binary_path(version: str, os_name: str, tool: str = "opa") -> Path:
    spec = catalog.get_tool(tool)
    return _tool_versions_dir(spec.name) / version / platform.binary_filename(os_name, spec.binary_base)


def binary_path(version: str, tool: str = "opa") -> Path:
    spec = catalog.get_tool(tool)
    os_name, _ = platform.normalized_os_arch()
    preferred = _platform_binary_path(version, os_name, spec.name)
    if preferred.exists():
        return preferred
    alternate_name = (
        f"{spec.binary_base}.exe" if preferred.name == spec.binary_base else spec.binary_base
    )
    alternate = preferred.parent / alternate_name
    if alternate.exists():
        return alternate
    return preferred


def is_installed(version: str, tool: str = "opa") -> bool:
    return binary_path(version, tool=tool).exists()


def verify_binary(binary: Path) -> None:
    try:
        subprocess.run([str(binary), "version"], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise OpavmError("Installed binary failed verification.", "Run install again.") from exc


def install(
    version: str,
    tool: str = "opa",
    on_status: StatusCallback | None = None,
    on_download: DownloadProgressCallback | None = None,
) -> str:
    spec = catalog.get_tool(tool)
    config.ensure_layout()
    if on_status is not None:
        on_status("resolving")

    os_name, arch = platform.normalized_os_arch()
    repo = spec.default_repo
    release = github.fetch_release(version, repo=repo)
    resolved_version = release.version

    if is_installed(resolved_version, tool=spec.name):
        if on_status is not None:
            on_status("already_installed")
        return resolved_version

    expected_assets = _asset_candidates(spec.name, os_name, arch)
    raw_assets = getattr(release, "assets", [])
    try:
        assets = list(raw_assets)
    except TypeError:
        assets = []
    selected_asset_name = ""
    for candidate in expected_assets:
        for asset in assets:
            if asset.name == candidate:
                selected_asset_name = candidate
                break
        if selected_asset_name:
            break
    if not selected_asset_name and expected_assets:
        selected_asset_name = expected_assets[0]
    asset_url = github.pick_asset_url(release, expected_assets)

    target = _platform_binary_path(resolved_version, os_name, spec.name)
    if on_status is not None:
        on_status("downloading")
    download.download_binary(asset_url, target, on_progress=on_download)
    checksum_url = github.checksum_asset_url(release, selected_asset_name)
    if checksum_url:
        if on_status is not None:
            on_status("verifying_checksum")
        expected_checksum = download.parse_checksum_text(download.fetch_text(checksum_url))
        actual_checksum = download.sha256_file(target)
        if expected_checksum != actual_checksum:
            raise OpavmError(
                "Checksum verification failed.",
                f"Downloaded file hash mismatch for {selected_asset_name}.",
            )
    if on_status is not None:
        on_status("verifying")
    verify_binary(target)
    if on_status is not None:
        on_status("done")

    return resolved_version


def uninstall(version: str, tool: str = "opa") -> None:
    spec = catalog.get_tool(tool)
    if not is_installed(version, tool=spec.name):
        install_hint = f"opavm install {version}" if spec.name == "opa" else f"opavm install {spec.name} {version}"
        raise VersionNotInstalledError(
            "Version not installed.", f"Run: {install_hint}"
        )
    download.remove_tree(_tool_versions_dir(spec.name) / version)
