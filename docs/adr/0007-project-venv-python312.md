# ADR-0007: Install and run from a project-local `.venv`, preferring Python 3.12

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

The DGX also hosts system Python. The upgrade prompt says "Prefer the project `.venv` (Python 3.12). Do not install into system Python"; common.sh says "The project venv keeps DeepAgents off the system Python on this DGX".

## Decision

`ensure_project_venv` creates `<repo>/.venv` with `python3.12` (else `python3`) and upgrades pip. `resolve_python` order: `PIP_PYTHON_BIN`, `RALPHDGX_PYTHON`, `<repo>/.venv/bin/python`, then python3.12 / python3. `setup-and-run.sh` and `ralph_install.sh` call `ensure_project_venv` unless a Python is forced. common.sh puts `.venv/bin` and `~/.local/bin` first on PATH.

## Consequences

### Positive

- DeepAgents upgrades cannot break other tools on the host.
- `./ralphdgx install` stays idempotent (an existing venv is reused).

### Negative

- Python 3.12 preference is a convention, not enforced: a plain python3 of another version is accepted if 3.12 is missing.

## Alternatives considered

- System or conda Python directly (README notes micromamba-only install is not included).
- uv-managed environments (not chosen; no rationale recorded).

## Evidence

- scripts/lib/common.sh (resolve_python, ensure_project_venv)
- setup-and-run.sh
- scripts/ralph_install.sh
- docs/upgradeLangGraphDeepAgentsStackSafely.md (Required Safety Rules)
- README.md (Installs land in ./.venv)
