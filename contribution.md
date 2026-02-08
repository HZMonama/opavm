# Contributing

Thanks for contributing to `opavm`.

## Prerequisites

- Python 3.10+
- `pip` or `pipx`

## Setup

```bash
pip install -e .[dev]
```

## Local validation

Run these before opening a PR:

```bash
ruff check .
pytest -q
```

Coverage is enforced via `pytest-cov` (`--cov-fail-under=70`) and produces `coverage.xml`.

## Testing and quality gates

- Lint: `ruff check .`
- Tests: `pytest -q`
- Coverage gate: `--cov-fail-under=70`
- Coverage artifact: `coverage.xml` (uploaded by CircleCI)

The coverage threshold is an enforced floor and should be raised as test depth increases.

## CircleCI (CI and release)

This repo uses CircleCI for CI and publishing.

### Validate CI config

```bash
circleci config validate .circleci/config.yml
```

### Run CI locally

Run the main CI job locally (Docker executor):

```bash
circleci local execute lint-test
```

### Release flow

- Tag push `vX.Y.Z` triggers the `release` workflow.
- Publish job requires CircleCI context `pypi` with `PYPI_API_TOKEN`.
- Version is derived from git tags via `setuptools-scm`; do not manually bump version fields for releases.

## Pull request expectations

- Keep changes scoped and focused.
- Add or update tests for behavior changes.
- Preserve actionable user-facing errors.
- Update `README.md` when command behavior or flags change.

## Release checklist

1. Ensure CI passes.
2. Create/push release tag on the target commit:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

3. Confirm CircleCI context `pypi` contains `PYPI_API_TOKEN`.
