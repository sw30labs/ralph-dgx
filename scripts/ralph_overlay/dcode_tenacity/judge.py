"""Acceptance judge for the tenacity loop."""

from __future__ import annotations

import os
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import BaseModel, Field, field_validator

from .state import GoalState, Verdict


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
        return float(value)
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


class JudgeOutput(BaseModel):
    done: bool = Field(description="True only if the goal is verifiably complete.")
    missing: str = Field(description="Concrete remaining work if not done; empty if done.")
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = Field(description="Concrete evidence proving completion.")

    @field_validator("missing", "evidence", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str:
        return _coerce_text(value)

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, value: Any) -> float:
        return _coerce_confidence(value)


_JUDGE_SYSTEM = """You are a strict acceptance judge for an autonomous coding agent.

You are given:
- GOAL: the user's locked-in objective.
- TRANSCRIPT: the agent's recent actions and outputs.

Decide whether the goal is verifiably complete. Self-reports are not evidence.
Evidence means file diffs, passing tests, exit codes, commands, or artifacts
the user can inspect. Err on done=false."""

_TAIL_MESSAGES = int(os.getenv("DCODE_JUDGE_TAIL", "12"))


def _format_messages(messages: list[BaseMessage]) -> str:
    tail = messages[-_TAIL_MESSAGES:]
    out: list[str] = []
    for message in tail:
        role = getattr(message, "type", "?")
        content = message.content if isinstance(message.content, str) else str(message.content)
        out.append(f"{role}: {content[:4000]}")
    return "\n\n".join(out)


def _judge_model():
    name = os.getenv("DCODE_JUDGE_MODEL", "anthropic:claude-haiku-4-5-20251001")
    return init_chat_model(name, temperature=0).with_structured_output(JudgeOutput)


def judge_node(state: GoalState) -> dict[str, Any]:
    transcript = _format_messages(state["messages"])
    prompt = [
        ("system", _JUDGE_SYSTEM),
        (
            "user",
            f"GOAL:\n{state['goal']}\n\nTRANSCRIPT (last {_TAIL_MESSAGES} msgs):\n{transcript}",
        ),
    ]
    output: JudgeOutput = _judge_model().invoke(prompt)
    verdict: Verdict = {
        "done": output.done,
        "missing": output.missing,
        "confidence": output.confidence,
    }
    return {"verdict": verdict, "done": bool(output.done)}


def nudge_node(state: GoalState) -> dict[str, Any]:
    verdict = state.get("verdict") or {"missing": "continue toward the goal"}
    nudge = (
        "The goal is NOT yet complete.\n\n"
        f"GOAL: {state['goal']}\n\n"
        f"Still missing: {verdict['missing']}\n\n"
        "Continue. Produce verifiable evidence such as tests, diffs, outputs, "
        "file paths, and exit codes before considering this done."
    )
    return {
        "messages": [HumanMessage(content=nudge)],
        "turns": state.get("turns", 0) + 1,
    }
