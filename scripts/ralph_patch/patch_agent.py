"""Patch agent.py: middleware injection, sync subagent guard, runtime install guard."""
from __future__ import annotations

from pathlib import Path

from ._shared import replace_once


def run(agent_py: Path) -> None:
    # Import the runtime install guard middleware
    replace_once(
        agent_py,
        "from deepagents_code.project_utils import ProjectContext, get_server_project_context\n",
        "from deepagents_code.project_utils import ProjectContext, get_server_project_context\nfrom deepagents_code.runtime_install_guard import RalphRuntimeInstallGuardMiddleware\n",
    )

    # Add the DISABLE_SYNC_SUBAGENTS_ENV constant and helpers
    replace_once(
        agent_py,
        '''REQUIRE_COMPACT_TOOL_APPROVAL: bool = True
"""When `True`, `compact_conversation` requires HITL approval like other gated tools."""
''',
        '''REQUIRE_COMPACT_TOOL_APPROVAL: bool = True
"""When `True`, `compact_conversation` requires HITL approval like other gated tools."""

DISABLE_SYNC_SUBAGENTS_ENV = "DEEPAGENTS_CODE_DISABLE_SYNC_SUBAGENTS"
"""Env var that disables synchronous subagents and the `task` tool."""

_NO_SYNC_SUBAGENT_PROFILE_KEYS: set[str] = set()


def _truthy_env(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _append_harness_profile_key(keys: list[str], key: str | None) -> None:
    cleaned = (key or "").strip()
    if not cleaned:
        return
    if cleaned.startswith(":") or cleaned.endswith(":") or cleaned.count(":") > 1:
        return
    keys.append(cleaned)


def _register_no_sync_subagents_profile(model: str | BaseChatModel) -> None:
    """Disable the default sync subagent for the active model/provider."""
    from deepagents.profiles.harness import (
        GeneralPurposeSubagentProfile,
        HarnessProfile,
        register_harness_profile,
    )
    from deepagents._models import get_model_identifier, get_model_provider

    keys: list[str] = []
    provider = (settings.model_provider or "").strip()
    model_name = (settings.model_name or "").strip()
    if provider:
        _append_harness_profile_key(keys, provider)
        if model_name:
            _append_harness_profile_key(keys, f"{provider}:{model_name}")
    try:
        detected_provider = (get_model_provider(model) or "").strip()
        detected_identifier = (get_model_identifier(model) or "").strip()
    except Exception:
        detected_provider = ""
        detected_identifier = ""
    if detected_provider:
        _append_harness_profile_key(keys, detected_provider)
        if detected_identifier and ":" not in detected_identifier:
            _append_harness_profile_key(
                keys, f"{detected_provider}:{detected_identifier}"
            )
    if detected_identifier and ":" in detected_identifier:
        _append_harness_profile_key(keys, detected_identifier)
    if isinstance(model, str) and model.strip():
        _append_harness_profile_key(keys, model.strip())
        if ":" in model:
            _append_harness_profile_key(keys, model.split(":", 1)[0].strip())

    for key in dict.fromkeys(k for k in keys if k):
        if key in _NO_SYNC_SUBAGENT_PROFILE_KEYS:
            continue
        register_harness_profile(
            key,
            HarnessProfile(
                general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)
            ),
        )
        _NO_SYNC_SUBAGENT_PROFILE_KEYS.add(key)
''',
    )

    # Wrap subagent middleware with RalphRuntimeInstallGuardMiddleware. In 0.1.27
    # subagent middleware is built once in the _subagent_cli_middleware helper
    # (covers both filesystem subagents and the general-purpose subagent), so the
    # guard is injected there, before the shell allow-list middleware.
    replace_once(
        agent_py,
        '''        if restrictive_shell_allow_list is not None:
            middleware.append(ShellAllowListMiddleware(restrictive_shell_allow_list))
''',
        '''        if restrictive_shell_allow_list is not None:
            middleware.append(RalphRuntimeInstallGuardMiddleware())
            middleware.append(ShellAllowListMiddleware(restrictive_shell_allow_list))
''',
    )

    # Add runtime guard middleware to agent_middleware when no sandbox
    replace_once(
        agent_py,
        '''    agent_middleware: list[AgentMiddleware[Any, Any]] = [
        ConfigurableModelMiddleware(),
    ]

    # Resume state: declares the `_context_tokens` and `_model_spec` channels
''',
        '''    agent_middleware: list[AgentMiddleware[Any, Any]] = [
        ConfigurableModelMiddleware(),
    ]

    if sandbox is None and enable_shell:
        agent_middleware.append(RalphRuntimeInstallGuardMiddleware())

    # Resume state: declares the `_context_tokens` and `_model_spec` channels
''',
    )

    # Guard the subagent listing with DISABLE_SYNC_SUBAGENTS_ENV
    replace_once(
        agent_py,
        '''    for subagent_meta in list_subagents(
        user_agents_dir=user_agents_dir,
        project_agents_dir=project_agents_dir,
    ):
        # Treat a falsy spec (`None` or `""`) as "no explicit model" so an empty
        # `model:` in subagent frontmatter inherits the runtime model rather than
        # being forwarded verbatim to `resolve_model("")`.
        model_spec = subagent_meta["model"]
        has_explicit_model = bool(model_spec)
        subagent: SubAgent = {
            "name": subagent_meta["name"],
            "description": subagent_meta["description"],
            "system_prompt": subagent_meta["system_prompt"],
        }
        if model_spec:
            subagent["model"] = model_spec
        subagent_middleware = _subagent_cli_middleware(
            has_explicit_model=has_explicit_model
        )
        if subagent_middleware:
            subagent["middleware"] = subagent_middleware
        custom_subagents.append(subagent)

    from deepagents.middleware.subagents import (
        GENERAL_PURPOSE_SUBAGENT,
        SubAgent as RuntimeSubAgent,
    )

    if not any(
        subagent["name"] == GENERAL_PURPOSE_SUBAGENT["name"]
        for subagent in custom_subagents
    ):
        general_purpose_subagent: RuntimeSubAgent = {
            "name": GENERAL_PURPOSE_SUBAGENT["name"],
            "description": GENERAL_PURPOSE_SUBAGENT["description"],
            "system_prompt": GENERAL_PURPOSE_SUBAGENT["system_prompt"],
            "middleware": _subagent_cli_middleware(has_explicit_model=False),
        }
        custom_subagents.append(general_purpose_subagent)
''',
        '''    disable_sync_subagents = _truthy_env(os.environ.get(DISABLE_SYNC_SUBAGENTS_ENV))
    if disable_sync_subagents:
        _register_no_sync_subagents_profile(model)
        logger.info(
            "Synchronous subagents disabled by %s", DISABLE_SYNC_SUBAGENTS_ENV
        )
    else:
        for subagent_meta in list_subagents(
            user_agents_dir=user_agents_dir,
            project_agents_dir=project_agents_dir,
        ):
            # Treat a falsy spec (`None` or `""`) as "no explicit model" so an empty
            # `model:` in subagent frontmatter inherits the runtime model rather than
            # being forwarded verbatim to `resolve_model("")`.
            model_spec = subagent_meta["model"]
            has_explicit_model = bool(model_spec)
            subagent: SubAgent = {
                "name": subagent_meta["name"],
                "description": subagent_meta["description"],
                "system_prompt": subagent_meta["system_prompt"],
            }
            if model_spec:
                subagent["model"] = model_spec
            subagent_middleware = _subagent_cli_middleware(
                has_explicit_model=has_explicit_model
            )
            if subagent_middleware:
                subagent["middleware"] = subagent_middleware
            custom_subagents.append(subagent)

        from deepagents.middleware.subagents import (
            GENERAL_PURPOSE_SUBAGENT,
            SubAgent as RuntimeSubAgent,
        )

        if not any(
            subagent["name"] == GENERAL_PURPOSE_SUBAGENT["name"]
            for subagent in custom_subagents
        ):
            general_purpose_subagent: RuntimeSubAgent = {
                "name": GENERAL_PURPOSE_SUBAGENT["name"],
                "description": GENERAL_PURPOSE_SUBAGENT["description"],
                "system_prompt": GENERAL_PURPOSE_SUBAGENT["system_prompt"],
                "middleware": _subagent_cli_middleware(has_explicit_model=False),
            }
            custom_subagents.append(general_purpose_subagent)
''',
    )
