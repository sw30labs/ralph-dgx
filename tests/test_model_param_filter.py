"""Unit tests for constructor vs invoke model-param splitting."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILTER_PATH = (
    ROOT / "scripts" / "ralph_overlay" / "deepagents_code" / "model_param_filter.py"
)


def _load_filter():
    spec = importlib.util.spec_from_file_location("model_param_filter", FILTER_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_strips_use_responses_api() -> None:
    mod = _load_filter()
    out = mod.invoke_model_params(
        {"use_responses_api": False, "temperature": 0.2, "max_tokens": 128}
    )
    assert out == {"temperature": 0.2, "max_tokens": 128}
    assert "use_responses_api" not in out


def test_strips_constructor_and_internal_keys() -> None:
    mod = _load_filter()
    out = mod.invoke_model_params(
        {
            "use_responses_api": False,
            "base_url": "http://127.0.0.1:8000/v1",
            "api_key": "test",
            "timeout": 600,
            "max_retries": 3,
            "__deepagents_cli_max_retries__": 5,
            "__deepagents_other__": "x",
            "temperature": 0.0,
        }
    )
    assert out == {"temperature": 0.0}


def test_empty_and_none() -> None:
    mod = _load_filter()
    assert mod.invoke_model_params(None) == {}
    assert mod.invoke_model_params({}) == {}
