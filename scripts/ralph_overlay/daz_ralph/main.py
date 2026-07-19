"""DeepAgents Code TUI launcher with Ralph/tenacity enabled."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from daz_ralph import __version__

logger = logging.getLogger(__name__)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


def _json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("must be a JSON object")
    return parsed


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _json_safe(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        return str(value)


def _configure_ralph_log_env(
    *,
    thread_id: str | None,
    resume_thread: str | None,
    initial_prompt: str | None,
    goal_budget: int,
    tenacity: bool,
) -> None:
    started_at = datetime.now(UTC)
    log_dir = Path(os.environ.get("DAZ_RALPH_LOG_DIR", Path.cwd() / "logs" / "ralph")).expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)

    effective_thread = thread_id or resume_thread or "resume-most-recent"
    run_id = os.environ.get("DAZ_RALPH_RUN_ID") or (
        f"{started_at.strftime('%Y%m%dT%H%M%S')}-{effective_thread}-{os.getpid()}"
    )

    os.environ.setdefault("DAZ_RALPH_RUN_ID", run_id)
    os.environ.setdefault("DAZ_RALPH_LOG_DIR", str(log_dir))
    os.environ.setdefault("DAZ_RALPH_THREAD_ID", effective_thread)

    iteration_log = Path(os.environ.get("DAZ_RALPH_ITERATION_LOG", log_dir / f"{run_id}.iterations.jsonl")).expanduser()
    run_log = Path(os.environ.get("DAZ_RALPH_RUN_LOG", log_dir / f"{run_id}.run.md")).expanduser()
    iteration_log.parent.mkdir(parents=True, exist_ok=True)
    run_log.parent.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DAZ_RALPH_ITERATION_LOG", str(iteration_log))
    os.environ.setdefault("DAZ_RALPH_RUN_LOG", str(run_log))

    with iteration_log.open("a", encoding="utf-8") as file:
        file.flush()
        os.fsync(file.fileno())

    metadata = {
        "schema_version": 1,
        "event": "ralph_run_start",
        "run_id": run_id,
        "thread_id": effective_thread,
        "started_at_utc": started_at.isoformat(),
        "cwd": str(Path.cwd()),
        "goal_budget": goal_budget,
        "tenacity": tenacity,
        "goal_judge_tail": os.environ.get("DEEPAGENTS_CODE_GOAL_JUDGE_TAIL", "8"),
        "goal_judge_message_chars": os.environ.get("DEEPAGENTS_CODE_GOAL_JUDGE_MESSAGE_CHARS", "600"),
        "initial_prompt_chars": len(initial_prompt or ""),
        "iteration_log": str(iteration_log),
    }
    with run_log.open("a", encoding="utf-8") as file:
        file.write(f"# Ralph run {run_id}\n\n")
        file.write("```json\n")
        file.write(json.dumps(_json_safe(metadata), ensure_ascii=False, indent=2))
        file.write("\n```\n\n")
        file.flush()
        os.fsync(file.fileno())


async def run_ralph_tui_async(
    *,
    assistant_id: str,
    auto_approve: bool = False,
    sandbox_type: str = "none",
    sandbox_id: str | None = None,
    sandbox_setup: str | None = None,
    model_name: str | None = None,
    model_params: dict[str, Any] | None = None,
    profile_override: dict[str, Any] | None = None,
    thread_id: str | None = None,
    resume_thread: str | None = None,
    initial_prompt: str | None = None,
    initial_skill: str | None = None,
    startup_cmd: str | None = None,
    mcp_config_path: str | None = None,
    no_mcp: bool = False,
    trust_project_mcp: bool | None = None,
    tenacity: bool = True,
    goal_budget: int = 20,
    goal_judge_model: str | None = None,
) -> int:
    from rich.console import Console
    from rich.markup import escape
    from rich.text import Text

    from deepagents_code.app import AppResult, run_textual_app
    from deepagents_code.config import _get_default_model_spec, detect_provider, settings
    from deepagents_code.model_config import ModelConfigError, ModelSpec, NoCredentialsConfiguredError
    from deepagents_code.onboarding import should_run_onboarding

    console = Console()
    defer_server_start = False
    try:
        resolved_spec = model_name or _get_default_model_spec()
    except NoCredentialsConfiguredError:
        resolved_spec = ""
        defer_server_start = True
    except ModelConfigError as exc:
        console.print(f"[bold red]Error:[/bold red] {escape(str(exc))}", highlight=False)
        return 1

    if resolved_spec:
        parsed = ModelSpec.try_parse(resolved_spec)
        if parsed:
            settings.model_provider = parsed.provider
            settings.model_name = parsed.model
        else:
            settings.model_name = resolved_spec
            settings.model_provider = detect_provider(resolved_spec) or ""
    else:
        settings.model_provider = ""
        settings.model_name = ""

    model_kwargs = {
        "model_spec": model_name or resolved_spec,
        "extra_kwargs": model_params,
        "profile_overrides": profile_override,
    }
    server_kwargs: dict[str, Any] = {
        "assistant_id": assistant_id,
        "model_name": model_name or resolved_spec or None,
        "model_params": model_params,
        "sandbox_type": sandbox_type,
        "sandbox_id": sandbox_id,
        "sandbox_setup": sandbox_setup,
        "enable_ask_user": True,
        "mcp_config_path": mcp_config_path,
        "no_mcp": no_mcp,
        "trust_project_mcp": trust_project_mcp,
        "goal_mode": tenacity,
        "goal_budget": goal_budget,
        "goal_judge_model": goal_judge_model,
    }
    mcp_preload_kwargs: dict[str, Any] | None = None
    if mcp_config_path and not no_mcp:
        mcp_preload_kwargs = {
            "mcp_config_path": mcp_config_path,
            "trust_project_mcp": trust_project_mcp,
        }

    try:
        result: AppResult = await run_textual_app(
            assistant_id=assistant_id,
            auto_approve=auto_approve,
            thread_id=thread_id,
            resume_thread=resume_thread,
            initial_prompt=initial_prompt,
            initial_skill=initial_skill,
            startup_cmd=startup_cmd,
            launch_init=should_run_onboarding(),
            profile_override=profile_override,
            server_kwargs=server_kwargs,
            mcp_preload_kwargs=mcp_preload_kwargs,
            model_kwargs=model_kwargs,
            defer_server_start=defer_server_start,
            title="daz-ralph",
            sub_title="tenacity on" if tenacity else "tenacity off",
        )
    except Exception as exc:
        logger.debug("App error", exc_info=True)
        error_text = Text("Application error: ", style="red")
        error_text.append(str(exc))
        console.print(error_text)
        if logger.isEnabledFor(logging.DEBUG):
            console.print(Text(traceback.format_exc()), style="dim")
        return 1

    if result.thread_id and result.return_code == 0:
        console.print()
        console.print("[dim]Resume this Ralph thread with:[/dim]")
        console.print(f"[cyan]daz-ralph -r {result.thread_id}[/cyan]")
    return result.return_code


def build_parser() -> argparse.ArgumentParser:
    from deepagents_code._constants import DEFAULT_AGENT_NAME

    parser = argparse.ArgumentParser(
        prog="daz-ralph",
        description="Run the DeepAgents Code TUI with the Ralph/dcode-tenacity judge-nudge loop enabled.",
    )
    parser.add_argument("goal", nargs="*", help="Optional initial goal to auto-submit")
    parser.add_argument("-m", "--model", dest="model", help="Model spec, e.g. openai:<model> (for OpenAI or a local OMLX server)")
    parser.add_argument("--model-params", type=_json_object, default=None, help="Extra model kwargs as a JSON object")
    parser.add_argument("-a", "--agent", default=DEFAULT_AGENT_NAME, help="DeepAgents assistant/agent id")
    parser.add_argument("-r", "--resume", nargs="?", const="_MOST_RECENT_", dest="resume_thread", help="Resume the most recent thread or the given thread id")
    parser.add_argument("-p", "--prompt", dest="initial_prompt", help="Initial goal to auto-submit")
    parser.add_argument("--skill", dest="initial_skill", help="Skill to invoke when the TUI starts")
    parser.add_argument("--startup-cmd", help="Shell command to run before the first prompt")
    parser.add_argument("-y", "--auto-approve", action="store_true", help="Auto-approve tool calls in the TUI")
    parser.add_argument("--sandbox", default="none", help="Sandbox provider, e.g. none, daytona")
    parser.add_argument("--sandbox-id", default=None, help="Existing sandbox id to attach to")
    parser.add_argument("--sandbox-setup", default=None, help="Setup script for the sandbox")
    parser.add_argument("--mcp-config", dest="mcp_config", default=None, help="Path to MCP config JSON")
    parser.add_argument("--no-mcp", action="store_true", help="Disable MCP loading")
    parser.add_argument("--trust-project-mcp", action="store_true", help="Trust project-scoped MCP servers")
    parser.set_defaults(tenacity=_env_bool("DAZ_RALPH_TENACITY", default=True))
    parser.add_argument("--tenacity", dest="tenacity", action="store_true", help="Enable Ralph wrapping")
    parser.add_argument("--no-tenacity", dest="tenacity", action="store_false", help="Run plain DeepAgents Code TUI without Ralph wrapping")
    parser.add_argument("--goal-budget", type=_positive_int, default=int(os.environ.get("DAZ_RALPH_GOAL_BUDGET", "20")), help="Maximum inner agent turns per locked goal")
    parser.add_argument("--goal-judge-model", default=os.environ.get("DAZ_RALPH_JUDGE_MODEL"), help="Model spec for the acceptance judge")
    parser.add_argument("--profile-override", type=_json_object, default=None, help="Profile overrides as a JSON object")
    parser.add_argument("--version", action="version", version=f"daz-ralph {__version__}")
    return parser


def main(argv: list[str] | None = None) -> None:
    from deepagents_code.sessions import generate_thread_id

    parser = build_parser()
    args = parser.parse_args(argv)
    initial_prompt = args.initial_prompt or (" ".join(args.goal).strip() or None)
    thread_id = None if args.resume_thread else generate_thread_id()
    _configure_ralph_log_env(
        thread_id=thread_id,
        resume_thread=args.resume_thread,
        initial_prompt=initial_prompt,
        goal_budget=args.goal_budget,
        tenacity=args.tenacity,
    )

    try:
        exit_code = asyncio.run(
            run_ralph_tui_async(
                assistant_id=args.agent,
                auto_approve=args.auto_approve,
                sandbox_type=args.sandbox,
                sandbox_id=args.sandbox_id,
                sandbox_setup=args.sandbox_setup,
                model_name=args.model,
                model_params=args.model_params,
                profile_override=args.profile_override,
                thread_id=thread_id,
                resume_thread=args.resume_thread,
                initial_prompt=initial_prompt,
                initial_skill=args.initial_skill,
                startup_cmd=args.startup_cmd,
                mcp_config_path=args.mcp_config,
                no_mcp=args.no_mcp,
                trust_project_mcp=True if args.trust_project_mcp else None,
                tenacity=args.tenacity,
                goal_budget=args.goal_budget,
                goal_judge_model=args.goal_judge_model,
            )
        )
    except KeyboardInterrupt:
        sys.stderr.write("\ninterrupted\n")
        raise SystemExit(130) from None
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
