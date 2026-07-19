"""Infrastructure-error guards for the tenacity loop."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if isinstance(text, str):
                    parts.append(text)
            else:
                parts.append(str(block))
        return "\n".join(parts)
    if content is None:
        return ""
    return str(content)


def agent_error_text(message: Any) -> str | None:
    text = _content_to_text(getattr(message, "content", message)).strip()
    if text.startswith("Agent error:"):
        return text
    return None


def recent_agent_errors(messages: Iterable[Any], *, limit: int = 2) -> list[str]:
    errors: list[str] = []
    for message in reversed(list(messages)):
        error_text = agent_error_text(message)
        if error_text is None:
            continue
        errors.append(error_text)
        if len(errors) == limit:
            break
    return errors


def latest_agent_error(messages: Iterable[Any]) -> str | None:
    errors = recent_agent_errors(messages, limit=1)
    return errors[0] if errors else None


def repeated_agent_error_message(messages: Iterable[Any]) -> str:
    error = latest_agent_error(messages) or "Agent error: unknown infrastructure failure"
    return (
        "Stopping Ralph loop after the same infrastructure error occurred twice. "
        "Retrying with another continue prompt will not make progress until the "
        f"environment issue is fixed. Last error:\n\n{error}"
    )


def has_repeated_agent_error(messages: Iterable[Any]) -> bool:
    recent_errors = recent_agent_errors(messages, limit=2)
    return len(recent_errors) == 2 and recent_errors[0] == recent_errors[1]
