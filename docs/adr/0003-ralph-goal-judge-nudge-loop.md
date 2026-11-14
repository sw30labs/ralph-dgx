# ADR-0003: Ralph goal mode: wrap the dcode agent in a goal → judge → nudge loop with an evidence-strict judge

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

The point of the fork is to keep a coding agent working until a goal is verifiably complete (QUICKSTART "Goal Loop Behavior"; docs/ralph-loop-diagram.md "Keep Agent Running").

## Decision

`deepagents_code/goal.py` (overlay) provides `wrap_goal_graph(agent, budget, judge_model_name)`: a `StateGraph` of seed_goal → agent → record_goal_turn → judge_goal → (END | nudge_goal → agent). The goal is the first human message; the loop ends on `goal_done` or when `goal_turns` reaches `goal_budget` (default 20, `--goal-budget`). The judge prompt says self-reports are not evidence and to err on `done=false`; it sees the last `DEEPAGENTS_CODE_GOAL_JUDGE_TAIL` (8) messages clipped to `DEEPAGENTS_CODE_GOAL_JUDGE_MESSAGE_CHARS` (600, head+tail). It uses structured output and falls back to plain-JSON parsing. The judge model comes from `create_model(judge_model_name)`; with no `--goal-judge-model` it is the same default model as the worker. Each verdict is appended (fsync) to `DAZ_RALPH_ITERATION_LOG` as JSONL. `patch_server.py` adds `goal_mode/goal_budget/goal_judge_model` to `ServerConfig` (GOAL_* env) and wraps the server graph when `goal_mode` is set; `daz-ralph` (`daz_ralph/main.py`) launches the dcode TUI with `goal_mode=tenacity` (default on via `DAZ_RALPH_TENACITY`).

## Consequences

### Positive

- Completion requires evidence in the transcript, not the agent's own claim.
- Every judge turn is logged, so the update workflow can check the final verdict (ADR-0010).
- Works with the local vLLM model alone; no second provider needed.

### Negative

- The judge sees a narrow window (8 messages × 600 chars by default), so evidence outside it is invisible.
- Default judge = worker model, so the same local model grades itself (TODO-ROADMAP P4 wants a separate judge).
- Two goal-loop implementations ship (see ADR-0015).

## Alternatives considered

- Upstream dcode `/goal` and rubrics (TODO-ROADMAP P4 wants a bridge, not two competing systems; not adopted yet).
- Single-shot agent runs (rejected by the purpose of the repo).

## Evidence

- scripts/ralph_overlay/deepagents_code/goal.py
- scripts/ralph_patch/patch_server.py
- scripts/ralph_overlay/daz_ralph/main.py
- QUICKSTART.md
- docs/ralph-loop-diagram.md
- TODO-ROADMAP.md (P4, P7)
