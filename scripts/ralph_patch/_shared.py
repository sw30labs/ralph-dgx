"""Shared utilities for Ralph overlay patch modules."""
from __future__ import annotations

import shutil
from pathlib import Path


def replace_once(path: Path, old: str, new: str, *, already: str | None = None) -> None:
    """Replace *old* with *new* in *path* exactly once.

    Raises ``SystemExit`` if *old* is not found (the upstream anchor has
    likely changed and the patch needs re-derivation).
    """
    text = path.read_text(encoding="utf-8")
    if new in text or (already is not None and already in text):
        return
    if old not in text:
        snippet = " ".join(old.strip().split())[:160]
        raise SystemExit(
            f"ERROR: expected Ralph patch anchor not found in {path}: {snippet}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def copy_tree(src: Path, dst: Path) -> None:
    if not src.is_dir():
        raise SystemExit(f"ERROR: missing Ralph overlay directory {src}")
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def copy_file(src: Path, dst: Path) -> None:
    if not src.is_file():
        raise SystemExit(f"ERROR: missing Ralph overlay file {src}")
    shutil.copy2(src, dst)
