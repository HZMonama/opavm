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
        "Use [cyan]--tool[/cyan] on tool-aware commands: "
        "[green]install[/green], [green]list[/green], [green]use[/green], [green]pin[/green], "
        "[green]current[/green], [green]which[/green], [green]exec[/green], "
        "[green]uninstall[/green], [green]releases[/green].\n"
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


def _render_exec_help(spec: catalog.ToolSpec) -> None:
    console.print()
    if spec.name == "opa":
        console.print("Usage: opavm exec -- <opa-args>")
    else:
        console.print(f"Usage: opavm exec --tool {spec.name} -- <{spec.name}-args>")
    console.print(
        f"Resolves {spec.display_name} version ({spec.pin_filename} > global default) and forwards args."
    )
    console.print()
    console.print("Examples")
    if spec.name == "opa":
        console.print("opavm exec -- version")
        console.print("opavm exec -- test -v ./policy")
        console.print('opavm exec -- eval -i input.json -d policy.rego "data.example.allow"')
    else:
        console.print("opavm exec --tool regal -- version")
        console.print("opavm exec --tool regal -- lint policy/")
    console.print()

    if spec.name == "opa":
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
def use(
    version: str,
    tool: str = typer.Option(
        "opa",
        "--tool",
        "-t",
        help="Tool to set global default for: `opa` or `regal`.",
        rich_help_panel="Tool Selection",
    ),
) -> None:
    """Set global default tool version."""
    try:
        spec = catalog.get_tool(tool)
        if not installer.is_installed(version, tool=spec.name):
            install_hint = (
                f"Run: opavm install {version}"
                if spec.name == "opa"
                else f"Run: opavm install {spec.name} {version}"
            )
            raise VersionNotInstalledError(
                "Version not installed.",
                install_hint,
            )
        config.set_global_default(spec.name, version)
    except OpavmError as err:
        _handle_error(err)
    console.print(f"Global default for {spec.display_name} set to {version}.")


@app.command()
def pin(
    version: str,
    tool: str = typer.Option(
        "opa",
        "--tool",
        "-t",
        help="Tool to pin in current project: `opa` or `regal`.",
        rich_help_panel="Tool Selection",
    ),
) -> None:
    """Pin tool version for current project."""
    try:
        spec = catalog.get_tool(tool)
        pinned_version = version
        if not installer.is_installed(version, tool=spec.name):
            should_install = typer.confirm(
                f"{spec.display_name} version {version} is not installed. Install now?",
                default=True,
            )
            if not should_install:
                install_hint = (
                    f"Run: opavm install {version}"
                    if spec.name == "opa"
                    else f"Run: opavm install {spec.name} {version}"
                )
                raise VersionNotInstalledError(
                    "Version not installed.",
                    install_hint,
                )
            pinned_version = _install_with_progress(spec.name, version)
        pin_file = Path.cwd() / spec.pin_filename
        pin_file.write_text(f"{pinned_version}\n", encoding="utf-8")
    except OpavmError as err:
        _handle_error(err)
    console.print(f"Pinned {spec.display_name} {pinned_version} in {pin_file}.")


@app.command()
def current(
    tool: str = typer.Option(
        "opa",
        "--tool",
        "-t",
        help="Tool to resolve current version for: `opa` or `regal`.",
        rich_help_panel="Tool Selection",
    ),
) -> None:
    """Show active tool version and resolution reason."""
    try:
        spec = catalog.get_tool(tool)
        version, reason = resolver.resolve_version(Path.cwd(), tool=spec.name)
    except OpavmError as err:
        _handle_error(err)
    console.print(f"{spec.display_name} {version} ({reason})")


@app.command()
def which(
    tool: str = typer.Option(
        "opa",
        "--tool",
        "-t",
        help="Tool to print binary path for: `opa` or `regal`.",
        rich_help_panel="Tool Selection",
    ),
) -> None:
    """Print resolved tool binary path."""
    try:
        spec = catalog.get_tool(tool)
        _, _, binary = runner.resolved_binary_path(Path.cwd(), tool=spec.name)
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
def exec(
    ctx: typer.Context,
    tool: str = typer.Option(
        "opa",
        "--tool",
        "-t",
        help="Tool to execute: `opa` or `regal`.",
        rich_help_panel="Tool Selection",
    ),
) -> None:
    """Run tool through resolved version and forward args."""
    try:
        spec = catalog.get_tool(tool)
    except OpavmError as err:
        _handle_error(err)

    if len(ctx.args) == 1 and ctx.args[0] in {"-h", "--help", "help"}:
        _render_exec_help(spec)
        raise typer.Exit(code=0)

    try:
        _, _, binary = runner.resolved_binary_path(Path.cwd(), tool=spec.name)
    except OpavmError as err:
        _handle_error(err)

    cmd = [str(binary), *ctx.args]
    try:
        proc = subprocess.run(cmd)
    except OSError as exc:
        _handle_error(OpavmError(f"Failed to execute {spec.display_name}.", str(exc)))
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
        repo = spec.default_repo
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
