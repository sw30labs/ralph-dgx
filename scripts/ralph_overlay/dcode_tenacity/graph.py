"""Tenacity wrapper graph around dcode."""

from __future__ import annotations

import os

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph

from .infra_errors import has_repeated_agent_error, repeated_agent_error_message
from .inner import load_inner_agent
from .judge import judge_node, nudge_node
from .state import GoalState

DEFAULT_BUDGET = int(os.getenv("DCODE_GOAL_BUDGET", "20"))


def _seed(state: GoalState) -> dict:
    if state.get("goal"):
        return {}
    messages = state.get("messages", [])
    first = next(
        (message for message in messages if getattr(message, "type", None) in ("human", "user")),
        None,
    )
    goal = first.content if first else "(no goal provided)"
    return {
        "goal": goal,
        "turns": 0,
        "done": False,
        "budget": state.get("budget") or DEFAULT_BUDGET,
    }


def _route_after_agent(state: GoalState) -> str:
    if has_repeated_agent_error(state.get("messages", [])):
        return "infra_error"
    return "judge"


def _infra_error_node(state: GoalState) -> dict:
    message = repeated_agent_error_message(state.get("messages", []))
    return {
        "messages": [AIMessage(content=message)],
        "done": True,
        "verdict": {
            "done": False,
            "missing": message,
            "confidence": 1.0,
        },
    }


def _route_after_judge(state: GoalState) -> str:
    if state.get("done"):
        return END
    if state.get("turns", 0) >= state.get("budget", DEFAULT_BUDGET):
        return END
    return "nudge"


def build_graph():
    inner = load_inner_agent()
    graph_builder = StateGraph(GoalState)
    graph_builder.add_node("seed", _seed)
    graph_builder.add_node("agent", inner)
    graph_builder.add_node("infra_error", _infra_error_node)
    graph_builder.add_node("judge", judge_node)
    graph_builder.add_node("nudge", nudge_node)

    graph_builder.set_entry_point("seed")
    graph_builder.add_edge("seed", "agent")
    graph_builder.add_conditional_edges(
        "agent",
        _route_after_agent,
        {"judge": "judge", "infra_error": "infra_error"},
    )
    graph_builder.add_edge("infra_error", END)
    graph_builder.add_conditional_edges("judge", _route_after_judge, {"nudge": "nudge", END: END})
    graph_builder.add_edge("nudge", "agent")
    return graph_builder.compile()


graph = build_graph()
