# ADR-0009: Environment switch to disable synchronous subagents and the `task` tool

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

TODO-ROADMAP says the author's `.env` sets `DEEPAGENTS_CODE_DISABLE_SYNC_SUBAGENTS=true` and that inline subagents block while async ones do not. The rationale for disabling them is not written down beyond that.

## Decision

`patch_agent.py` adds `DISABLE_SYNC_SUBAGENTS_ENV = "DEEPAGENTS_CODE_DISABLE_SYNC_SUBAGENTS"`. When truthy, dcode skips building file-defined subagents and the general-purpose subagent, and registers a deepagents `HarnessProfile(general_purpose_subagent=...enabled=False)` under every key it can derive for the active model (provider, provider:model, detected identifier, raw model string). Otherwise upstream behaviour is unchanged.

## Consequences

### Positive

- Opt-in; default upstream behaviour is preserved.

### Negative

- Profile keys are derived heuristically from several sources; a missed key form would leave the default subagent on.
- Interaction with future async subagents is open (TODO-ROADMAP P6).

## Alternatives considered

- Async subagents (TODO-ROADMAP P6, not done).

## Evidence

- scripts/ralph_patch/patch_agent.py
- TODO-ROADMAP.md (Async / dynamic subagents, P6)
