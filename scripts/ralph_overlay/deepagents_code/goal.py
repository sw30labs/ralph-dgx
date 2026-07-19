"""Goal-mode wrapper for running the coding agent until judged complete."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, NotRequired, TypedDict

from langchain.agents.middleware.todo import PlanningState
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class GoalVerdict(TypedDict):
    done: bool
    missing: str
    confidence: float
    evidence: str


class GoalState(PlanningState[Any]):
    goal: str
    goal_turns: int
    goal_budget: int
    goal_done: bool
    goal_verdict: NotRequired[GoalVerdict | None]


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value)
    return str(value)


def _coerce_confidence(value: Any) -> float:
    if isinstance(value, (int, float)):
        parsed = float(value)
        return parsed / 100.0 if parsed > 1 else parsed
    if isinstance(value, str):
        normalized = value.strip().lower().replace("_", " ").replace("-", " ")
        labels = {
            "none": 0.0,
            "no": 0.0,
            "low": 0.25,
            "medium": 0.5,
            "moderate": 0.5,
            "high": 0.85,
            "very high": 0.95,
            "certain": 1.0,
        }
        if normalized in labels:
            return labels[normalized]
        try:
            parsed = float(normalized.rstrip("%"))
        except ValueError:
            return 0.0
        return parsed / 100.0 if normalized.endswith("%") or parsed > 1 else parsed
    return 0.0


class GoalJudgeOutput(BaseModel):
    done: bool = Field(description="True only if the goal is verifiably complete.")
    missing: str = Field(description="Concrete remaining work when not done, empty when done.")
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = Field(description="Concrete evidence proving completion; empty if not complete.")

    @field_validator("missing", "evidence", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str:
        return _coerce_text(value)

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, value: Any) -> float:
        return _coerce_confidence(value)


_GOAL_JUDGE_SYSTEM = """You are a strict acceptance judge for an autonomous coding agent.

You are given:
- GOAL: the user's locked objective.
- TRANSCRIPT: the agent's recent actions and outputs.

Decide whether the goal is verifiably complete.

Rules:
1. Self-reports are not evidence.
2. Evidence means concrete artifacts in the transcript: file paths, diffs,
   commands, tests, exit codes, or outputs the user can inspect.
3. If concrete evidence is missing, set done=false and explain the remaining
   work in actionable terms.
4. Err on done=false. False negatives cost another turn; false positives ship
   broken work."""


def _message_content(message: BaseMessage | None) -> str:
    if message is None:
        return ""
    content = message.content
    return content if isinstance(content, str) else str(content)


def _positive_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        parsed = int(raw)
    except ValueError:
        logger.warning("Ignoring invalid integer environment value", extra={"env_var": name})
        return default
    if parsed < 0:
        logger.warning("Ignoring negative integer environment value", extra={"env_var": name})
        return default
    return parsed


def _clip_content(content: str, limit: int) -> str:
    if limit == 0 or len(content) <= limit:
        return content
    marker = f"\n[... truncated {len(content) - limit} characters; preserving head and tail ...]\n"
    if limit <= len(marker) + 2:
        return content[:limit]
    head = (limit - len(marker)) // 2
    tail = limit - len(marker) - head
    return f"{content[:head]}{marker}{content[-tail:]}"


def _compact_goal(goal: str, limit: int = 500) -> str:
    return _clip_content(" ".join(goal.split()), limit)


def _format_transcript(messages: list[BaseMessage], tail: int, message_chars: int) -> str:
    lines: list[str] = []
    for message in messages[-tail:]:
        role = getattr(message, "type", "?")
        content = _clip_content(_message_content(message), message_chars)
        lines.append(f"{role}: {content}")
    return "\n\n".join(lines)


def _parse_plain_judge_output(raw: Any) -> GoalJudgeOutput:
    text = _message_content(raw) if isinstance(raw, BaseMessage) else str(raw)
    text = text.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```")
    stripped = text.strip()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        data = json.loads(stripped[start : end + 1])
    return GoalJudgeOutput.model_validate(data)


def _json_safe(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        return str(value)


def append_iteration_log(
    state: GoalState,
    verdict: GoalVerdict,
    *,
    judge_tail: int,
    message_chars: int,
    transcript: str,
) -> None:
    path_raw = os.getenv("DAZ_RALPH_ITERATION_LOG")
    if not path_raw:
        return

    messages = state.get("messages", [])
    role_counts: dict[str, int] = {}
    for message in messages:
        role = str(getattr(message, "type", "?"))
        role_counts[role] = role_counts.get(role, 0) + 1
    latest = messages[-1] if messages else None
    latest_response_metadata = getattr(latest, "response_metadata", None) or {}
    latest_usage_metadata = getattr(latest, "usage_metadata", None) or {}

    record = _json_safe(
        {
            **verdict,
            "goal": state.get("goal", ""),
            "goal_turns": state.get("goal_turns", 0),
            "goal_budget": state.get("goal_budget", 0),
            "message_count": len(messages),
            "message_role_counts": role_counts,
            "transcript_chars": len(transcript),
            "latest_message": {
                "type": getattr(latest, "type", None),
                "content_chars": len(_message_content(latest)),
                "done_reason": latest_response_metadata.get("done_reason"),
                "input_tokens": latest_usage_metadata.get("input_tokens"),
                "output_tokens": latest_usage_metadata.get("output_tokens"),
                "total_tokens": latest_usage_metadata.get("total_tokens"),
            },
            "evidence_window": {
                "judge_tail": judge_tail,
                "message_chars": message_chars,
                "message_chars_unlimited": message_chars == 0,
            },
        }
    )

    path = Path(path_raw).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, default=str))
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())


def wrap_goal_graph(
    agent: Any,
    *,
    budget: int,
    judge_model_name: str | None,
    judge_tail: int | None = None,
) -> Any:
    tail = judge_tail or _positive_env_int("DEEPAGENTS_CODE_GOAL_JUDGE_TAIL", 8)
    message_chars = _positive_env_int("DEEPAGENTS_CODE_GOAL_JUDGE_MESSAGE_CHARS", 600)

    judge: Any | None = None
    plain_judge: Any | None = None

    def seed_node(state: GoalState) -> dict[str, Any]:
        if state.get("goal"):
            return {}
        first = next(
            (
                message
                for message in state.get("messages", [])
                if getattr(message, "type", None) in {"human", "user"}
            ),
            None,
        )
        return {
            "goal": _message_content(first),
            "goal_turns": 0,
            "goal_budget": state.get("goal_budget") or budget,
            "goal_done": False,
            "goal_verdict": None,
        }

    def record_turn_node(state: GoalState) -> dict[str, int]:
        return {"goal_turns": state.get("goal_turns", 0) + 1}

    def judge_node(state: GoalState) -> dict[str, Any]:
        nonlocal judge, plain_judge

        from deepagents_code.config import create_model

        transcript = _format_transcript(state.get("messages", []), tail, message_chars)
        window_note = (
            "unlimited characters per message"
            if message_chars == 0
            else f"up to {message_chars} characters per message, preserving head and tail"
        )
        prompt = [
            ("system", _GOAL_JUDGE_SYSTEM),
            (
                "user",
                f"GOAL:\n{state.get('goal', '')}\n\n"
                f"TRANSCRIPT (last {tail} messages; {window_note}):\n{transcript}",
            ),
        ]

        try:
            if judge is None:
                result = create_model(judge_model_name)
                judge = result.model.with_structured_output(GoalJudgeOutput)
            output: GoalJudgeOutput = judge.invoke(prompt)
        except Exception:
            logger.warning(
                "Structured goal judge failed; retrying with plain JSON output",
                exc_info=True,
            )
            if plain_judge is None:
                plain_judge = create_model(judge_model_name).model
            raw = plain_judge.invoke(
                prompt
                + [
                    (
                        "user",
                        "Return ONLY valid JSON with keys: done, missing, confidence, evidence.",
                    )
                ]
            )
            output = _parse_plain_judge_output(raw)

        verdict: GoalVerdict = {
            "done": output.done,
            "missing": output.missing,
            "confidence": output.confidence,
            "evidence": output.evidence,
        }
        append_iteration_log(state, verdict, judge_tail=tail, message_chars=message_chars, transcript=transcript)
        return {"goal_verdict": verdict, "goal_done": bool(output.done)}

    def nudge_node(state: GoalState) -> dict[str, list[HumanMessage]]:
        verdict = state.get("goal_verdict") or {"missing": "continue toward the goal"}
        missing = verdict.get("missing") or "produce stronger completion evidence"
        content = (
            "The goal is NOT yet complete.\n\n"
            f"Goal summary: {_compact_goal(state.get('goal', ''))}\n\n"
            f"Still missing: {missing}\n\n"
            "Continue working, then make the next response include compact, "
            "inspectable evidence rather than a summary. Include exact file paths "
            "and line numbers, relevant diff or file excerpts, command strings, "
            "exit codes, and key outputs."
        )
        return {"messages": [HumanMessage(content=content)]}

    def route_after_judge(state: GoalState) -> str:
        if state.get("goal_done"):
            return END
        if state.get("goal_turns", 0) >= state.get("goal_budget", budget):
            return END
        return "nudge"

    graph = StateGraph(GoalState)
    graph.add_node("seed_goal", seed_node)
    graph.add_node("agent", agent)
    graph.add_node("record_goal_turn", record_turn_node)
    graph.add_node("judge_goal", judge_node)
    graph.add_node("nudge_goal", nudge_node)
    graph.set_entry_point("seed_goal")
    graph.add_edge("seed_goal", "agent")
    graph.add_edge("agent", "record_goal_turn")
    graph.add_edge("record_goal_turn", "judge_goal")
    graph.add_conditional_edges("judge_goal", route_after_judge, {"nudge": "nudge_goal", END: END})
    graph.add_edge("nudge_goal", "agent")
    return graph.compile()
