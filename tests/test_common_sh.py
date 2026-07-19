"""Minimal unit checks for ralphdgx provider helpers (no live server)."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / "scripts" / "lib" / "common.sh"


def _bash(script: str) -> str:
    env = os.environ.copy()
    # Isolate from caller's provider overrides.
    for key in list(env):
        if key.startswith("DEEPAGENTS_") or key.startswith("VLLM_") or key.startswith("OPENAI_"):
            env.pop(key, None)
    proc = subprocess.run(
        ["bash", "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
    )
    return proc.stdout.strip()


def test_model_spec_vllm_default() -> None:
    out = _bash(
        f'''
        source "{COMMON}"
        export DEEPAGENTS_MODEL_PROVIDER=vllm
        export VLLM_MODEL=Qwen/Qwen3-Coder-Next-FP8
        model_spec
        '''
    )
    assert out == "openai:Qwen/Qwen3-Coder-Next-FP8"


def test_model_params_vllm_disables_responses_api() -> None:
    out = _bash(
        f'''
        source "{COMMON}"
        export DEEPAGENTS_MODEL_PROVIDER=vllm
        model_params_spec
        '''
    )
    assert "use_responses_api" in out
    assert "false" in out


def test_unsupported_provider_exits() -> None:
    proc = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{COMMON}"; DEEPAGENTS_MODEL_PROVIDER=omlx resolve_provider',
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert proc.returncode != 0
    assert "Unsupported" in proc.stderr
