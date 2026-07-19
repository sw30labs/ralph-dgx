from __future__ import annotations

import os
from dataclasses import dataclass
from importlib import util
from pathlib import Path

MODULES_TO_CHECK = (
    "deepagents_code.config",
    "deepagents_code.model_config",
    "deepagents_code.server_config",
    "deepagents_code.server_manager",
    "daz_ralph.main",
    "dcode_tenacity.graph",
    "dcode_tenacity.inner",
    "dcode_tenacity.judge",
    "dcode_tenacity.state",
)

VENDORED_MODULES = (
    "daz_ralph.main",
    "dcode_tenacity.graph",
    "dcode_tenacity.inner",
    "dcode_tenacity.judge",
    "dcode_tenacity.state",
)

PATCH_MARKERS = {
    "daz_ralph.main": ("run_textual_app", "goal_mode"),
    "deepagents_code.config": ("use_responses_api", "responses/v1"),
    "deepagents_code.server_config": ("goal_mode: bool = False", "GOAL_MODE"),
    "deepagents_code.goal": ("def wrap_goal_graph(", "judge_goal", "nudge_goal"),
    "deepagents_code.server_graph": ("wrap_goal_graph", "goal_mode"),
    "dcode_tenacity.graph": ("def build_graph", 'g.add_node("nudge", nudge_node)'),
    "dcode_tenacity.inner": ("def load_inner_agent", "create_deep_agent"),
    "dcode_tenacity.judge": ("class JudgeOutput", "def nudge_node"),
    "dcode_tenacity.state": ("class GoalState", "budget: int"),
}


@dataclass(frozen=True)
class ModuleOrigin:
    module: str
    locations: tuple[Path, ...]


class RuntimeVerificationError(RuntimeError):
    pass


def _origin_locations(module_name: str) -> tuple[Path, ...]:
    spec = util.find_spec(module_name)
    if spec is None:
        raise RuntimeVerificationError(f"Could not resolve import spec for {module_name}")

    locations: list[Path] = []
    if spec.origin and spec.origin not in ("built-in", "namespace"):
        locations.append(Path(spec.origin).resolve())
    if spec.submodule_search_locations:
        locations.extend(Path(item).resolve() for item in spec.submodule_search_locations)
    return tuple(dict.fromkeys(locations))


def _location_under(location: Path, root: Path) -> bool:
    return location == root or root in location.parents


def _install_roots_for_package(package_name: str) -> tuple[Path, ...]:
    roots: list[Path] = []
    for location in _origin_locations(package_name):
        package_dir = location.parent if location.is_file() else location
        if package_dir.name == package_name:
            roots.append(package_dir.parent)
    return tuple(dict.fromkeys(roots))


def _source_file(locations: tuple[Path, ...]) -> Path | None:
    for location in locations:
        if location.is_file() and location.suffix == ".py":
            return location
    return None


def _verify_patch_markers(module_name: str, locations: tuple[Path, ...]) -> None:
    markers = PATCH_MARKERS.get(module_name)
    if not markers:
        return
    source_file = _source_file(locations)
    if source_file is None:
        raise RuntimeVerificationError(f"{module_name} did not resolve to a Python source file")
    source = source_file.read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in source]
    if missing:
        raise RuntimeVerificationError(f"{module_name} resolved to {source_file}, but is missing marker(s): {missing}")


def verify_runtime_origins(
    *,
    parent_repo: Path = Path("/projects/langgraph-deepagents-cli"),
    expected_project: Path | None = None,
    modules: tuple[str, ...] = MODULES_TO_CHECK,
) -> tuple[ModuleOrigin, ...]:
    if "PYTHONPATH" in os.environ:
        raise RuntimeVerificationError(f"PYTHONPATH unexpectedly set to {os.environ['PYTHONPATH']!r}")

    parent_repo = parent_repo.resolve()
    expected_raw = os.environ.get("DAZ_RALPH_VERIFY_PROJECT_DIR")
    expected_project = (expected_project or Path(expected_raw)) if expected_raw else expected_project
    expected_project = expected_project.resolve() if expected_project is not None else None
    install_roots = _install_roots_for_package("daz_ralph")
    if not install_roots:
        raise RuntimeVerificationError("Could not determine daz-ralph install root")

    forbidden_named_roots = (parent_repo / "deepagents-main", parent_repo / "dcode-tenacity")
    origins: list[ModuleOrigin] = []
    for module_name in modules:
        locations = _origin_locations(module_name)
        for location in locations:
            if any(_location_under(location, root) for root in forbidden_named_roots):
                raise RuntimeVerificationError(f"{module_name} resolved from forbidden sibling source path: {location}")
            if _location_under(location, parent_repo):
                raise RuntimeVerificationError(f"{module_name} resolved from parent repo instead of install: {location}")
            if expected_project is not None and _location_under(location, expected_project):
                raise RuntimeVerificationError(f"{module_name} resolved from copied source tree instead of installed package: {locations}")
            if module_name in VENDORED_MODULES and not any(_location_under(location, root) for root in install_roots):
                raise RuntimeVerificationError(f"{module_name} did not resolve under daz-ralph install root: {location}")
        _verify_patch_markers(module_name, locations)
        origins.append(ModuleOrigin(module_name, locations))
    return tuple(origins)


def main() -> None:
    origins = verify_runtime_origins()
    print("runtime import origin scan passed")
    for origin in origins:
        rendered = ", ".join(str(location) for location in origin.locations) or "<unknown>"
        print(f"origin {origin.module}: {rendered}")


if __name__ == "__main__":
    main()
