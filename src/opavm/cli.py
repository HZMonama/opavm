from __future__ import annotations

import subprocess
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.filesize import decimal
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from opavm import catalog, config, github, installer, resolver, runner, shim
from opavm.errors import OpavmError, VersionNotInstalledError

app = typer.Typer(
    no_args_is_help=True,
    help=(
        "A dead-simple OPA version manager.\n\n"
        "[bold magenta]Tool Selection[/]\n"
        "- [cyan]opa[/cyan] (default)\n"
        "- [cyan]regal[/cyan]\n\n"
        "Use [cyan]--tool[/cyan] on tool-aware commands like "
        "[green]list[/green], [green]uninstall[/green], and [green]releases[/green].\n"
        "For install you can use either [green]opavm install regal 0.38.1[/green] "
        "or [green]opavm install 0.38.1 --tool regal[/green]."
    ),
    rich_markup_mode="rich",
)
console = Console()
OPA_COMMANDS = [
    ("bench", "Benchmark a Rego query"),
    ("build", "Build an OPA bundle"),
    ("capabilities", "Print the capabilities of OPA"),
    ("check", "Check Rego source files"),
    ("completion", "Generate shell completion"),
    ("deps", "Analyze Rego query dependencies"),
    ("eval", "Evaluate a Rego query"),
    ("exec", "Execute against input files"),
    ("fmt", "Format Rego source files"),
    ("help", "Help about any command"),
    ("inspect", "Inspect OPA bundle(s)"),
    ("parse", "Parse Rego source file"),
    ("run", "Start OPA in interactive or server mode"),
    ("sign", "Generate an OPA bundle signature"),
    ("test", "Execute Rego test cases"),
    ("version", "Print the version of OPA"),
]


def _handle_error(err: OpavmError) -> None:
    console.print(f"[red]{err.format()}[/red]")
    raise typer.Exit(code=1)


def _resolve_install_target(subject: str, version: str | None) -> tuple[catalog.ToolSpec, str]:
    if version is None:
        lowered = subject.lower().strip()
        if lowered in catalog.SUPPORTED_TOOLS:
            return catalog.get_tool(lowered), "latest"
        return catalog.get_tool("opa"), subject
    return catalog.get_tool(subject), version


def _resolve_install_target_with_option(
    subject: str,
    version: str | None,
    tool_option: str | None,
) -> tuple[catalog.ToolSpec, str]:
    if tool_option is None:
        return _resolve_install_target(subject, version)

    spec = catalog.get_tool(tool_option)
    if version is not None:
        raise OpavmError(
            "Invalid install arguments.",
            "With --tool, use: opavm install <version> --tool <opa|regal>",
        )

    if subject.lower().strip() == spec.name:
        return spec, "latest"
    return spec, subject


def _install_with_progress(tool: str, version: str) -> str:
    spec = catalog.get_tool(tool)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task("Preparing install...", total=100.0, completed=0.0)

        def on_status(stage: str) -> None:
            if stage == "resolving":
                progress.update(
                    task_id, description=f"Resolving {spec.display_name} release metadata...", completed=5.0
                )
            elif stage == "downloading":
                progress.update(
                    task_id, description=f"Downloading {spec.display_name} binary...", completed=10.0
                )
            elif stage == "verifying":
                progress.update(task_id, description=f"Verifying {spec.display_name} binary...", completed=95.0)
            elif stage == "verifying_checksum":
                progress.update(task_id, description=f"Verifying {spec.display_name} checksum...", completed=92.0)
            elif stage == "done":
                progress.update(task_id, description="Install complete.", completed=100.0)
            elif stage == "already_installed":
                progress.update(task_id, description="Version already installed.", completed=100.0)

        def on_download(total_bytes: int | None, downloaded_bytes: int) -> None:
            if total_bytes and total_bytes > 0:
                ratio = min(downloaded_bytes / total_bytes, 1.0)
                progress_pct = 10.0 + (ratio * 80.0)
                progress.update(
                    task_id, description=f"Downloading {spec.display_name} binary...", completed=progress_pct
                )
                return
            # Unknown content length: keep moving the bar while showing bytes received.
            task = progress.tasks[task_id]
            next_progress = task.completed + 1.0
            if next_progress > 90.0:
                next_progress = 10.0
            progress.update(
                task_id,
                description=f"Downloading {spec.display_name} binary... {decimal(downloaded_bytes)}",
                completed=next_progress,
            )

        return installer.install(version, tool=spec.name, on_status=on_status, on_download=on_download)


def _render_exec_help() -> None:
    console.print()
    console.print("Usage: opavm exec -- <opa-args>")
    console.print("Resolves OPA version (.opa-version > global default) and forwards args.")
    console.print()
    console.print("Examples")
    console.print("opavm exec -- version")
    console.print("opavm exec -- test -v ./policy")
    console.print('opavm exec -- eval -i input.json -d policy.rego "data.example.allow"')
    console.print()

    table = Table(title="Available OPA Commands", box=box.SIMPLE_HEAVY, show_header=True)
    table.add_column("Command", style="cyan")
    table.add_column("Description")
    for command, description in OPA_COMMANDS:
        table.add_row(command, description)
    console.print(table)


@app.command()
def install(
    subject: str = typer.Argument(..., help="Version for OPA, or tool name like `regal`."),
    version: str | None = typer.Argument(None, help="Version when tool is provided."),
    tool: str | None = typer.Option(
        None,
        "--tool",
        "-t",
        help="[cyan]Target tool[/cyan]: `opa` or `regal`.",
        rich_help_panel="Tool Selection",
    ),
) -> None:
    """Install OPA or Regal.

    [bold cyan]Examples[/]
    [green]opavm install 1.13.1[/green]
    [green]opavm install latest[/green]
    [green]opavm install regal 0.38.1[/green]
    [green]opavm install 0.38.1 --tool regal[/green]
    """
    try:
        spec, target_version = _resolve_install_target_with_option(subject, version, tool)
        resolved = _install_with_progress(spec.name, target_version)
        if spec.name == "opa":
            shim_path = shim.ensure_shim()
    except OpavmError as err:
        _handle_error(err)
    console.print(f"Installed {spec.display_name} {resolved}.")
    if spec.name == "opa":
        console.print(f"Shim ready at {shim_path}.")
    else:
        console.print(f"Binary path: {installer.binary_path(resolved, tool=spec.name)}")


@app.command("list")
def list_versions(
    tool: str = typer.Option(
        "opa",
        "--tool",
        "-t",
        help="Tool to list: `opa` or `regal`.",
        rich_help_panel="Tool Selection",
    ),
) -> None:
    """List installed tool versions."""
    try:
        spec = catalog.get_tool(tool)
    except OpavmError as err:
        _handle_error(err)
    versions = installer.installed_versions(tool=spec.name)
    if not versions:
        if spec.name == "opa":
            console.print("No installed versions. Run: opavm install latest")
        else:
            console.print(f"No installed {spec.display_name} versions. Run: opavm install {spec.name} latest")
        return
    for version in versions:
        console.print(version)


@app.command()
def use(version: str) -> None:
    """Set global default OPA version."""
    try:
        if not installer.is_installed(version):
            raise VersionNotInstalledError(
                "Version not installed.", f"Run: opavm install {version}"
            )
        config.save_state({"global_default": version})
    except OpavmError as err:
        _handle_error(err)
    console.print(f"Global default set to {version}.")


@app.command()
def pin(version: str) -> None:
    """Pin OPA version for current project."""
    try:
        pinned_version = version
        if not installer.is_installed(version):
            should_install = typer.confirm(
                f"Version {version} is not installed. Install now?", default=True
            )
            if not should_install:
                raise VersionNotInstalledError(
                    "Version not installed.", f"Run: opavm install {version}"
                )
            pinned_version = _install_with_progress("opa", version)
        pin_file = Path.cwd() / ".opa-version"
        pin_file.write_text(f"{pinned_version}\n", encoding="utf-8")
    except OpavmError as err:
        _handle_error(err)
    console.print(f"Pinned {pinned_version} in {pin_file}.")


@app.command()
def current() -> None:
    """Show active OPA version and resolution reason."""
    try:
        version, reason = resolver.resolve_version(Path.cwd())
    except OpavmError as err:
        _handle_error(err)
    console.print(f"{version} ({reason})")


@app.command()
def which() -> None:
    """Print resolved OPA binary path."""
    try:
        _, _, binary = runner.resolved_binary_path(Path.cwd())
    except OpavmError as err:
        _handle_error(err)
    typer.echo(str(binary.resolve()))


@app.command(
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
        "help_option_names": [],
    }
)
def exec(ctx: typer.Context) -> None:
    """Run OPA through resolved version and forward args."""
    if len(ctx.args) == 1 and ctx.args[0] in {"-h", "--help", "help"}:
        _render_exec_help()
        raise typer.Exit(code=0)

    try:
        _, _, binary = runner.resolved_binary_path(Path.cwd())
    except OpavmError as err:
        _handle_error(err)

    cmd = [str(binary), *ctx.args]
    try:
        proc = subprocess.run(cmd)
    except OSError as exc:
        _handle_error(OpavmError("Failed to execute OPA.", str(exc)))
    raise typer.Exit(proc.returncode)


@app.command()
def uninstall(
    version: str,
    tool: str = typer.Option(
        "opa",
        "--tool",
        "-t",
        help="Tool to uninstall: `opa` or `regal`.",
        rich_help_panel="Tool Selection",
    ),
) -> None:
    """Uninstall a specific tool version."""
    try:
        spec = catalog.get_tool(tool)
        installer.uninstall(version, tool=spec.name)
    except OpavmError as err:
        _handle_error(err)
    console.print(f"Uninstalled {spec.display_name} {version}.")


@app.command("releases")
def releases(
    limit: int = typer.Option(10, "--limit", min=1, help="Number of recent releases"),
    tool: str = typer.Option(
        "opa",
        "--tool",
        "-t",
        help="Tool releases to show: `opa` or `regal`.",
        rich_help_panel="Tool Selection",
    ),
) -> None:
    """Show recent tool releases from GitHub."""
    try:
        spec = catalog.get_tool(tool)
        repo = github.configured_repo(env_var=spec.repo_env_var, default_repo=spec.default_repo)
        releases_data = github.fetch_recent_releases(limit=limit, repo=repo)
    except OpavmError as err:
        _handle_error(err)

    console.print()
    console.print(f"{spec.display_name} Releases")
    console.print(f"https://github.com/{repo}/releases")
    console.print()

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
    table.add_column("Version", style="cyan")
    table.add_column("Tag")
    table.add_column("Published")
    table.add_column("Pre-release", justify="center")

    for item in releases_data:
        published = item.published_at[:10] if item.published_at else "-"
        table.add_row(item.version, item.tag, published, "yes" if item.prerelease else "no")

    console.print(table)
