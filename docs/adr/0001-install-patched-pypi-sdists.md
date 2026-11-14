# ADR-0001: Install DeepAgents by downloading pinned PyPI sdists and patching them, not by forking the source

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

ralphdgx needs a DeepAgents Code CLI (`dcode`) that carries the Ralph/tenacity goal loop and DGX-specific fixes. The initial commit describes the repo as a "DGX/vLLM installer and overlays" baseline "so the LangGraph/DeepAgents safe-update workflow can track and commit validated dependency upgrades". CLAUDE.md states it is "Not the DeepAgents source tree".

## Decision

`scripts/ralph_install.sh` deletes and recreates `deepagents-sdists/` and `deepagents-main/`, runs `pip download --no-binary :all: --no-deps` for exact pins (`deepagents==0.7.0a7`, `deepagents-acp==0.0.9`, `deepagents-code==0.1.43`), lays them out under `deepagents-main/libs/{deepagents,acp,code}` with `scripts/extract_sdists.py` (tar `filter="data"`), applies the Ralph patch (`python -m ralph_patch.main`), installs the patched trees with pip, writes `~/.deepagents/config.toml`, and verifies versions, overlay imports and `pip check`. Both generated trees are gitignored; the committed sources of truth are `scripts/ralph_patch/`, `scripts/ralph_overlay/` and the DGX helper scripts.

## Consequences

### Positive

- Upgrading means changing three pins plus re-deriving patch anchors; there is no fork to rebase.
- Every install starts from a clean download, so the result is reproducible from the repo plus PyPI.
- The repo stays small: only overlays, patches and shell/Python helpers are tracked.

### Negative

- Each install needs network access to the configured pip index; sdists are not hash-pinned.
- Upstream sdist layout changes (package names, pyproject anchors) break the install until patches are updated.

## Alternatives considered

- Vendor or fork the DeepAgents monorepo (not chosen; README and CLAUDE.md say generated trees are not committed).
- Install upstream wheels unmodified (would lose the goal loop and vLLM fixes).

## Evidence

- scripts/ralph_install.sh
- scripts/extract_sdists.py
- scripts/ralph_patch/main.py
- .gitignore (deepagents-sdists/, deepagents-main/)
- README.md (Architecture)
- CLAUDE.md (What this repo is)
- commit 070413f (initial commit message)
- commit 0bb06e8 (pin bump 0.7.0a2→0.7.0a7)
