from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Sequence

import httpx

from opavm.errors import GitHubLookupError

GITHUB_API_ROOT = "https://api.github.com/repos"


@dataclass
class ReleaseAsset:
    name: str
    url: str


@dataclass
class ReleaseInfo:
    version: str
    tag: str
    assets: list[ReleaseAsset]


@dataclass
class ReleaseSummary:
    version: str
    tag: str
    published_at: str
    prerelease: bool


def _github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("OPAVM_GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _raise_friendly_http_error(exc: httpx.HTTPError) -> GitHubLookupError:
    if isinstance(exc, httpx.ProxyError):
        return GitHubLookupError(
            "Failed to query GitHub releases.",
            "Proxy error. Check HTTP_PROXY/HTTPS_PROXY or corporate proxy settings.",
        )
    if isinstance(exc, httpx.ConnectError):
        return GitHubLookupError(
            "Failed to query GitHub releases.",
            "Network connection failed. Check internet connectivity, DNS, firewall, or VPN.",
        )
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 403 and exc.response.headers.get("x-ratelimit-remaining") == "0":
            return GitHubLookupError(
                "GitHub API rate limit exceeded.",
                "Set OPAVM_GITHUB_TOKEN or retry after the rate limit resets.",
            )
        if status == 404:
            return GitHubLookupError(
                "Requested release was not found.",
                "Check version tag and access permissions.",
            )
        if status in {401, 403}:
            return GitHubLookupError(
                "GitHub request was unauthorized.",
                "Check OPAVM_GITHUB_TOKEN and repository access.",
            )
        return GitHubLookupError(
            "Failed to query GitHub releases.",
            f"GitHub API responded with HTTP {status}.",
        )
    return GitHubLookupError(
        "Failed to query GitHub releases.",
        "Check network connectivity, proxy settings, or GitHub availability.",
    )


def configured_repo(
    default_repo: str = "open-policy-agent/opa",
) -> str:
    repo = default_repo.strip()
    parts = repo.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise GitHubLookupError(
            "Invalid repository value.",
            f"Use format: owner/repo (example: {default_repo}).",
        )
    return repo


def validate_repo(repo: str) -> str:
    normalized = repo.strip()
    parts = normalized.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise GitHubLookupError(
            "Invalid repository value.",
            "Use format: owner/repo (example: open-policy-agent/opa).",
        )
    return normalized


def releases_api_url(repo: str) -> str:
    return f"{GITHUB_API_ROOT}/{repo}/releases"


def _normalize_tag(version: str) -> str:
    if version == "latest":
        return version
    if version.startswith("v"):
        return version
    return f"v{version}"


def _version_from_tag(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def fetch_release(version: str, timeout: float = 30.0, repo: str | None = None) -> ReleaseInfo:
    tag = _normalize_tag(version)
    selected_repo = validate_repo(repo) if repo else configured_repo()
    base_url = releases_api_url(selected_repo)
    url = f"{base_url}/latest" if version == "latest" else f"{base_url}/tags/{tag}"

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers=_github_headers())
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise _raise_friendly_http_error(exc) from exc

    release_tag = payload.get("tag_name")
    if not release_tag:
        raise GitHubLookupError("Invalid GitHub response.", "Release tag missing.")

    assets = [
        ReleaseAsset(name=item["name"], url=item["browser_download_url"])
        for item in payload.get("assets", [])
        if "name" in item and "browser_download_url" in item
    ]
    return ReleaseInfo(version=_version_from_tag(release_tag), tag=release_tag, assets=assets)


def fetch_recent_releases(
    limit: int = 10,
    timeout: float = 30.0,
    repo: str | None = None,
) -> list[ReleaseSummary]:
    if limit < 1:
        raise GitHubLookupError("Limit must be at least 1.", "Try: opavm releases --limit 10")

    selected_repo = validate_repo(repo) if repo else configured_repo()
    base_url = releases_api_url(selected_repo)
    url = f"{base_url}?per_page={min(limit, 100)}"
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers=_github_headers())
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise _raise_friendly_http_error(exc) from exc

    if not isinstance(payload, list):
        raise GitHubLookupError("Invalid GitHub response.", "Expected release list.")

    releases: list[ReleaseSummary] = []
    for item in payload:
        tag = item.get("tag_name")
        if not tag:
            continue
        releases.append(
            ReleaseSummary(
                version=_version_from_tag(tag),
                tag=tag,
                published_at=str(item.get("published_at") or ""),
                prerelease=bool(item.get("prerelease")),
            )
        )
        if len(releases) >= limit:
            break

    return releases


def pick_asset_url(release: ReleaseInfo, expected_names: Sequence[str]) -> str:
    for expected_name in expected_names:
        for asset in release.assets:
            if asset.name == expected_name:
                return asset.url
    expected = ", ".join(expected_names)
    raise GitHubLookupError(f"No matching asset found for {expected}.", "Check available release assets.")


def checksum_asset_url(release: ReleaseInfo, asset_name: str) -> str | None:
    checksum_name = f"{asset_name}.sha256"
    raw_assets = getattr(release, "assets", [])
    try:
        assets = list(raw_assets)
    except TypeError:
        return None
    for asset in assets:
        if asset.name == checksum_name:
            return asset.url
    return None
