from __future__ import annotations

from pathlib import Path

import httpx
from typer.testing import CliRunner

from opavm import cli


class _RateLimitedClient:
    def __init__(self, *_args, **_kwargs) -> None:
        return None

    def __enter__(self) -> "_RateLimitedClient":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> bool:
        return False

    def get(self, url: str, headers: dict[str, str]) -> httpx.Response:
        _ = headers
        request = httpx.Request("GET", url)
        response = httpx.Response(403, request=request, headers={"x-ratelimit-remaining": "0"})
        raise httpx.HTTPStatusError("rate limited", request=request, response=response)


class _ProxyErrorClient:
    def __init__(self, *_args, **_kwargs) -> None:
        return None

    def __enter__(self) -> "_ProxyErrorClient":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> bool:
        return False

    def get(self, url: str, headers: dict[str, str]) -> httpx.Response:
        _ = headers
        request = httpx.Request("GET", url)
        raise httpx.ProxyError("proxy failure", request=request)


class _ConnectErrorClient:
    def __init__(self, *_args, **_kwargs) -> None:
        return None

    def __enter__(self) -> "_ConnectErrorClient":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> bool:
        return False

    def get(self, url: str, headers: dict[str, str]) -> httpx.Response:
        _ = headers
        request = httpx.Request("GET", url)
        raise httpx.ConnectError("connect failure", request=request)


def test_cli_releases_rate_limited_message(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("opavm.github.httpx.Client", _RateLimitedClient)

    result = runner.invoke(cli.app, ["releases", "--limit", "1"])

    assert result.exit_code == 1
    assert "rate limit" in result.output.lower()


def test_cli_releases_proxy_error_message(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("opavm.github.httpx.Client", _ProxyErrorClient)

    result = runner.invoke(cli.app, ["releases", "--limit", "1"])

    assert result.exit_code == 1
    assert "proxy" in result.output.lower()


def test_cli_install_network_fault_message(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("opavm.github.httpx.Client", _ConnectErrorClient)
    monkeypatch.setattr("opavm.installer.platform.normalized_os_arch", lambda: ("linux", "amd64"))

    result = runner.invoke(cli.app, ["install", "latest"])

    assert result.exit_code == 1
    assert "network" in result.output.lower() or "connect" in result.output.lower()
