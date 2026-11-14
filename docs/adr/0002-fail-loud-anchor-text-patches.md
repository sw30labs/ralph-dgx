# ADR-0002: Text-anchor patches that apply exactly once and fail loudly when upstream changes

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

The Ralph changes have to land inside upstream files (`agent.py`, `configurable_model.py`, `_server_config.py`, `server_graph.py`, `client/launch/server_manager.py`, `pyproject.toml`, `system_prompt.md`) that change between deepagents-code releases. Comments in the patch modules reference re-deriving anchors for 0.1.27, and commit 0bb06e8 records patch updates "for new agent_middleware structure" and "new _apply_overrides signature".

## Decision

Patches are plain-text replacements through `_shared.replace_once(path, old, new)`: it is a no-op if `new` (or an `already` marker) is already present, otherwise it requires `old` to exist and replaces only the first occurrence; a missing anchor raises `SystemExit("expected Ralph patch anchor not found ...")`. Whole overlay packages/files are copied with `copy_tree`/`copy_file`, which also fail if the source is missing. `ralph_patch.main` copies overlays first, then patches agent, configurable model, server config/graph/manager and pyproject in a fixed order.

## Consequences

### Positive

- Idempotent: re-running the patch on an already patched tree is safe.
- An upstream change surfaces as an explicit install failure naming the file and anchor, not as a silently unpatched CLI.

### Negative

- Anchors are verbatim multi-line code blocks; whitespace or comment changes upstream break them.
- No semantic check that a patch still does what it did; that relies on the verify block in ralph_install.sh and the smoke tests.

## Alternatives considered

- git/diff patch files (not chosen; no rationale recorded).
- Monkey-patching at runtime (not chosen; inferred).

## Evidence

- scripts/ralph_patch/_shared.py
- scripts/ralph_patch/patch_agent.py
- scripts/ralph_patch/patch_configurable_model.py
- scripts/ralph_patch/patch_server.py
- scripts/ralph_patch/patch_pyproject.py
- scripts/ralph_patch/copy_overlays.py
- commit 0bb06e8 message
