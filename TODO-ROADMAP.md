# TODO / Roadmap

Personal notes after reading the current DeepAgents docs (SDK + `dcode`) and comparing them to what **ralphdgx** already does on this DGX Spark.

**Stack I’m on today:** `deepagents==0.7.0a7`, `deepagents-code==0.1.43`, `deepagents-acp==0.0.9`  
**Repo:** https://github.com/sw30labs/ralphdgx

I’m **not** behind on package versions in any serious way. The opportunity is turning on and packaging features the stack already supports, but that I haven’t made first-class DGX defaults yet.

## Docs I used

| Area | Link |
|------|------|
| SDK harness | https://docs.langchain.com/oss/python/deepagents/overview |
| Coding agent (`dcode`) | https://docs.langchain.com/oss/python/deepagents/code/overview |
| Goals / rubrics | https://docs.langchain.com/oss/python/deepagents/code/goals-and-rubrics |
| v0.5 (async subagents, multimodal FS) | https://www.langchain.com/blog/deep-agents-v0-5 |
| v0.6 (profiles, interpreter, streaming, delta, Context Hub) | https://www.langchain.com/blog/deep-agents-0-6 |

---

## What I already have (don’t reinvent)

- Local OpenAI-compatible **vLLM** path (default) + optional cloud OpenAI-compatible
- Ralph / tenacity goal–judge–nudge loop (overlays + `goal_mode` patches)
- Safe stack upgrade workflow + last-known-good backups
- Forcing chat-completions for vLLM (`use_responses_api = false` + `model_param_filter`)
- Runtime install guard so the agent doesn’t trash its own env
- Pin / download / patch / install pipeline on Python 3.12 + project `.venv`

---

## What’s new or important in the docs (my take)

### Harness profiles (v0.6) — highest ROI for this box

Per-model tuning of system prompt, tools, and middleware. The docs pitch this hard for **open-weight models (Qwen, Kimi, DeepSeek)** — often a big quality jump without changing the model.

I want checked-in profiles for:

- `Qwen/Qwen3-Coder-Next-FP8` (primary local coder)
- `Qwen/Qwen3.6-27B-FP8` (dense fallback recipe)

Things to tune: tool-call style, thinking off for coder-next, context limits, maybe excluding noisy tools.

### Code interpreter / QuickJS PTC (v0.6)

In-process JS REPL so the agent can loop tools in code (programmatic tool calling) without a full OS sandbox. Model-agnostic; works with open models.

Optional `deepagents[quickjs]` / REPL middleware on Spark. Complements shell; does **not** replace vLLM. Goal: fewer “model → tool → model” round-trips on long loops.

### Async / dynamic subagents (v0.5+)

Background remote subagents via Agent Protocol (`start_async_task`, poll/cancel/list). Inline subagents block; async ones don’t.

My `.env` currently has `DEEPAGENTS_CODE_DISABLE_SYNC_SUBAGENTS=true`. Docs push async for long research / code analysis. On one Spark I could:

- keep local Qwen as orchestrator, or  
- spawn async workers on Grok / another recipe  

Useful for “big repo explore while the main loop keeps steering.”

### Upstream goals & rubrics (`dcode`)

Native `/goal`, `/goal amend|pause|resume`, `/rubric set|next|file`, and non-interactive:

```bash
dcode -n "..." --rubric "tests pass; ..." --rubric-model openai:grok-4.5
```

I already have Ralph tenacity. I don’t want two competing systems — I want a **bridge**:

- upstream `/goal` + rubrics for interactive coding  
- Ralph loop for stack upgrades / long autonomous jobs  
- or grade Ralph with **Grok as judge** and local Qwen as worker (docs support separate goal/rubric models)

### Filesystem permissions + multimodal FS

Declarative allow/deny paths; multimodal `read_file` for images, PDF, audio, video (model-dependent).

I want default denies on `.env`, keys, `~/.grok/auth.json`, and model weight dirs under `~/models` — safer YOLO on a workstation that also holds secrets and 100GB weights. Multimodal is lower priority unless I do vision/docs work.

### Remote sandboxes

Shell/`execute` in an isolated remote environment instead of the host.

Optional “run tests in a sandbox, keep the agent on the host” so YOLO can’t wreck the Spark. Lower priority if I keep trusting local shell + install guards.

### Streaming v3 + frontend SDKs

Typed streams for messages, tools, **subagents**.

Less critical for the TUI; more interesting if I build a simple status UI for multi-hour Ralph runs (subagent progress, judge turns).

### ContextHub + DeltaChannel

Versioned skills/memory in LangSmith; delta checkpoints (much less storage for long runs).

DeltaChannel already shows up in the `deepagents` graph code I’m shipping. ContextHub only pays off if I want cloud-synced skills/memory — optional, not DGX-core.

### Skills + `AGENTS.md` memory

Progressive skills + always-on memory files are first-class.

I should ship a **DGX skill pack**:

- start/stop vLLM recipes (`coder-next` / `qwen27`)
- `use_responses_api=false` gotchas  
- aarch64 / GB10 memory notes  
- “never require omlx” on this fork  

---

## Ranked work I actually want to do

| Priority | Item | Why I care |
|----------|------|------------|
| **1** | **Qwen harness profiles** for Coder-Next + 3.6-27B | Docs’ open-weight story; free quality on local models |
| **2** | **Project skills + AGENTS.md** for Spark/vLLM ops | Turn box-specific knowledge into agent memory |
| **3** | **Filesystem permissions** defaults | Safer auto-approve on a machine with secrets + huge model dirs |
| **4** | **Wire upstream rubrics into Ralph** (`--rubric`, separate judge model) | Grok as judge, Qwen as worker; less “missing evidence” thrash |
| **5** | **Optional QuickJS / PTC** | Fewer round-trips on long tool loops with local models |
| **6** | **Async subagents** (enable + document; dual-model) | Parallel explore/test while main agent steers |
| **7** | **Headless CI mode** (`dcode -n` + rubric + ralph scripts) | Avoid TUI hanging after `done=true` (I already hit this) |
| **8** | Remote sandbox / ContextHub / fancy streaming UI | Nice later; not the first win |

---

## Concrete TODO checklist

### P1 — Harness profiles

- [ ] Add a Qwen / Coder-Next harness profile (tool calling, thinking off, context)
- [ ] Add a Qwen3.6-27B profile for the `qwen27` recipe
- [ ] Document how profiles load with `./ralphdgx run` and local recipes
- [ ] Smoke-test both recipes after profile changes

### P2 — Skills + memory

- [ ] Add repo `AGENTS.md` (or project agent memory) with DGX conventions
- [ ] Add a skill for vLLM recipe lifecycle (`serve-local-llm.sh` / `start-vllm.sh`)
- [ ] Add a skill for ralphdgx provider rules (vllm vs openai, no omlx)
- [ ] Document skill install paths that actually work on this host

### P3 — Filesystem permissions

- [ ] Default deny (or read-only) for `.env`, credential files, `~/.grok/auth.json`
- [ ] Keep model weight trees under `~/models` out of casual writes
- [ ] Document how permissions interact with YOLO / `--auto-approve`

### P4 — Goals / rubrics bridge

- [ ] Map Ralph tenacity loop vs upstream `/goal` and `/rubric` (when to use which)
- [ ] Support separate judge model (e.g. Grok) vs worker model (local Qwen)
- [ ] Prefer `--rubric` / non-interactive criteria for upgrade-style jobs
- [ ] Update `docs/upgradeLangGraphDeepAgentsStackSafely.md` to match DGX gates only

### P5 — QuickJS / PTC

- [ ] Optional install path for `deepagents[quickjs]` in the venv
- [ ] Wire REPL middleware behind a clear flag/env (off by default until proven)
- [ ] Benchmark a long tool loop with/without interpreter on Coder-Next

### P6 — Async subagents

- [ ] Revisit `DEEPAGENTS_CODE_DISABLE_SYNC_SUBAGENTS`
- [ ] Document async subagent setup (local ASGI vs remote Agent Protocol)
- [ ] Prototype: local Qwen orchestrator + Grok (or second recipe) worker

### P7 — Headless / CI

- [ ] Ensure Ralph upgrade path exits cleanly when `done=true` (no hung TUI)
- [ ] Scripted `dcode -n` + rubric validation for post-upgrade smoke
- [ ] Make `run-ralph-update-langgraph.sh` post-steps reliable after headless exit

### P8 — Later / optional

- [ ] Remote sandbox for test execution
- [ ] LangSmith ContextHub for shared skills/memory (only if I commit to LangSmith)
- [ ] Streaming status UI for long Ralph runs

---

## Bottom line (for future me)

Docs emphasize **harness quality around open models**, **lighter-than-sandbox code execution**, **non-blocking subagents**, and **first-class goals/rubrics** in `dcode`.

For this repo, the coolest next work is **not** another blind stack bump. It’s:

1. **Qwen-specific harness profiles**  
2. **DGX skill pack + path permissions**  
3. **Ralph ↔ upstream rubric/judge integration + true headless exit**

I’ll turn those into PRs when I’m ready to implement.
