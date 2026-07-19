# Goal

Upgrade this helper repository to the latest compatible DeepAgents, LangGraph,
LangChain, and model-provider stack without breaking the known-good local
OMLX/OpenAI workflow.

## Required Safety Rules

- Keep the `omlx` and `openai` providers working (both routed through dcode's
  `openai` provider / `langchain-openai`).
- Avoid pinning impossible dependency sets. If exact pins conflict with package
  metadata, prefer a fresh resolver output from the active environment.
- Keep the project install script idempotent.
- Keep local secrets out of git. Do not commit `.env`.

## Update Work

1. Discover the latest available versions of:
   - `deepagents`
   - `deepagents-acp`
   - `deepagents-code`
   - LangGraph and LangChain packages pulled by those packages
   - model provider packages needed for the OMLX/OpenAI providers
     (`langchain-openai`)
2. Update the installer and patch scripts so the selected versions install
   cleanly in a fresh `ralph-deepagents` environment.
3. Update `constraints.txt` from a validated environment, not from stale OCR
   transcript data. Note: the installer extracts only the `websockets==` pin
   from `constraints.txt` and passes it to the eager-upgrade `pip install`
   steps. This stops `langsmith` (which requires `websockets>=15` with no upper
   bound) from transiently floating websockets to 16.0, which would trip
   `langgraph-sdk`'s `websockets<16` and print a self-correcting pip conflict.
   The full file is deliberately *not* wired in, because during a version bump
   `constraints.txt` still holds the old pins and would make the new sdists fail
   to install. If a future `langgraph-sdk` raises its websockets ceiling, this
   pin can simply track whatever the validated environment resolves.
4. Keep a last-known-good backup under `backups/last-known-good/<timestamp>/`.
5. Run validation:
   - `bash -n` on shell scripts
   - `python -m py_compile` on repo Python scripts
   - `dcode --version`
   - `./ralph test omlx`
   - `./setup-and-run.sh --omlx --no-run`
6. Commit only after validation passes.

## Evidence Required

When done, report:

- Exact package versions installed.
- Commands run and exit status.
- Files changed.
- Backup directory path.
- Commit hash.
