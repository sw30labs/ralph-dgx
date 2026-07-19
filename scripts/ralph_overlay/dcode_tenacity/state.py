"""Shared state for the tenacity wrapper."""

from __future__ import annotations

from typing import Optional, TypedDict

from langgraph.graph import MessagesState


class Verdict(TypedDict):
    done: bool
    missing: str
    confidence: float


class GoalState(MessagesState):
    goal: str
    turns: int
    verdict: Optional[Verdict]
    done: bool
    budget: int
