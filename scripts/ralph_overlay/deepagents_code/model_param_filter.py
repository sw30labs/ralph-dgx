"""Split CLI/config model params into constructor vs invoke kwargs.

`--model-params` and config.toml provider params are fed to `create_model` as
constructor kwargs (correct for ChatOpenAI fields like `use_responses_api`).
They are also stashed on CLI context and re-merged into each request's
`model_settings`, which LangChain binds onto the generation call.

Constructor-only fields must not reach `openai.AsyncCompletions.create()` —
that raises:

    TypeError: AsyncCompletions.create() got an unexpected keyword argument
    'use_responses_api'

Ralph uses `use_responses_api=false` so local vLLM (chat-completions only)
is not routed to the Responses API.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# ChatOpenAI / client construction keys — not Completions.create payload.
CONSTRUCTOR_ONLY_MODEL_PARAMS: frozenset[str] = frozenset(
    {
        "use_responses_api",
        "use_previous_response_id",
        "base_url",
        "api_key",
        "organization",
        "openai_api_key",
        "openai_api_base",
        "openai_organization",
        "openai_proxy",
        "timeout",
        "max_retries",
        "default_headers",
        "default_query",
        "http_client",
        "http_async_client",
        "tiktoken_model_name",
        "stream_usage",
        "disabled_params",
        "include_response_headers",
        "output_version",
        "stream_chunk_timeout",
        "model_kwargs",
        # Internal CLI sentinel carried for create_model only (see config.py).
        "__deepagents_cli_max_retries__",
    }
)


def invoke_model_params(model_params: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return per-call model_settings kwargs from a model_params mapping.

    Drops constructor-only fields and any `__deepagents*` internal sentinels
    so they are never bound into the OpenAI (or other provider) wire call.
    """
    if not model_params:
        return {}
    return {
        key: value
        for key, value in model_params.items()
        if key not in CONSTRUCTOR_ONLY_MODEL_PARAMS
        and not (isinstance(key, str) and key.startswith("__deepagents"))
    }
