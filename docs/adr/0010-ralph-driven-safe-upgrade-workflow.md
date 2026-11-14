# ADR-0010: Ralph-driven safe upgrade workflow: back up, require a done verdict, validate, refresh constraints, commit

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

Stack upgrades (DeepAgents, LangGraph, LangChain, langchain-openai) are frequent; the repo was created so "the LangGraph/DeepAgents safe-update workflow can track and commit validated dependency upgrades" (commit 070413f).

## Decision

`./ralphdgx update` execs `run-ralph-update-langgraph.sh`. It requires a non-empty Markdown prompt with a top-level heading (default `docs/upgradeLangGraphDeepAgentsStackSafely.md`), loads `.env`, requires a git repo, and copies `constraints.txt`, `.env.example`, a redacted `.env` (`API_KEY|TOKEN|SECRET|PASSWORD=` → `REDACTED`), all repo `*.toml` and `~/.deepagents/config.toml` into `backups/last-known-good/<UTC timestamp>/`. It then runs `daz-ralph` with the prompt, `--goal-budget 50`, `--no-mcp` and `--auto-approve` by default ("This wrapper runs headless, so the TUI's tool-approval prompt would block forever"). Unless `RALPH_UPDATE_REQUIRE_DONE=false`, it stops if the last iteration-log line is not `done: true`. Then it runs `./setup-and-run.sh --vllm --no-run`, writes `pip freeze --exclude-editable` to `constraints.txt`, and `git add .` + commit if anything changed. The prompt defines done criteria (bash -n, py_compile, `dcode --version`, provider smoke test, setup validate, backup dir, commit) and evidence to report.

## Consequences

### Positive

- Upgrades are reproducible and leave a last-known-good copy.
- Validation and commit only happen after the judge's final done=true.

### Negative

- Runs with auto-approve and commits `git add .`, so anything not gitignored is committed (A-013).
- The raw freeze can diverge from the prompt's pinning rule (A-004).
- The TUI may not exit after done=true (TODO-ROADMAP P7, A-016).

## Alternatives considered

- Manual upgrades by hand (what the workflow replaces).
- Upstream `dcode -n` + `--rubric` headless mode (TODO-ROADMAP P7, not adopted).

## Evidence

- run-ralph-update-langgraph.sh
- ralphdgx (cmd_update)
- docs/upgradeLangGraphDeepAgentsStackSafely.md
- README.md (Update Workflow Sequence Diagram)
- commits 070413f, 0bb06e8, 6b36a35, aec24c3
