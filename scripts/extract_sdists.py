#!/usr/bin/env python3
"""Extract DeepAgents source distributions into the repo libs/ layout.

Reads SDIST_DIR and REPO_DIR from environment. Downloads .tar.gz archives are
expected under ${SDIST_DIR}; extracted packages are laid out under
${REPO_DIR}/libs/{deepagents,acp,code}.
"""
from __future__ import annotations

import os
import re
import shutil
import tarfile
from pathlib import Path

SDIST_DIR = Path(os.environ["SDIST_DIR"])
REPO_DIR = Path(os.environ["REPO_DIR"])
UNPACKED_DIR = SDIST_DIR / "unpacked"

LAYOUT = {
    "deepagents": "deepagents",
    "deepagents-acp": "acp",
    "deepagents-code": "code",
}


def extract_all(archive_dir: Path, dest: Path) -> None:
    """Extract every .tar.gz under *archive_dir* into *dest*."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for archive in sorted(archive_dir.glob("*.tar.gz")):
        with tarfile.open(archive) as tf:
            tf.extractall(dest, filter="data")


def detect_packages(extract_dir: Path) -> dict[str, Path]:
    """Return {package_name: source_root_path} by scanning pyproject.toml files."""
    found: dict[str, Path] = {}
    for pyproject in extract_dir.glob("*/pyproject.toml"):
        text = pyproject.read_text(encoding="utf-8")
        match = re.search(r'^name\s*=\s*"([^"]+)"', text, re.MULTILINE)
        if match:
            found[match.group(1)] = pyproject.parent
    return found


def layout_packages(found: dict[str, Path], libs_dir: Path) -> None:
    """Copy each detected package into libs/<target_name>/."""
    for package_name, target_name in LAYOUT.items():
        if package_name not in found:
            raise SystemExit(f"Missing expected source distribution: {package_name}")
        target = libs_dir / target_name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(found[package_name], target)


def main() -> None:
    extract_all(SDIST_DIR, UNPACKED_DIR)
    found = detect_packages(UNPACKED_DIR)
    layout_packages(found, REPO_DIR / "libs")
    print(f"Prepared DeepAgents source layout under {REPO_DIR}")


if __name__ == "__main__":
    main()
