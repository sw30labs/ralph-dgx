# Architecture Decision Records — ralphdgx (sw30labs/ralph-dgx)

Retrospective ADRs for ralphdgx, the DGX Spark / local-vLLM installer that patches DeepAgents Code with the Ralph/tenacity goal loop. Reviewed commit: `1af0b155d85cf96d77ab1504a80d4c726fe4a1af`.

Format: Title; Status; Context; Decision; Consequences (positive/negative); Alternatives considered; Evidence (file paths, commit SHAs). All records here were written retrospectively on 2026-11-14 from a full read of the repository at the reviewed commit. Where the *why* is inferred rather than stated in the code, docs, or commit messages, the ADR says so and the inference is logged in [`../assumptions.md`](../assumptions.md).

| ADR | Title | Status |
|---|---|---|
| [0001](0001-install-patched-pypi-sdists.md) | Install DeepAgents by downloading pinned PyPI sdists and patching them, not by forking the source | Accepted (retrospective) |
| [0002](0002-fail-loud-anchor-text-patches.md) | Text-anchor patches that apply exactly once and fail loudly when upstream changes | Accepted (retrospective) |
| [0003](0003-ralph-goal-judge-nudge-loop.md) | Ralph goal mode: wrap the dcode agent in a goal → judge → nudge loop with an evidence-strict judge | Accepted (retrospective) |
| [0004](0004-dgx-fork-vllm-and-openai-only.md) | DGX fork supports only `vllm` and `openai` providers; no OMLX/MLX path | Accepted (retrospective) |
| [0005](0005-vllm-via-openai-provider-chat-completions.md) | Reach local vLLM through dcode's `openai` provider with the Responses API forced off | Accepted (retrospective) |
| [0006](0006-vllm-owns-openai-env.md) | When the provider is `vllm`, local vLLM always owns OPENAI_BASE_URL / OPENAI_API_KEY | Accepted (retrospective) |
| [0007](0007-project-venv-python312.md) | Install and run from a project-local `.venv`, preferring Python 3.12 | Accepted (retrospective) |
| [0008](0008-runtime-install-guard.md) | Block agent shell commands that pip-install into Ralph's own runtime | Accepted (retrospective) |
| [0009](0009-env-switch-disable-sync-subagents.md) | Environment switch to disable synchronous subagents and the `task` tool | Accepted (retrospective) |
| [0010](0010-ralph-driven-safe-upgrade-workflow.md) | Ralph-driven safe upgrade workflow: back up, require a done verdict, validate, refresh constraints, commit | Accepted (retrospective) |
| [0011](0011-constraints-websockets-pin-only.md) | `constraints.txt` is a validated-env reference; only its `websockets==` pin is enforced at install | Accepted (retrospective) |
| [0012](0012-truststore-autoloader-opt-in-on-linux.md) | System-trust (truststore) autoloader is opt-in on Linux | Accepted (retrospective) |
| [0013](0013-secrets-in-env-only.md) | Secrets live only in a gitignored `.env`; generated config stores env-var names, not keys | Accepted (retrospective) |
| [0014](0014-local-first-runtime-defaults.md) | Local-first runtime defaults: tracing and update checks off, debug log on, MCP off | Accepted (retrospective) |
| [0015](0015-ship-standalone-dcode-tenacity.md) | Also ship the standalone `dcode-tenacity` headless graph next to goal mode | Accepted (retrospective) |
| [0016](0016-offline-unit-tests-plus-validation-gates.md) | Offline unit tests for helpers, plus shell/compile/smoke validation gates | Accepted (retrospective) |
