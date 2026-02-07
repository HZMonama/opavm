from __future__ import annotations

from pathlib import Path

from opavm import config, platform


def ensure_shim() -> Path:
    config.ensure_layout()
    os_name, _ = platform.normalized_os_arch()

    if os_name == "windows":
        shim_path = config.shims_dir() / "opa.cmd"
        if shim_path.exists():
            return shim_path
        content = """@echo off
for /f "delims=" %%i in ('opavm which') do set "OPA_BIN=%%i"
"%OPA_BIN%" %*
"""
        shim_path.write_text(content, encoding="utf-8")
        return shim_path

    shim_path = config.shims_dir() / "opa"
    if shim_path.exists():
        return shim_path
    content = """#!/usr/bin/env sh
set -eu
resolved="$(opavm which)"
exec "$resolved" "$@"
"""
    shim_path.write_text(content, encoding="utf-8")
    shim_path.chmod(shim_path.stat().st_mode | 0o111)
    return shim_path


def path_instruction() -> str:
    os_name, _ = platform.normalized_os_arch()
    if os_name == "windows":
        return f'$env:Path = "{config.shims_dir()};$env:Path"'
    return f'export PATH="{config.shims_dir()}:$PATH"'
