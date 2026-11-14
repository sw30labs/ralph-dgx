# ADR-0005: Reach local vLLM through dcode's `openai` provider with the Responses API forced off

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

dcode has no separate vLLM backend. vLLM serves `/v1/chat/completions`, not `/v1/responses`, and deepagents' built-in openai profile may set `use_responses_api=True` (README "How the vLLM provider works"; common.sh comments). Passing `use_responses_api` through to the request raises `TypeError: AsyncCompletions.create() got an unexpected keyword argument` (model_param_filter.py docstring).

## Decision

The `vllm` provider maps to model spec `openai:${VLLM_MODEL}` (default `Qwen/Qwen3-Coder-Next-FP8` at `http://127.0.0.1:8000/v1`, 131072 max input tokens). `use_responses_api = false` is set in three places so it outranks the profile: `~/.deepagents/config.toml` provider params (`write_deepagents_config.py`), `--model-params '{"use_responses_api": false}'` from `run_dcode` (caller args appended last so they can override), and the ChatOpenAI constructor. The overlay `model_param_filter.invoke_model_params` strips constructor-only keys (`use_responses_api`, `base_url`, `api_key`, `timeout`, `max_retries`, `model_kwargs`, …) and `__deepagents*` sentinels, and `patch_configurable_model.py` uses it so only wire-level kwargs are merged into `model_settings`. Stream chunk timeout defaults to 600 s for long local prefills.

## Consequences

### Positive

- Local vLLM and cloud OpenAI share one code path (langchain-openai).
- The TypeError class of failures is covered by unit tests.

### Negative

- Three layers must agree; a future upstream default could need a fourth.
- The constructor-only key list is hand-maintained.

## Alternatives considered

- Use the Responses API (not possible against vLLM).
- Add a dedicated vLLM provider to dcode (not chosen; inferred).

## Evidence

- README.md (How the vLLM provider works)
- scripts/lib/common.sh (model_spec, model_params_spec, configure_vllm_defaults, run_dcode)
- scripts/write_deepagents_config.py
- scripts/ralph_overlay/deepagents_code/model_param_filter.py
- scripts/ralph_patch/patch_configurable_model.py
- tests/test_model_param_filter.py
- tests/test_common_sh.py
- commit 6b36a35
