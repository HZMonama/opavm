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

## CI validation (CircleCI)

Validate config:

```bash
circleci config validate .circleci/config.yml
```

Run the main CI job locally:

```bash
circleci local execute lint-test
```

## Pull request expectations

- Keep changes scoped and focused.
- Add or update tests for behavior changes.
- Preserve actionable user-facing errors.
- Update `README.md` when command behavior or flags change.

## Release notes

For package releases:

1. Bump version in:
   - `pyproject.toml`
   - `src/opavm/__init__.py`
2. Ensure CI passes.
3. Ensure CircleCI context `pypi` contains `PYPI_API_TOKEN`.
4. Push a tag like `v0.1.1` to trigger publish workflow.
