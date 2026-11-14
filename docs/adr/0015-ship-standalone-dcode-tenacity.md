# ADR-0015: Also ship the standalone `dcode-tenacity` headless graph next to goal mode

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

Before goal mode was wired into the dcode server (ADR-0003), the loop existed as a separate LangGraph package `dcode_tenacity` ("goal loop wrapped around deepagents-code"). It is still copied into the install.

## Decision

`copy_overlays.py` copies `daz_ralph` and `dcode_tenacity` into the deepagents-code project, and `patch_pyproject.py` adds both packages plus console scripts `daz-ralph` and `dcode-tenacity` (`dcode_tenacity.runner:main`, subcommands start/resume/status/clear with a SQLite checkpoint file `DCODE_DB`, default `./dcode_tenacity.sqlite`, gitignored). `dcode_tenacity.graph` is seed → agent → (infra_error | judge) → nudge, stopping after the same `Agent error:` appears twice. The inner agent is resolved from candidate import paths or `DCODE_GRAPH_IMPORT`, falling back to `create_deep_agent`. Its judge defaults to `DCODE_JUDGE_MODEL=anthropic:claude-haiku-4-5-20251001` and its fallback agent to `DCODE_MODEL=anthropic:claude-sonnet-4-6`.

## Consequences

### Positive

- A headless CLI path exists alongside the TUI.
- The repeated-infrastructure-error stop avoids burning turns on a broken environment.

### Negative

- Two loop implementations with different state keys (`turns/done` vs `goal_turns/goal_done`) and defaults.
- Its defaults point at Anthropic models, not the local vLLM (A-005).
- Checkpointer wiring may not persist state (A-006).

## Alternatives considered

- Remove `dcode_tenacity` once goal mode covers it (not done; see Questions).

## Evidence

- scripts/ralph_overlay/dcode_tenacity/*.py
- scripts/ralph_patch/copy_overlays.py
- scripts/ralph_patch/patch_pyproject.py
- .gitignore (dcode_tenacity.sqlite)
- docs/ralph-loop-diagram.md (Expanded Architecture)
