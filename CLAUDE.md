# CLAUDE.md

Guidance for agents working in **ralphdgx** (DGX / NVIDIA / vLLM fork of Ralph).

## What this repo is

Helper/installer that downloads DeepAgents Code CLI from PyPI, patches it with
the Ralph/tenacity goal-loop overlays, installs into the active Python, and
runs against a **local vLLM** OpenAI-compatible server (default) or cloud OpenAI.

Not the DeepAgents source tree. Generated trees `deepagents-main/` and
`deepagents-sdists/` are gitignored. Source of truth: `scripts/ralph_patch/`,
`scripts/ralph_overlay/`, and the DGX provider scripts.

This is **not** the Mac `ralph` repo: no OMLX, no Hy3/MLX. Target host is
Linux aarch64 NVIDIA (DGX Spark / GB10).

## Common commands

```bash
cp .env.example .env
./ralphdgx doctor
./ralphdgx install
./ralphdgx run                   # default: vllm
./ralphdgx run --provider openai
./ralphdgx test vllm
./ralphdgx test openai
./setup-and-run.sh --vllm
./setup-and-run.sh --vllm --no-run
```

Start the local model (outside this repo, on this DGX):

```bash
~/Desktop/start-vllm.sh
# or: ~/Desktop/serve-local-llm.sh up coder-next
```

## Provider model

- **`vllm`** (default): `VLLM_MODEL` + `VLLM_BASE_URL` → dcode `openai:` provider
  with `use_responses_api=false`. Defaults to `Qwen/Qwen3-Coder-Next-FP8` at
  `http://127.0.0.1:8000/v1`.
- **`openai`**: real OpenAI or any compatible endpoint via `OPENAI_*`.

## Install pipeline

Same as parent ralph: download pinned sdists → extract → `ralph_patch` overlays →
pip install → `write_deepagents_config.py` → truststore pth → verify.

Python preference: `PIP_PYTHON_BIN` / `RALPHDGX_PYTHON`, else **python3.12**.

## Shell conventions

Scripts must run on bash 3.2+ as well as Linux bash: expand possibly-empty
arrays as `"${arr[@]+"${arr[@]}"}"`.
