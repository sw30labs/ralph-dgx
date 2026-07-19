"""Guard against mutating Ralph's own Python runtime from agent shell tools."""

from __future__ import annotations

import logging
import os
import re
import shlex
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain.agents.middleware.types import AgentMiddleware

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from langchain_core.messages import ToolMessage
    from langgraph.prebuilt.tool_node import ToolCallRequest
    from langgraph.types import Command

logger = logging.getLogger(__name__)

ALLOW_RALPH_ENV_PIP_INSTALL = "DEEPAGENTS_CODE_ALLOW_RALPH_ENV_PIP_INSTALL"

_PYTHON_EXECUTABLE_NAMES = frozenset(
    {
        "python",
        "python3",
        f"python{sys.version_info.major}",
        f"python{sys.version_info.major}.{sys.version_info.minor}",
        Path(sys.executable).name,
    }
)
_PIP_EXECUTABLE_NAMES = frozenset({"pip", "pip3", f"pip{sys.version_info.major}"})
_SHELL_SEGMENT_RE = re.compile(r"&&|\|\||;|\|")
_ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_RALPH_EXECUTABLE = Path(os.path.normpath(str(Path(sys.executable).expanduser())))
_RALPH_BIN_DIR = _RALPH_EXECUTABLE.parent


def _truthy_env(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_executable_path(executable: str) -> Path | None:
    if "/" not in executable:
        return None
    return Path(os.path.normpath(str(Path(executable).expanduser())))


def _executable_points_at_ralph(executable: str, executable_names: frozenset[str]) -> bool:
    executable_path = _resolve_executable_path(executable)
    executable_name = Path(executable).name
    if executable_path is None:
        return executable_name in executable_names
    return executable_path == _RALPH_EXECUTABLE or (
        executable_path.parent == _RALPH_BIN_DIR and executable_name in executable_names
    )


def _strip_shell_prefixes(tokens: list[str]) -> list[str]:
    while tokens:
        token = tokens[0]
        if _ENV_ASSIGNMENT_RE.match(token):
            tokens = tokens[1:]
            continue
        if token == "env":
            tokens = tokens[1:]
            while tokens:
                if _ENV_ASSIGNMENT_RE.match(tokens[0]):
                    tokens = tokens[1:]
                elif tokens[0] in {"-u", "--unset", "-C", "--chdir"} and len(tokens) >= 2:
                    tokens = tokens[2:]
                elif tokens[0].startswith(("--unset=", "--chdir=")):
                    tokens = tokens[1:]
                elif tokens[0].startswith("-"):
                    tokens = tokens[1:]
                else:
                    break
            continue
        if token == "command":
            tokens = tokens[1:]
            continue
        break
    return tokens


def _contains_pip_install(args: list[str]) -> bool:
    return "install" in args


def _uv_pip_install_targets_ralph(tokens: list[str]) -> bool:
    if len(tokens) < 3 or tokens[0] != "uv" or tokens[1] != "pip":
        return False
    if "install" not in tokens[2:]:
        return False
    if "--system" in tokens:
        return True
    for index, token in enumerate(tokens):
        if token in {"--target", "--prefix"} and index + 1 < len(tokens):
            return False
        if token.startswith(("--target=", "--prefix=")):
            return False
        if token == "--python" and index + 1 < len(tokens):
            return _executable_points_at_ralph(tokens[index + 1], _PYTHON_EXECUTABLE_NAMES)
        if token.startswith("--python="):
            return _executable_points_at_ralph(token.split("=", 1)[1], _PYTHON_EXECUTABLE_NAMES)
    return True


def command_installs_into_ralph_runtime(command: str) -> bool:
    """Return whether a shell command installs packages into Ralph's runtime."""

    for segment in _SHELL_SEGMENT_RE.split(command):
        segment = segment.strip()
        if not segment:
            continue
        try:
            tokens = _strip_shell_prefixes(shlex.split(segment))
        except ValueError:
            continue
        if not tokens:
            continue

        executable = tokens[0]
        if (
            _executable_points_at_ralph(executable, _PYTHON_EXECUTABLE_NAMES)
            and len(tokens) >= 4
            and tokens[1:3] == ["-m", "pip"]
            and _contains_pip_install(tokens[3:])
        ):
            return True
        if _executable_points_at_ralph(executable, _PIP_EXECUTABLE_NAMES) and _contains_pip_install(tokens[1:]):
            return True
        if _uv_pip_install_targets_ralph(tokens):
            return True
    return False


class RalphRuntimeInstallGuardMiddleware(AgentMiddleware):
    """Reject package installs that would mutate Ralph's active Python runtime."""

    def _validate_tool_call(self, request: "ToolCallRequest") -> "ToolMessage | None":
        from langchain_core.messages import ToolMessage as LCToolMessage

        if _truthy_env(os.environ.get(ALLOW_RALPH_ENV_PIP_INSTALL)):
            return None

        args = request.tool_call.get("args") or {}
        command = args.get("command", "")
        if not isinstance(command, str) or not command_installs_into_ralph_runtime(command):
            return None

        logger.warning("Shell command rejected by Ralph runtime install guard: %r", command)
        return LCToolMessage(
            content=(
                "Shell command rejected: it would install Python packages into "
                f"Ralph's active runtime ({sys.prefix}). This can break Ralph "
                "between loops. Create an isolated target environment instead, "
                "for example `python -m venv .venv && .venv/bin/python -m pip "
                "install -r requirements.txt`. If you intentionally need to "
                f"modify Ralph's runtime, set `{ALLOW_RALPH_ENV_PIP_INSTALL}=1` "
                "after explicit approval."
            ),
            tool_call_id=request.tool_call["id"],
            name="execute",
            status="error",
        )

    def wrap_tool_call(
        self,
        request: "ToolCallRequest",
        handler: "Callable[[ToolCallRequest], ToolMessage | Command[Any]]",
    ) -> "ToolMessage | Command[Any]":
        if (rejection := self._validate_tool_call(request)) is not None:
            return rejection
        return handler(request)

    async def awrap_tool_call(
        self,
        request: "ToolCallRequest",
        handler: "Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]]",
    ) -> "ToolMessage | Command[Any]":
        if (rejection := self._validate_tool_call(request)) is not None:
            return rejection
        return await handler(request)
