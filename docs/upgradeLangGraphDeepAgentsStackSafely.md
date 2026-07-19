# Goal

Upgrade this helper repository (`ralphdgx`) to the latest compatible DeepAgents,
LangGraph, LangChain, and model-provider stack without breaking the known-good
**local vLLM** and optional **OpenAI-compatible** workflows on NVIDIA DGX Spark
(Linux aarch64 / GB10).

This is **not** the Mac `ralph` repo: there is **no OMLX**, no Hy3/MLX, and no
`omlx` provider. Do not run, invent, or require `omlx` commands.

## Required Safety Rules

- Keep both providers working, both routed through dcode’s `openai` provider /
  `langchain-openai`:
  - **`vllm`** (default): local OpenAI-compatible server at
    `VLLM_BASE_URL` (default `http://127.0.0.1:8000/v1`) with
    `use_responses_api = false` (chat-completions only).
  - **`openai`**: real OpenAI or any compatible endpoint via `OPENAI_*`
    (including xAI Grok when `OPENAI_BASE_URL=https://api.x.ai/v1`).
- Constructor-only model params such as `use_responses_api` must stay on the
  ChatOpenAI instance and must **not** be bound into `model_settings` (that
  leaks into `AsyncCompletions.create()` and raises TypeError). Keep the
  Ralph `model_param_filter` / configurable_model patch working.
- Avoid pinning impossible dependency sets. If exact pins conflict with package
  metadata, prefer a fresh resolver output from the active environment.
- Keep the project install script idempotent (`./ralphdgx install`).
- Keep local secrets out of git. Do not commit `.env`.
- Prefer the project `.venv` (Python 3.12). Do not install into system Python.

## Update Work

1. Discover the latest available versions of:
   - `deepagents`
   - `deepagents-acp`
   - `deepagents-code`
   - LangGraph and LangChain packages pulled by those packages
   - model provider package for the vLLM/OpenAI path (`langchain-openai`)
2. Update the installer and patch scripts so the selected versions install
   cleanly in a fresh project `.venv` environment:
   - `scripts/ralph_install.sh` (sdist pins)
   - `scripts/ralph_patch/` (overlays + text patches, including
     `patch_configurable_model.py` and `server_manager` goal_mode wiring)
   - `scripts/ralph_overlay/` (daz_ralph, dcode_tenacity, goal, model_param_filter)
3. Update `constraints.txt` from a validated environment, not from stale data.
   Note: the installer extracts only the `websockets==` pin from
   `constraints.txt` and passes it to the eager-upgrade `pip install` steps.
   This stops `langsmith` (which requires `websockets>=15` with no upper bound)
   from transiently floating websockets to 16.0, which would trip
   `langgraph-sdk`’s `websockets<16`. The full file is deliberately *not* wired
   in during a version bump. When regenerating `constraints.txt`, pin
   `deepagents*` by version (`==x.y.z`), not by local `file://` path from the
   patched install tree.
4. Keep a last-known-good backup under `backups/last-known-good/<timestamp>/`.
5. Run validation (DGX commands only):
   - `bash -n` on repo shell scripts (`ralphdgx`, `setup-and-run.sh`,
     `run-ralph-update-langgraph.sh`, `scripts/*.sh`)
   - `python -m py_compile` on repo Python scripts under `scripts/` and
     `scripts/ralph_overlay/` / `scripts/ralph_patch/`
   - `dcode --version` (from project `.venv`)
   - `./ralphdgx test vllm` **or** `./ralphdgx test openai` if the local vLLM
     server is down and cloud/OpenAI-compatible credentials are configured
   - `./setup-and-run.sh --vllm --no-run` (install + smoke without launching TUI)
6. Commit only after validation passes.

## Done criteria

Mark the goal **done only when all** of the following are true and visible in
the transcript with raw command lines and exit codes:

1. Installer/patch sources updated for the chosen DeepAgents stack versions.
2. `constraints.txt` regenerated from the validated `.venv`.
3. Backup directory exists under `backups/last-known-good/<timestamp>/`.
4. Validation commands above all exit 0 (use `test openai` only if vLLM is
   unavailable and that path is what you validated).
5. Changes committed (or clean working tree with proof nothing further to commit).

## Evidence Required

When done, report:

- Exact package versions installed (`pip show deepagents deepagents-acp
  deepagents-code langchain-openai langgraph` and relevant freezes).
- Commands run and exit status (raw, not paraphrased).
- Files changed (`git show --stat` / `git status`).
- Backup directory path.
- Commit hash.
