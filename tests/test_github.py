from __future__ import annotations

import pytest

from opavm.errors import GitHubLookupError
from opavm import github


def test_configured_repo_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPAVM_GITHUB_REPO", raising=False)
    assert github.configured_repo() == "open-policy-agent/opa"


def test_configured_repo_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_GITHUB_REPO", "acme/custom-opa")
    assert github.configured_repo() == "acme/custom-opa"


def test_configured_repo_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_GITHUB_REPO", "not-valid")
    with pytest.raises(GitHubLookupError):
        github.configured_repo()


def test_configured_repo_custom_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_REGAL_GITHUB_REPO", "styra/regal-fork")
    assert github.configured_repo(
        env_var="OPAVM_REGAL_GITHUB_REPO",
        default_repo="StyraInc/regal",
    ) == "styra/regal-fork"


def test_fetch_release_uses_configured_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_GITHUB_REPO", "acme/custom-opa")
    seen: dict[str, str] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"tag_name": "v1.2.3", "assets": []}

    class FakeClient:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, _exc_type, _exc, _tb) -> bool:
            return False

        def get(self, url: str, headers: dict[str, str]) -> FakeResponse:
            seen["url"] = url
            seen["accept"] = headers.get("Accept", "")
            return FakeResponse()

    monkeypatch.setattr(github.httpx, "Client", FakeClient)

    release = github.fetch_release("1.2.3")
    assert release.version == "1.2.3"
    assert seen["url"] == "https://api.github.com/repos/acme/custom-opa/releases/tags/v1.2.3"
    assert seen["accept"] == "application/vnd.github+json"


def test_fetch_recent_releases_uses_configured_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPAVM_GITHUB_REPO", "acme/custom-opa")
    seen: dict[str, str] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            return [
                {
                    "tag_name": "v1.2.3",
                    "published_at": "2026-02-01T00:00:00Z",
                    "prerelease": False,
                }
            ]

    class FakeClient:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, _exc_type, _exc, _tb) -> bool:
            return False

        def get(self, url: str, headers: dict[str, str]) -> FakeResponse:
            seen["url"] = url
            seen["accept"] = headers.get("Accept", "")
            return FakeResponse()

    monkeypatch.setattr(github.httpx, "Client", FakeClient)

    releases = github.fetch_recent_releases(limit=1)
    assert releases[0].version == "1.2.3"
    assert seen["url"] == "https://api.github.com/repos/acme/custom-opa/releases?per_page=1"
    assert seen["accept"] == "application/vnd.github+json"


def test_pick_asset_url_prefers_first_candidate() -> None:
    release = github.ReleaseInfo(
        version="1.2.3",
        tag="v1.2.3",
        assets=[
            github.ReleaseAsset(name="opa_linux_arm64_static", url="https://example/static"),
            github.ReleaseAsset(name="opa_linux_amd64", url="https://example/amd64"),
        ],
    )
    picked = github.pick_asset_url(release, ["opa_linux_arm64", "opa_linux_arm64_static"])
    assert picked == "https://example/static"
