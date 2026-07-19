"""Copy Ralph overlay packages into the installed deepagents-code tree."""
from __future__ import annotations

from pathlib import Path

from ._shared import copy_file, copy_tree


def run(overlay_dir: Path, code_project_dir: Path, code_pkg_dir: Path) -> None:
    """Copy overlay dirs and files into the installed package."""
    copy_tree(overlay_dir / "daz_ralph", code_project_dir / "daz_ralph")
    copy_tree(overlay_dir / "dcode_tenacity", code_project_dir / "dcode_tenacity")
    copy_file(overlay_dir / "deepagents_code" / "goal.py", code_pkg_dir / "goal.py")
    copy_file(
        overlay_dir / "deepagents_code" / "runtime_install_guard.py",
        code_pkg_dir / "runtime_install_guard.py",
    )
