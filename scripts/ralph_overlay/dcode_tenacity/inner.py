"""Resolve the inner DeepAgents Code graph."""

from __future__ import annotations

import importlib
import logging
import os
from typing import Any

log = logging.getLogger(__name__)

_CANDIDATES = [
    "deepagents_code.server.graph:graph",
    "deepagents_code.graph:graph",
    "deepagents_code.agent.graph:graph",
    "deepagents_code:graph",
]


def _try_import(spec: str) -> Any | None:
    try:
        module_path, attr = spec.split(":", 1)
        module = importlib.import_module(module_path)
        graph = getattr(module, attr, None)
        if graph is None:
            return None
        log.info("inner agent: loaded dcode graph from %s", spec)
        return graph
    except Exception as exc:
        log.debug("inner agent: %s failed (%s)", spec, exc)
        return None


def _build_fallback():
    from deepagents import create_deep_agent

    model = os.getenv("DCODE_MODEL", "anthropic:claude-sonnet-4-6")
    instructions = (
        "You are a tenacious coding agent. You will be called repeatedly "
        "by an outer judge until a goal is verifiably complete. "
        "On each turn: make concrete progress, run tests where applicable, "
        "and never declare a task done without evidence."
    )
    return create_deep_agent(model=model, tools=[], system_prompt=instructions)


def load_inner_agent():
    override = os.getenv("DCODE_GRAPH_IMPORT")
    if override:
        graph = _try_import(override)
        if graph is not None:
            return graph
        log.warning("DCODE_GRAPH_IMPORT=%s did not resolve; falling back", override)

    for spec in _CANDIDATES:
        graph = _try_import(spec)
        if graph is not None:
            return graph

    log.info("no dcode graph found; using create_deep_agent fallback")
    return _build_fallback()
