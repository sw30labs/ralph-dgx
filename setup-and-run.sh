#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/scripts/lib/common.sh"

MODEL_PROVIDER="${DEEPAGENTS_MODEL_PROVIDER:-vllm}"
SKIP_INSTALL="${RALPH_SKIP_INSTALL:-false}"
SKIP_RUN="${RALPH_SKIP_RUN:-false}"
ARGS=()

usage() {
    cat <<EOF
Usage: $(basename "$0") [--vllm] [--openai] [--no-run] [--skip-install] [--] [dcode args...]

Installs DeepAgents into the active Python (prefers python3.12), smoke-tests
the chosen provider, and optionally launches ./ralphdgx run.

Environment:
  DEEPAGENTS_MODEL_PROVIDER   vllm or openai (default: vllm)
  RALPH_SKIP_INSTALL          true to skip installing patched packages
  RALPH_SKIP_RUN              true to skip launching the runner
  PIP_PYTHON_BIN / RALPHDGX_PYTHON
                              Python used for install/run
EOF
}

while (($#)); do
    case "$1" in
        --vllm)
            MODEL_PROVIDER="vllm"
            shift
            ;;
        --openai)
            MODEL_PROVIDER="openai"
            shift
            ;;
        --no-run)
            SKIP_RUN="true"
            shift
            ;;
        --skip-install)
            SKIP_INSTALL="true"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            ARGS+=("$@")
            break
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

cd "${SCRIPT_DIR}"
export DEEPAGENTS_MODEL_PROVIDER="${MODEL_PROVIDER}"
export DEEPAGENTS_MODEL_PROVIDER_CLI="${MODEL_PROVIDER}"

# Prefer a project-local .venv so we never write into system Python.
if [[ -z "${PIP_PYTHON_BIN:-}" && -z "${RALPHDGX_PYTHON:-}" ]]; then
    ensure_project_venv
else
    resolve_python
fi
export PIP_PYTHON_BIN

run_step "Making helper scripts executable" chmod +x ./ralphdgx ./scripts/ralph_install.sh

if [[ ! -f .env ]]; then
    run_step "Creating .env from .env.example" cp .env.example .env
fi

if [[ "${SKIP_INSTALL}" != "true" ]]; then
    run_step "Installing patched DeepAgents (ralphdgx)" \
        env PIP_PYTHON_BIN="${PIP_PYTHON_BIN}" ./ralphdgx install --provider "${MODEL_PROVIDER}"
fi

run_step "Smoke-test provider ${MODEL_PROVIDER}" \
    env PIP_PYTHON_BIN="${PIP_PYTHON_BIN}" ./ralphdgx test "${MODEL_PROVIDER}"

if [[ "${SKIP_RUN}" == "true" ]]; then
    echo "Setup and tests completed. Skipping launch (--no-run / RALPH_SKIP_RUN=true)."
    exit 0
fi

run_step "Launching ralphdgx run --provider ${MODEL_PROVIDER}" \
    env PIP_PYTHON_BIN="${PIP_PYTHON_BIN}" ./ralphdgx run --provider "${MODEL_PROVIDER}" ${ARGS[@]+"${ARGS[@]}"}
