"""Patch pyproject.toml and system_prompt.md for overlay entry points."""
from __future__ import annotations

from pathlib import Path

from ._shared import replace_once


def run(pyproject: Path, system_prompt: Path) -> None:
    # Add daz-ralph and dcode-tenacity entry points
    replace_once(
        pyproject,
        'deepagents-code = "deepagents_code:cli_main"\ndcode = "deepagents_code:cli_main"\n',
        'deepagents-code = "deepagents_code:cli_main"\ndcode = "deepagents_code:cli_main"\ndaz-ralph = "daz_ralph.main:main"\ndcode-tenacity = "dcode_tenacity.runner:main"\n',
    )

    # Add overlay packages to the packages list
    replace_once(
        pyproject,
        'packages = ["deepagents_code"]\n',
        'packages = ["deepagents_code", "daz_ralph", "dcode_tenacity"]\n',
    )

    # Include overlay sources in the manifest
    replace_once(
        pyproject,
        '''    "deepagents_code/**/*.tcss",
]
''',
        '''    "deepagents_code/**/*.tcss",
    "daz_ralph/**/*.py",
    "dcode_tenacity/**/*.py",
]
''',
    )

    # Update system prompt example if it exists
    if system_prompt.exists():
        replace_once(
            system_prompt,
            "<good-example>\npytest /foo/bar/tests\n</good-example>\n",
            "<good-example>\nuv run --group test pytest /foo/bar/tests\n</good-example>\n",
        )
