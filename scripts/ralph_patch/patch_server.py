"""Patch server config, graph, and manager for goal-mode wiring."""
from __future__ import annotations

from pathlib import Path

from ._shared import replace_once


def run(
    server_config: Path,
    server_graph: Path,
    server_manager: Path,
) -> None:
    # _server_config.py: add goal_mode, goal_budget, goal_judge_model fields
    replace_once(
        server_config,
        '''    trust_project_mcp: bool | None = None
    """Tri-state trust flag for project-scoped MCP servers: `True`/`False`/`None`
    (prompt user)."""

    def __post_init__(self) -> None:
''',
        '''    trust_project_mcp: bool | None = None
    """Tri-state trust flag for project-scoped MCP servers: `True`/`False`/`None`
    (prompt user)."""

    goal_mode: bool = False
    """Enable the Ralph/tenacity judge-nudge loop."""

    goal_budget: int = 20
    """Maximum Ralph/tenacity loop turns."""

    goal_judge_model: str | None = None
    """Optional model spec for the Ralph completion judge."""

    def __post_init__(self) -> None:
''',
    )

    replace_once(
        server_config,
        '''            "TRUST_PROJECT_MCP": (
                str(self.trust_project_mcp).lower()
                if self.trust_project_mcp is not None
                else None
            ),
        }
''',
        '''            "TRUST_PROJECT_MCP": (
                str(self.trust_project_mcp).lower()
                if self.trust_project_mcp is not None
                else None
            ),
            "GOAL_MODE": str(self.goal_mode).lower(),
            "GOAL_BUDGET": str(self.goal_budget),
            "GOAL_JUDGE_MODEL": self.goal_judge_model,
        }
''',
    )

    replace_once(
        server_config,
        '''            no_mcp=_read_env_bool("NO_MCP"),
            trust_project_mcp=_read_env_optional_bool("TRUST_PROJECT_MCP"),
        )
''',
        '''            no_mcp=_read_env_bool("NO_MCP"),
            trust_project_mcp=_read_env_optional_bool("TRUST_PROJECT_MCP"),
            goal_mode=_read_env_bool("GOAL_MODE"),
            goal_budget=int(_read_env_str("GOAL_BUDGET") or "20"),
            goal_judge_model=_read_env_str("GOAL_JUDGE_MODEL") or None,
        )
''',
    )

    replace_once(
        server_config,
        '''        no_mcp: bool,
        trust_project_mcp: bool | None,
        interactive: bool,
    ) -> ServerConfig:
''',
        '''        no_mcp: bool,
        trust_project_mcp: bool | None,
        goal_mode: bool = False,
        goal_budget: int = 20,
        goal_judge_model: str | None = None,
        interactive: bool = True,
    ) -> ServerConfig:
''',
    )

    replace_once(
        server_config,
        '''            no_mcp=no_mcp,
            trust_project_mcp=trust_project_mcp,
        )
''',
        '''            no_mcp=no_mcp,
            trust_project_mcp=trust_project_mcp,
            goal_mode=goal_mode,
            goal_budget=goal_budget,
            goal_judge_model=goal_judge_model,
        )
''',
    )

    # server_manager.py: thread goal params through
    replace_once(
        server_manager,
        '''    trust_project_mcp: bool | None = None,
    interactive: bool = True,
    host: str = "127.0.0.1",
''',
        '''    trust_project_mcp: bool | None = None,
    goal_mode: bool = False,
    goal_budget: int = 20,
    goal_judge_model: str | None = None,
    interactive: bool = True,
    host: str = "127.0.0.1",
''',
    )

    replace_once(
        server_manager,
        '''        trust_project_mcp=trust_project_mcp,
        interactive=interactive,
    )
''',
        '''        trust_project_mcp=trust_project_mcp,
        goal_mode=goal_mode,
        goal_budget=goal_budget,
        goal_judge_model=goal_judge_model,
        interactive=interactive,
    )
''',
    )

    replace_once(
        server_manager,
        '''    trust_project_mcp: bool | None = None,
    interactive: bool = True,
    host: str = "127.0.0.1",
    port: int = _EPHEMERAL_PORT,
) -> AsyncIterator[tuple[RemoteAgent, ServerProcess]]:
''',
        '''    trust_project_mcp: bool | None = None,
    goal_mode: bool = False,
    goal_budget: int = 20,
    goal_judge_model: str | None = None,
    interactive: bool = True,
    host: str = "127.0.0.1",
    port: int = _EPHEMERAL_PORT,
) -> AsyncIterator[tuple[RemoteAgent, ServerProcess]]:
''',
    )

    replace_once(
        server_manager,
        '''            trust_project_mcp=trust_project_mcp,
            interactive=interactive,
            host=host,
''',
        '''            trust_project_mcp=trust_project_mcp,
            goal_mode=goal_mode,
            goal_budget=goal_budget,
            goal_judge_model=goal_judge_model,
            interactive=interactive,
            host=host,
''',
    )

    # server_graph.py: wrap with goal graph when goal_mode is set. In 0.1.27 the
    # agent is built in a nested sync helper and returned via asyncio.to_thread;
    # `config` (from ServerConfig.from_env()) is in scope at that return.
    replace_once(
        server_graph,
        '''    return await asyncio.to_thread(_create_cli_agent_sync)
''',
        '''    agent = await asyncio.to_thread(_create_cli_agent_sync)
    if config.goal_mode:
        from deepagents_code.goal import wrap_goal_graph

        return wrap_goal_graph(
            agent,
            budget=config.goal_budget,
            judge_model_name=config.goal_judge_model,
        )
    return agent
''',
    )
