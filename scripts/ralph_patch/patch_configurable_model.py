"""Patch configurable_model.py: logging helpers and model-request auditing."""
from __future__ import annotations

from pathlib import Path

from ._shared import replace_once


def run(configurable_model_py: Path) -> None:
    # Add imports
    replace_once(
        configurable_model_py,
        "import logging\n",
        "import json\nimport logging\nimport os\nimport time\n",
    )

    # Add helper functions before _apply_overrides. In 0.1.27 the
    # _ANTHROPIC_ONLY_SETTINGS constant is no longer immediately followed by
    # _apply_overrides, so anchor directly on the _apply_overrides def header.
    replace_once(
        configurable_model_py,
        '''def _apply_overrides(request: ModelRequest) -> ModelRequest:
    """Apply model/param overrides from `CLIContext` on the runtime.
''',
        '''def _content_chars(content: Any) -> int:
    if content is None:
        return 0
    if isinstance(content, str):
        return len(content)
    return len(str(content))


def _tool_name(tool: Any) -> str:
    if isinstance(tool, dict):
        function = tool.get("function")
        if isinstance(function, dict) and function.get("name"):
            return str(function["name"])
        return str(tool.get("name") or tool.get("type") or "<dict>")
    return str(getattr(tool, "name", type(tool).__name__))


def _message_summary(message: Any) -> dict[str, Any]:
    tool_calls = getattr(message, "tool_calls", None) or []
    summary: dict[str, Any] = {
        "type": getattr(message, "type", type(message).__name__),
        "content_chars": _content_chars(getattr(message, "content", None)),
    }
    if tool_calls:
        summary["tool_calls"] = [
            {
                "name": call.get("name"),
                "id": call.get("id"),
                "args_keys": sorted((call.get("args") or {}).keys()),
            }
            for call in tool_calls
            if isinstance(call, dict)
        ]
    tool_call_id = getattr(message, "tool_call_id", None)
    if tool_call_id:
        summary["tool_call_id"] = tool_call_id
    name = getattr(message, "name", None)
    if name:
        summary["name"] = name
    return summary


def _log_model_request(request: ModelRequest, *, phase: str) -> None:
    path = os.getenv("DEEPAGENTS_CODE_MODEL_REQUEST_LOG")
    if not path:
        return
    try:
        record = {
            "ts": time.time(),
            "phase": phase,
            "model": str(getattr(request.model, "model", request.model)),
            "tool_count": len(request.tools),
            "tools": [_tool_name(tool) for tool in request.tools[:80]],
            "tool_choice": request.tool_choice,
            "model_settings_keys": sorted(request.model_settings.keys()),
            "has_system_prompt": bool(request.system_prompt),
            "message_count": len(request.messages),
            "messages": [_message_summary(message) for message in request.messages],
        }
        with open(path, "a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False, default=str))
            file.write("\\n")
    except Exception:
        logger.debug("Failed to write model request summary", exc_info=True)


def _apply_overrides(request: ModelRequest) -> ModelRequest:
    """Apply model/param overrides from `CLIContext` on the runtime.
''',
    )

    # Hook logging into sync handler
    replace_once(
        configurable_model_py,
        "        return handler(_apply_overrides(request))\n",
        '''        request = _apply_overrides(request)
        _log_model_request(request, phase="sync")
        return handler(request)
''',
    )

    # Hook logging into async handler. In 0.1.27 the async path applies overrides
    # through the awaitable _apply_overrides_async variant.
    replace_once(
        configurable_model_py,
        "        return await handler(await _apply_overrides_async(request))\n",
        '''        request = await _apply_overrides_async(request)
        _log_model_request(request, phase="async")
        return await handler(request)
''',
    )
