"""Entry point for the Ralph/tenacity overlay patch.

Reads BASE_DIR, REPO_DIR, and RALPH_OVERLAY from environment. Copies overlay
packages into the installed deepagents-code tree, then applies text-replacement
patches to add goal-mode, runtime-protection middleware, and config overrides.
"""
from __future__ import annotations

import os
from pathlib import Path

from . import (
    copy_overlays,
    patch_agent,
    patch_configurable_model,
    patch_pyproject,
    patch_server,
)

base_dir = Path(os.environ.get("BASE_DIR", Path(__file__).resolve().parents[1]))
repo_dir = Path(os.environ.get("REPO_DIR", base_dir / "deepagents-main"))
overlay_dir = Path(os.environ.get("RALPH_OVERLAY", base_dir / "scripts" / "ralph_overlay"))

code_project_dir = repo_dir / "libs" / "code"
code_pkg_dir = code_project_dir / "deepagents_code"

if not code_pkg_dir.is_dir():
    raise SystemExit(f"ERROR: missing deepagents-code package dir {code_pkg_dir}")


def main() -> None:
    # 1. Copy overlay packages
    copy_overlays.run(overlay_dir, code_project_dir, code_pkg_dir)

    # 2. Patch core files
    patch_agent.run(code_pkg_dir / "agent.py")
    patch_configurable_model.run(code_pkg_dir / "configurable_model.py")
    patch_server.run(
        code_pkg_dir / "_server_config.py",
        code_pkg_dir / "server_graph.py",
        code_pkg_dir / "client" / "launch" / "server_manager.py",
    )
    patch_pyproject.run(
        code_project_dir / "pyproject.toml",
        code_pkg_dir / "system_prompt.md",
    )

    print("Applied Ralph/tenacity overlay to deepagents-code")


if __name__ == "__main__":
    main()
