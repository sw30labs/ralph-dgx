# ADR-0004: DGX fork supports only `vllm` and `openai` providers; no OMLX/MLX path

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

ralphdgx is a sibling of the Mac `ralph` repo, which targets Apple Silicon OMLX / Hy3-MLX (README). The target here is Linux aarch64 NVIDIA DGX Spark / GB10. Commit 1a9888a (2026-07-19 09:10 -0400) briefly accepted `omlx` as an alias mapping to local vLLM because shared upgrade prompts call `./ralph test omlx`; commit aec24c3 (10:13 the same morning) removed those aliases "so this fork only exposes vllm and openai paths".

## Decision

`scripts/lib/common.sh` accepts only `vllm` (default) and `openai`; anything else hits `unsupported_provider` ("Expected vllm or openai"). `ralphdgx` is the dispatcher (install, update, test, run, doctor). A thin `./ralph` script stays as a compatibility entry point that execs `./ralphdgx` for shared prompts. The upgrade prompt says "Do not run, invent, or require `omlx` commands". README lists OMLX/MLX, Hy3-MLX and micromamba as "Not included (by design)".

## Consequences

### Positive

- One small provider matrix to test on the DGX.
- Shared prompts that call `./ralph` still work.

### Negative

- Leftover OMLX wording remains in some files (A-009, A-010).
- Mac and DGX repos must be kept in sync by hand.

## Alternatives considered

- Keep an `omlx` alias that maps to vLLM (tried in 1a9888a, reverted in aec24c3).

## Evidence

- scripts/lib/common.sh (normalize_provider, resolve_provider, unsupported_provider)
- ralphdgx
- ralph
- README.md (Not included)
- docs/upgradeLangGraphDeepAgentsStackSafely.md
- tests/test_common_sh.py::test_unsupported_provider_exits
- commits 1a9888a, aec24c3
