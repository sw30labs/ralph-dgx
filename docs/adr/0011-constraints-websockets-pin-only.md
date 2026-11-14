# ADR-0011: `constraints.txt` is a validated-env reference; only its `websockets==` pin is enforced at install

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

The upgrade prompt explains that `langsmith` requires `websockets>=15` with no upper bound and could float websockets to 16.0 during eager upgrades, tripping `langgraph-sdk`'s `websockets<16`; it says the full file "is deliberately *not* wired in during a version bump". The constraints header says it is "fresh resolver output from a validated ralph-deepagents env (Python 3.12) … not hand-edited", with deepagents-* pinned "for reference".

## Decision

`ralph_install.sh` greps the `websockets==` line from `constraints.txt` into a temp file and passes only that as `--constraint` to its `pip install --upgrade --upgrade-strategy eager` steps. The rest of `constraints.txt` (about 140 pins at reviewed HEAD) is regenerated after a validated upgrade and kept for reference. The prompt says to pin `deepagents*` by version (`==x.y.z`), not by `file://` path, and to "prefer a fresh resolver output" over impossible exact pins.

## Consequences

### Positive

- Eager upgrades still pick up new compatible versions while avoiding the one known conflict.

### Negative

- Installs are not fully reproducible from `constraints.txt`; transitive versions float.
- How the file is regenerated is ambiguous (A-004).

## Alternatives considered

- Apply the full constraints file on install (rejected in the prompt during version bumps).
- No constraints at all (rejected because of the websockets conflict).

## Evidence

- scripts/ralph_install.sh (PIP_CONSTRAINT_ARGS)
- constraints.txt (header)
- docs/upgradeLangGraphDeepAgentsStackSafely.md (Update Work step 3)
- commits 0bb06e8, 6b36a35, aec24c3 (constraints regenerated)
