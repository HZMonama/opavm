from __future__ import annotations

from pathlib import Path
from unittest import mock

from typer.testing import CliRunner

from opavm import cli, github, installer


def test_cli_root_help_includes_tool_selection(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0
    assert "Tool Selection" in result.output
    assert "--tool" in result.output
    assert "opa" in result.output
    assert "regal" in result.output


def test_cli_current_smoke(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    (tmp_path / ".opa-version").write_text("0.62.1\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["current"])
    assert result.exit_code == 0
    assert "OPA 0.62.1" in result.output


def test_cli_which_smoke(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    opavm_home = tmp_path / ".opavm"
    monkeypatch.setenv("OPAVM_HOME", str(opavm_home))

    (tmp_path / ".opa-version").write_text("0.62.1\n", encoding="utf-8")
    binary = installer.binary_path("0.62.1")
    binary.parent.mkdir(parents=True)
    binary.write_text("fake", encoding="utf-8")

    result = runner.invoke(cli.app, ["which"])
    assert result.exit_code == 0
    assert str(binary.resolve()) in result.output


def test_cli_exec_forwards_args_and_exit_code(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    opavm_home = tmp_path / ".opavm"
    monkeypatch.setenv("OPAVM_HOME", str(opavm_home))

    (tmp_path / ".opa-version").write_text("0.62.1\n", encoding="utf-8")
    binary = installer.binary_path("0.62.1")
    binary.parent.mkdir(parents=True)
    binary.write_text("fake", encoding="utf-8")

    with mock.patch("opavm.cli.subprocess.run", return_value=mock.Mock(returncode=7)) as run_mock:
        result = runner.invoke(cli.app, ["exec", "--", "version"])

    assert result.exit_code == 7
    run_mock.assert_called_once_with([str(binary), "version"])


def test_cli_pin_prompts_install_for_missing_version(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    with mock.patch("opavm.cli.installer.is_installed", return_value=False), mock.patch(
        "opavm.cli.installer.install", return_value="0.61.0"
    ) as install_mock:
        result = runner.invoke(cli.app, ["pin", "0.61.0"], input="y\n")

    assert result.exit_code == 0
    assert install_mock.call_count == 1
    args, kwargs = install_mock.call_args
    assert args == ("0.61.0",)
    assert kwargs["tool"] == "opa"
    assert callable(kwargs["on_status"])
    assert callable(kwargs["on_download"])
    assert (tmp_path / ".opa-version").read_text(encoding="utf-8") == "0.61.0\n"


def test_cli_pin_decline_install_exits_with_error(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    with mock.patch("opavm.cli.installer.is_installed", return_value=False), mock.patch(
        "opavm.cli.installer.install"
    ) as install_mock:
        result = runner.invoke(cli.app, ["pin", "0.61.0"], input="n\n")

    assert result.exit_code == 1
    install_mock.assert_not_called()
    assert not (tmp_path / ".opa-version").exists()


def test_cli_releases_table(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    releases_data = [
        github.ReleaseSummary(
            version="1.2.3",
            tag="v1.2.3",
            published_at="2026-02-01T00:00:00Z",
            prerelease=False,
        )
    ]
    with mock.patch("opavm.cli.github.fetch_recent_releases", return_value=releases_data):
        result = runner.invoke(cli.app, ["releases", "--limit", "1"])

    assert result.exit_code == 0
    assert result.output.startswith("\n")
    assert "OPA Releases" in result.output
    assert "https://github.com/open-policy-agent/opa/releases" in result.output
    assert "1.2.3" in result.output


def test_cli_releases_regal_table_header_link(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    releases_data = [
        github.ReleaseSummary(
            version="0.38.1",
            tag="v0.38.1",
            published_at="2026-02-01T00:00:00Z",
            prerelease=False,
        )
    ]
    with mock.patch("opavm.cli.github.fetch_recent_releases", return_value=releases_data):
        result = runner.invoke(cli.app, ["releases", "--tool", "regal", "--limit", "1"])

    assert result.exit_code == 0
    assert "Regal Releases" in result.output
    assert "https://github.com/StyraInc/regal/releases" in result.output
    assert "0.38.1" in result.output


def test_cli_install_help_includes_tool_and_examples(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["install", "--help"])

    assert result.exit_code == 0
    assert "--tool" in result.output
    assert "Tool Selection" in result.output
    assert "Examples" in result.output
    assert "opavm install regal 0.38.1" in result.output


def test_cli_exec_help_shows_opa_commands(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["exec", "--help"])

    assert result.exit_code == 0
    assert "Usage: opavm exec -- <opa-args>" in result.output
    assert "Available OPA Commands" in result.output
    assert "bench" in result.output
    assert "test" in result.output


def test_cli_use_regal_sets_global_default(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPAVM_HOME", str(tmp_path / ".opavm"))

    with mock.patch("opavm.cli.installer.is_installed", return_value=True):
        result = runner.invoke(cli.app, ["use", "0.38.1", "--tool", "regal"])

    assert result.exit_code == 0
    assert "Global default for Regal set to 0.38.1." in result.output


def test_cli_pin_regal_writes_regal_pin_file(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    with mock.patch("opavm.cli.installer.is_installed", return_value=True):
        result = runner.invoke(cli.app, ["pin", "0.38.1", "--tool", "regal"])

    assert result.exit_code == 0
    assert (tmp_path / ".regal-version").read_text(encoding="utf-8") == "0.38.1\n"


def test_cli_current_regal_smoke(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    (tmp_path / ".regal-version").write_text("0.38.1\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["current", "--tool", "regal"])
    assert result.exit_code == 0
    assert "Regal 0.38.1" in result.output


def test_cli_which_regal_smoke(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    opavm_home = tmp_path / ".opavm"
    monkeypatch.setenv("OPAVM_HOME", str(opavm_home))

    (tmp_path / ".regal-version").write_text("0.38.1\n", encoding="utf-8")
    binary = installer.binary_path("0.38.1", tool="regal")
    binary.parent.mkdir(parents=True)
    binary.write_text("fake", encoding="utf-8")

    result = runner.invoke(cli.app, ["which", "--tool", "regal"])
    assert result.exit_code == 0
    assert str(binary.resolve()) in result.output


def test_cli_exec_regal_forwards_args_and_exit_code(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    opavm_home = tmp_path / ".opavm"
    monkeypatch.setenv("OPAVM_HOME", str(opavm_home))

    (tmp_path / ".regal-version").write_text("0.38.1\n", encoding="utf-8")
    binary = installer.binary_path("0.38.1", tool="regal")
    binary.parent.mkdir(parents=True)
    binary.write_text("fake", encoding="utf-8")

    with mock.patch("opavm.cli.subprocess.run", return_value=mock.Mock(returncode=3)) as run_mock:
        result = runner.invoke(cli.app, ["exec", "--tool", "regal", "--", "version"])

    assert result.exit_code == 3
    run_mock.assert_called_once_with([str(binary), "version"])


def test_cli_install_regal_invokes_regal_tool(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    with mock.patch("opavm.cli._install_with_progress", return_value="0.38.1") as install_mock, mock.patch(
        "opavm.cli.installer.binary_path", return_value=Path("/tmp/regal")
    ) as path_mock, mock.patch("opavm.cli.shim.ensure_shim") as shim_mock:
        result = runner.invoke(cli.app, ["install", "regal", "0.38.1"])

    assert result.exit_code == 0
    install_mock.assert_called_once_with("regal", "0.38.1")
    path_mock.assert_called_once_with("0.38.1", tool="regal")
    shim_mock.assert_not_called()
    assert "Installed Regal 0.38.1." in result.output


def test_cli_install_tool_without_version_defaults_latest(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    with mock.patch("opavm.cli._install_with_progress", return_value="0.38.1") as install_mock, mock.patch(
        "opavm.cli.installer.binary_path", return_value=Path("/tmp/regal")
    ), mock.patch("opavm.cli.shim.ensure_shim") as shim_mock:
        result = runner.invoke(cli.app, ["install", "regal"])

    assert result.exit_code == 0
    install_mock.assert_called_once_with("regal", "latest")
    shim_mock.assert_not_called()
