# ADR-0006: When the provider is `vllm`, local vLLM always owns OPENAI_BASE_URL / OPENAI_API_KEY

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

Commit 6b36a35 says it forces "local vLLM to own OPENAI_BASE_URL so ambient cloud endpoints cannot hijack smoke tests". common.sh explains that leftover cloud xAI values from a previous shell would route the local model id to the wrong host and fail with "Model not found".

## Decision

`configure_vllm_defaults` unconditionally exports `OPENAI_BASE_URL=$VLLM_BASE_URL` and `OPENAI_API_KEY=$VLLM_API_KEY` (default `test`). `scripts/test-vllm.py` does the same before probing `/models` and requires `VLLM_MODEL` to be in the catalog before a tiny chat call. The `openai` provider leaves `OPENAI_BASE_URL` optional (real OpenAI if unset, any compatible endpoint such as xAI if set).

## Consequences

### Positive

- Smoke tests and runs hit the intended server regardless of the parent shell.

### Negative

- Users cannot point the `vllm` provider at a different OpenAI-compatible host through OPENAI_* (they must change VLLM_BASE_URL).

## Alternatives considered

- Respect ambient OPENAI_* when set (rejected in 6b36a35).

## Evidence

- scripts/lib/common.sh (configure_vllm_defaults, configure_openai_defaults)
- scripts/test-vllm.py
- scripts/test-openai.py
- commit 6b36a35 message
