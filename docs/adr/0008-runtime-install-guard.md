# ADR-0008: Block agent shell commands that pip-install into Ralph's own runtime

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

An autonomous loop that runs `pip install` with Ralph's interpreter can break Ralph between iterations (guard rejection text). TODO-ROADMAP lists "Runtime install guard so the agent doesn't trash its own env" as already done.

## Decision

Overlay `runtime_install_guard.py` adds `RalphRuntimeInstallGuardMiddleware`, which inspects the `command` argument of tool calls and returns an error `ToolMessage` when `command_installs_into_ralph_runtime()` is true: `python -m pip install`, `pip install`, or `uv pip install` (including `--system`, or `--python` pointing at Ralph) where the executable is a bare name or a path into Ralph's bin dir. Commands are split on `&&`, `||`, `;`, `|`, and leading env assignments, `env` and `command` are stripped. Paths outside Ralph (e.g. `.venv/bin/python -m pip install`) and `--target/--prefix` are allowed. `DEEPAGENTS_CODE_ALLOW_RALPH_ENV_PIP_INSTALL=1` disables it. `patch_agent.py` adds it to the main agent middleware when there is no sandbox and shell is enabled, and to subagent middleware ahead of `ShellAllowListMiddleware` when a restrictive allow-list is set. ralph_install.sh asserts the two canonical cases after install.

## Consequences

### Positive

- Agents are steered to create a separate venv instead of mutating the running one.

### Negative

- Heuristic, not a sandbox: wrappers such as `sudo` or `bash -c "pip install …"` are not parsed (A-007).
- A bare `python -m pip install` is always treated as Ralph's runtime, even if PATH resolves to another interpreter.

## Alternatives considered

- Rely on a remote/OS sandbox (TODO-ROADMAP P8, later).

## Evidence

- scripts/ralph_overlay/deepagents_code/runtime_install_guard.py
- scripts/ralph_patch/patch_agent.py
- scripts/ralph_install.sh (Ralph overlays ok assertions)
- TODO-ROADMAP.md
