# ADR-0013: Secrets live only in a gitignored `.env`; generated config stores env-var names, not keys

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

The upgrade prompt says "Keep local secrets out of git. Do not commit `.env`". README says `.env` (gitignored) holds provider settings.

## Decision

`.gitignore` excludes `.env`, `backups/`, `logs/`, the venvs and generated trees. `write_deepagents_config.py` writes `api_key_env = "VLLM_API_KEY"` or `"OPENAI_API_KEY"` and states the key is "never stored here"; install `chmod 600`s `~/.deepagents/config.toml`. `load_project_env` sources `.env` with `set -a` and lets an explicit `--provider` override `DEEPAGENTS_MODEL_PROVIDER` from `.env`. The update workflow backs up `.env` only as a sed-redacted copy. `setup-and-run.sh` creates `.env` from `.env.example` when missing.

## Consequences

### Positive

- Keys do not end up in the repo, config.toml or backups.

### Negative

- Redaction is a regex on `*API_KEY|TOKEN|SECRET|PASSWORD=` lines; other secret-bearing names would be copied in clear into the (gitignored) backup.
- `.env` is sourced as shell, so it must be trusted.

## Alternatives considered

- Store keys in config.toml (rejected in the generated comments).

## Evidence

- .gitignore
- scripts/write_deepagents_config.py
- scripts/ralph_install.sh (chmod 600)
- scripts/lib/common.sh (load_project_env)
- run-ralph-update-langgraph.sh (env.redacted)
- setup-and-run.sh
- docs/upgradeLangGraphDeepAgentsStackSafely.md
