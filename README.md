# opavm

A dead-simple version manager for Open Policy Agent (OPA).

`opavm` lets you install, pin, and switch OPA versions locally and per-project so your policies run against the same OPA version in dev, CI, and production.
No Docker. No magic. Just predictable binaries.

## Why opavm exists

OPA is "just a single binary" until it isn't.
Teams regularly run into:

- different OPA versions in CI vs local
- silent upgrades via package managers
- subtle behavior changes across releases
- ad-hoc scripts and manual downloads

`opavm` solves this by making OPA versioning explicit, reproducible, and boring.

## Features (v0.1)

- Install specific OPA versions (or `latest`)
- Install Regal (Rego linter/LSP) versions
- Set a global default version per tool (`opa` / `regal`)
- Pin per project with `.opa-version` or `.regal-version`
- Automatically switch versions by directory
- CI-safe execution without PATH hacks
- Rich progress bar UI for installs
- Show recent OPA/Regal releases in a Rich table (`opavm releases`)
- Zero runtime services, zero configuration files

## Installation

v0.1 supports:

- macOS (`amd64`, `arm64`)
- Linux (`amd64`, `arm64`)
- Windows (`amd64`)

Install as a Python package (recommended with `pipx`):

```bash
pipx install opavm
```

Or with `pip`:

```bash
pip install opavm
```

Then add the shim directory to your shell.

macOS/Linux:

```bash
export PATH="$HOME/.opavm/shims:$PATH"
```

Windows PowerShell:

```powershell
$env:Path = "$HOME\.opavm\shims;$env:Path"
```

## GitHub API token

`opavm` uses fixed upstream repos:

- `open-policy-agent/opa` for OPA release lookup
- `StyraInc/regal` for Regal release lookup

If you hit GitHub API rate limits, set `OPAVM_GITHUB_TOKEN`.

## Quick start

Install OPA:

```bash
opavm install 0.62.1
```

Set a global default:

```bash
opavm use 0.62.1
opavm use 0.38.1 --tool regal
```

Now:

```bash
opa version
```

uses OPA `0.62.1`.

## Per-project pinning

Inside a repo that requires a specific version:

```bash
opavm pin 0.61.0
opavm pin 0.38.1 --tool regal
```

If that version is not installed, `opavm` prompts to install it.

This creates tool-specific version files:

```text
.opa-version   # OPA
.regal-version # Regal
```

Anywhere inside that repo:

```bash
opa version
```

automatically resolves to `0.61.0`.
Outside the repo, your global version is used again.

## Common commands

Install versions:

```bash
opavm install 0.62.1
opavm install latest
opavm install regal 0.38.1
opavm install regal latest
```

List installed versions:

```bash
opavm list
opavm list --tool regal
```

Switch global version:

```bash
opavm use 0.63.0
opavm use 0.38.1 --tool regal
```

See what's active (and why):

```bash
opavm current
opavm current --tool regal
```

Get the actual binary path:

```bash
opavm which
opavm which --tool regal
```

`opavm which` prints the resolved binary as an absolute path.

Show recent OPA releases:

```bash
opavm releases --limit 10
opavm releases --tool regal --limit 10
```

Run OPA without relying on PATH (CI-safe):

```bash
opavm exec -- test -v ./policy
opavm exec --tool regal -- lint policy/
```

Remove a version:

```bash
opavm uninstall 0.59.0
opavm uninstall 0.38.1 --tool regal
```

## How version resolution works

When you resolve a tool with `current`, `which`, or `exec`:

1. Look for the tool pin file in the current directory or parents
2. Use `.opa-version` for OPA, `.regal-version` for Regal
3. If found, use that version
4. Otherwise, use the global default for that tool
5. If neither exists, error with guidance

This behavior is deterministic and transparent.

## File layout

```text
~/.opavm/
|- versions/
|  |- 0.62.1/opa
|  `- 0.63.0/opa
|- tools/
|  `- regal/
|     `- versions/
|        `- 0.38.1/regal
|- shims/
|  `- opa (or opa.cmd on Windows)
`- state.json
```

`.opa-version` and `.regal-version` files live in your project repos and should usually be committed.

## CI usage

You don't need shell shims in CI:

```bash
opavm install 0.62.1
opavm exec -- test ./policy
```

This guarantees the correct OPA version regardless of environment.

## Integrity and Reliability

- `opavm` verifies downloaded binaries by executing `<tool> version` after install.
- For releases that provide `*.sha256` assets (for example OPA), `opavm` validates SHA256 before completing install.
- GitHub error handling includes actionable messages for:
  - proxy misconfiguration (`HTTP_PROXY` / `HTTPS_PROXY`)
  - rate limit exhaustion
  - network connectivity failures
  - auth/permission failures

Contributor workflow, testing gates, and CircleCI release details are in `contribution.md`.

## What opavm is not

- Not a container runtime
- Not a policy runner
- Not a plugin manager

It does one thing: manage OPA binaries predictably.

## License

Apache 2.0.
See `LICENSE` and `license.md`.
