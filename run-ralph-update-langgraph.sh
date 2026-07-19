#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/lib/common.sh"

PROMPT_FILE="${RALPH_UPDATE_PROMPT_FILE:-${SCRIPT_DIR}/docs/upgradeLangGraphDeepAgentsStackSafely.md}"
BACKUP_ROOT="${RALPH_UPDATE_BACKUP_ROOT:-${SCRIPT_DIR}/backups/last-known-good}"
SKIP_RALPH="${RALPH_UPDATE_SKIP_RALPH:-false}"
SKIP_VALIDATE="${RALPH_UPDATE_SKIP_VALIDATE:-false}"
SKIP_COMMIT="${RALPH_UPDATE_SKIP_COMMIT:-false}"
NO_MCP="${RALPH_UPDATE_NO_MCP:-true}"
AUTO_APPROVE="${RALPH_UPDATE_AUTO_APPROVE:-true}"
REQUIRE_RALPH_DONE="${RALPH_UPDATE_REQUIRE_DONE:-true}"
VALIDATE_CMD="${RALPH_UPDATE_VALIDATE_CMD:-./setup-and-run.sh --vllm --no-run}"
COMMIT_MESSAGE="${RALPH_UPDATE_COMMIT_MESSAGE:-Safely update DeepAgents/LangGraph stack}"

require_file() {
    local path="$1"
    if [[ ! -f "${path}" ]]; then
        echo "Missing file: ${path}" >&2
        exit 1
    fi
}

copy_if_exists() {
    local src="$1"
    local dst="$2"
    if [[ -e "${src}" ]]; then
        mkdir -p "$(dirname -- "${dst}")"
        cp -a "${src}" "${dst}"
    fi
}

latest_ralph_verdict_done() {
    local log_path="$1"
    [[ -s "${log_path}" ]] || return 1
    python3 - "${log_path}" <<'PY'
import json
import sys
from pathlib import Path

last = ""
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if line.strip():
        last = line

if not last:
    raise SystemExit(1)

try:
    verdict = json.loads(last)
except json.JSONDecodeError:
    raise SystemExit(1)

raise SystemExit(0 if verdict.get("done") is True else 1)
PY
}

require_file "${PROMPT_FILE}"
if [[ "${PROMPT_FILE}" != *.md ]]; then
    echo "Prompt file must be Markdown: ${PROMPT_FILE}" >&2
    exit 1
fi
if [[ ! -s "${PROMPT_FILE}" ]] || [[ -z "$(tr -d '[:space:]' < "${PROMPT_FILE}")" ]]; then
    echo "Prompt file must be non-empty Markdown text: ${PROMPT_FILE}" >&2
    exit 1
fi
if ! grep -qE '^# .+' "${PROMPT_FILE}"; then
    echo "Prompt file must start with a top-level Markdown heading, e.g. '# Goal'." >&2
    exit 1
fi

cd "${SCRIPT_DIR}"
load_project_env
configure_provider_defaults
require_model_provider_env
configure_deepagents_defaults

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "This update workflow must run inside a git repository." >&2
    exit 1
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="${BACKUP_ROOT}/${timestamp}"
run_step "Backing up last-known-good configuration to ${backup_dir}" mkdir -p "${backup_dir}"
copy_if_exists "${SCRIPT_DIR}/constraints.txt" "${backup_dir}/constraints.txt"
copy_if_exists "${SCRIPT_DIR}/.env.example" "${backup_dir}/.env.example"
copy_if_exists "${SCRIPT_DIR}/.env" "${backup_dir}/env.redacted"
if [[ -f "${backup_dir}/env.redacted" ]]; then
    sed -i -E 's/(API_KEY|TOKEN|SECRET|PASSWORD)=.*/\1=REDACTED/g' "${backup_dir}/env.redacted"
fi
while IFS= read -r toml_file; do
    rel_path="${toml_file#${SCRIPT_DIR}/}"
    copy_if_exists "${toml_file}" "${backup_dir}/repo/${rel_path}"
done < <(find "${SCRIPT_DIR}" \
    -path "${SCRIPT_DIR}/deepagents-main" -prune -o \
    -path "${SCRIPT_DIR}/deepagents-sdists" -prune -o \
    -path "${SCRIPT_DIR}/backups" -prune -o \
    -path "${SCRIPT_DIR}/logs" -prune -o \
    -path "${SCRIPT_DIR}/.git" -prune -o \
    -name '*.toml' -type f -print)
copy_if_exists "${HOME}/.deepagents/config.toml" "${backup_dir}/home/.deepagents/config.toml"

unset PYTHONPATH

RALPH_CMD=(python -m daz_ralph)
if command -v daz-ralph >/dev/null 2>&1 && daz-ralph --version >/dev/null 2>&1; then
    RALPH_CMD=(daz-ralph)
fi

if [[ "${SKIP_RALPH}" != "true" ]]; then
    PROMPT_CONTENT="$(<"${PROMPT_FILE}")"
    RALPH_EXTRA_ARGS=()
    if [[ "${NO_MCP}" == "true" ]]; then
        RALPH_EXTRA_ARGS+=(--no-mcp)
    fi
    # This wrapper runs headless, so the TUI's tool-approval prompt would block
    # forever on the first command. Auto-approve unless explicitly disabled.
    if [[ "${AUTO_APPROVE}" == "true" ]]; then
        RALPH_EXTRA_ARGS+=(--auto-approve)
    fi
    export DAZ_RALPH_RUN_ID="${DAZ_RALPH_RUN_ID:-${timestamp}-update-$$}"
    export DAZ_RALPH_ITERATION_LOG="${DAZ_RALPH_ITERATION_LOG:-${DAZ_RALPH_LOG_DIR}/${DAZ_RALPH_RUN_ID}.iterations.jsonl}"
    export DAZ_RALPH_RUN_LOG="${DAZ_RALPH_RUN_LOG:-${DAZ_RALPH_LOG_DIR}/${DAZ_RALPH_RUN_ID}.run.md}"
    # Guard the expansion: with NO_MCP=false and AUTO_APPROVE=false the array is
    # empty, and an unguarded "${arr[@]}" crashes under `set -u` on bash 3.2.
    run_step "Running Ralph update goal" "${RALPH_CMD[@]}" \
        --model "$(model_spec)" \
        --goal-budget "${RALPH_UPDATE_GOAL_BUDGET:-50}" \
        ${RALPH_EXTRA_ARGS[@]+"${RALPH_EXTRA_ARGS[@]}"} \
        --prompt "${PROMPT_CONTENT}" \
        "$@"
    if [[ "${REQUIRE_RALPH_DONE}" == "true" ]] && ! latest_ralph_verdict_done "${DAZ_RALPH_ITERATION_LOG}"; then
        echo
        echo "Ralph exited without a final done=true verdict; stopping before validation/install/commit." >&2
        echo "Iteration log: ${DAZ_RALPH_ITERATION_LOG}" >&2
        echo "Resume the thread shown above with daz-ralph -r <thread-id>, or set RALPH_UPDATE_REQUIRE_DONE=false to force the post-Ralph phases." >&2
        exit 1
    fi
fi

if [[ "${SKIP_VALIDATE}" != "true" ]]; then
    run_step "Validating updated stack" bash -lc "${VALIDATE_CMD}"
fi

run_step "Refreshing constraints.txt from active environment" \
    python -m pip freeze --exclude-editable
python -m pip freeze --exclude-editable > "${SCRIPT_DIR}/constraints.txt"

if [[ "${SKIP_COMMIT}" != "true" ]]; then
    run_step "Committing validated update" git add .
    if git diff --cached --quiet; then
        echo "No changes to commit."
    else
        git commit -m "${COMMIT_MESSAGE}"
    fi
fi
