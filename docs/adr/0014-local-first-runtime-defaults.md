# ADR-0014: Local-first runtime defaults: tracing and update checks off, debug log on, MCP off

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

The tool runs on a single workstation against a local model. No rationale beyond the code is recorded for most of these defaults.

## Decision

`configure_deepagents_defaults` sets (unless already set) LangSmith/LangChain tracing off, `DEEPAGENTS_CODE_NO_UPDATE_CHECK=1`, `DEEPAGENTS_CODE_DEBUG=1` writing to `/tmp/deepagents_debug.log`, `DEEPAGENT_REASONING_EFFORT=xhigh`, `DEEPAGENT_APPROVE_SHELL=true`, `DEEPAGENT_APPROVE_WRITES=true`, and `DAZ_RALPH_LOG_DIR=<repo>/logs/ralph`. Generated config.toml disables update checks/auto-update and suppresses the tavily warning. `run_dcode` always passes `--no-mcp`; the update workflow defaults `RALPH_UPDATE_NO_MCP=true`.

## Consequences

### Positive

- No traces or telemetry leave the box by default.
- Debug logs and Ralph run logs are available for troubleshooting.

### Negative

- The debug log in /tmp is on by default and may contain prompt or tool content (A-015).
- Exact semantics of the APPROVE_* variables are upstream-defined and were not verified (A-014).

## Alternatives considered

- Upstream defaults (tracing/update checks as shipped).

## Evidence

- scripts/lib/common.sh (configure_deepagents_defaults, run_dcode)
- scripts/write_deepagents_config.py
- run-ralph-update-langgraph.sh (NO_MCP)
