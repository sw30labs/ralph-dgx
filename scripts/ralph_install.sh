#!/usr/bin/env bash
set -euo pipefail

# Install DeepAgents: download sdists, extract, patch, install, verify.
# Called by: ralphdgx install

# This script lives in scripts/, but every path below is repo-root relative,
# so SCRIPT_DIR is the repository root (the parent of scripts/).
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/scripts/lib/common.sh"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
SKIP_INSTALL_PACKAGES="${RALPH_SKIP_INSTALL:-false}"
PROVIDER_EXPLICIT="false"

while (($#)); do
    case "$1" in
        --provider) PROVIDER="$2"; PROVIDER_EXPLICIT="true"; shift 2 ;;
        --skip-install) SKIP_INSTALL_PACKAGES="true"; shift ;;
        --) shift; break ;;
        *) shift ;;
    esac
done

PROVIDER="${PROVIDER:-${DEEPAGENTS_MODEL_PROVIDER:-vllm}}"
if [[ "${PROVIDER_EXPLICIT}" == "true" ]]; then
    export DEEPAGENTS_MODEL_PROVIDER_CLI="${PROVIDER}"
fi
export DEEPAGENTS_MODEL_PROVIDER="${PROVIDER}"

SDIST_DIR="${SCRIPT_DIR}/deepagents-sdists"
REPO_DIR="${SCRIPT_DIR}/deepagents-main"
CONFIG_SCRIPT="${SCRIPT_DIR}/scripts/write_deepagents_config.py"
EXTRACT_SCRIPT="${SCRIPT_DIR}/scripts/extract_sdists.py"
CONSTRAINTS_FILE="${SCRIPT_DIR}/constraints.txt"
PIP_CONSTRAINT_ARGS=()
if [[ -f "${CONSTRAINTS_FILE}" ]]; then
    WEBSOCKETS_CONSTRAINT_FILE="$(mktemp -t ralphdgx_ws_constraint.XXXXXX)"
    trap 'rm -f "${WEBSOCKETS_CONSTRAINT_FILE}"' EXIT
    if grep -E '^[[:space:]]*websockets[[:space:]]*==' "${CONSTRAINTS_FILE}" \
        > "${WEBSOCKETS_CONSTRAINT_FILE}" 2>/dev/null \
        && [[ -s "${WEBSOCKETS_CONSTRAINT_FILE}" ]]; then
        PIP_CONSTRAINT_ARGS=(--constraint "${WEBSOCKETS_CONSTRAINT_FILE}")
    fi
fi
CONFIG_DIR="${HOME}/.deepagents"
CONFIG_PATH="${CONFIG_DIR}/config.toml"

# Isolate installs in the project .venv unless the caller forced PIP_PYTHON_BIN.
if [[ -z "${PIP_PYTHON_BIN:-}" && -z "${RALPHDGX_PYTHON:-}" ]]; then
    ensure_project_venv
else
    resolve_python
fi
PIP_PYTHON_BIN="${PIP_PYTHON_BIN}"
PIP_BIN=("${PIP_PYTHON_BIN}" -m pip)
PYTHON_EXECUTABLE_PATH="$("${PIP_PYTHON_BIN}" -c 'import sys; print(sys.executable)')"
PYTHON_SCRIPTS_PATH="$("${PIP_PYTHON_BIN}" -c 'import sysconfig; print(sysconfig.get_path("scripts"))')"
export PATH="${PYTHON_SCRIPTS_PATH}:${HOME}/.local/bin:${PATH}"

echo "Using Python: ${PYTHON_EXECUTABLE_PATH}"
"${PIP_BIN[@]}" --version

load_project_env
PROVIDER="${DEEPAGENTS_MODEL_PROVIDER:-${PROVIDER}}"
configure_provider_defaults
require_model_provider_env
configure_deepagents_defaults

# ---------------------------------------------------------------------------
# Download & extract
# ---------------------------------------------------------------------------
echo "Downloading DeepAgents source distributions using configured pip index..."
rm -rf "${SDIST_DIR}" "${REPO_DIR}"
mkdir -p "${SDIST_DIR}" "${REPO_DIR}/libs"
"${PIP_BIN[@]}" download --no-binary :all: --no-deps --dest "${SDIST_DIR}" \
    deepagents==0.7.0a7 \
    deepagents-acp==0.0.9 \
    deepagents-code==0.1.43

echo "Extracting source distributions..."
SDIST_DIR="${SDIST_DIR}" REPO_DIR="${REPO_DIR}" "${PIP_PYTHON_BIN}" "${EXTRACT_SCRIPT}"

if [[ ! -d "${REPO_DIR}/libs/code/deepagents_code" ]]; then
    echo "Expected deepagents-code source under ${REPO_DIR}/libs/code/deepagents_code" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Patch
# ---------------------------------------------------------------------------
echo "Applying local Ralph/tenacity patch..."
BASE_DIR="${SCRIPT_DIR}" REPO_DIR="${REPO_DIR}" \
    PYTHONPATH="${SCRIPT_DIR}/scripts${PYTHONPATH:+:${PYTHONPATH}}" \
    "${PIP_PYTHON_BIN}" -m ralph_patch.main

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------
if "${PIP_BIN[@]}" show daz-ralph >/dev/null 2>&1; then
    echo "Removing external daz-ralph package; Ralph is vendored into patched deepagents-code..."
    "${PIP_BIN[@]}" uninstall -y daz-ralph
fi

if [[ "${SKIP_INSTALL_PACKAGES}" != "true" ]]; then
    echo "Installing deepagents packages from local repo using configured pip index..."
    "${PIP_BIN[@]}" install --upgrade --upgrade-strategy eager pip
    "${PIP_BIN[@]}" install --upgrade --upgrade-strategy eager ${PIP_CONSTRAINT_ARGS[@]+"${PIP_CONSTRAINT_ARGS[@]}"} \
        langchain-core \
        openai \
        python-dotenv \
        truststore

    case "${PROVIDER}" in
        vllm|omlx|openai)
            # Local vLLM/omlx and cloud openai are all reached through dcode's
            # `openai` provider / langchain-openai.
            "${PIP_BIN[@]}" install --upgrade --upgrade-strategy eager ${PIP_CONSTRAINT_ARGS[@]+"${PIP_CONSTRAINT_ARGS[@]}"} langchain-openai
            ;;
    esac

    for optional_package in fastapi prometheus-fastapi-instrumentator; do
        if "${PIP_BIN[@]}" show "${optional_package}" >/dev/null 2>&1; then
            "${PIP_BIN[@]}" install --upgrade --upgrade-strategy eager ${PIP_CONSTRAINT_ARGS[@]+"${PIP_CONSTRAINT_ARGS[@]}"} "${optional_package}"
        fi
    done

    "${PIP_BIN[@]}" install --upgrade --upgrade-strategy eager ${PIP_CONSTRAINT_ARGS[@]+"${PIP_CONSTRAINT_ARGS[@]}"} "${REPO_DIR}/libs/deepagents"
    "${PIP_BIN[@]}" install --upgrade --upgrade-strategy eager ${PIP_CONSTRAINT_ARGS[@]+"${PIP_CONSTRAINT_ARGS[@]}"} "${REPO_DIR}/libs/acp" "${REPO_DIR}/libs/code"
fi

# ---------------------------------------------------------------------------
# Configure
# ---------------------------------------------------------------------------
echo "Writing ${CONFIG_PATH} for ${PROVIDER}..."
CONFIG_DIR="${CONFIG_DIR}" CONFIG_PATH="${CONFIG_PATH}" SCRIPT_PATH="$0" "${PIP_PYTHON_BIN}" "${CONFIG_SCRIPT}"

SITE_PACKAGES="$("${PIP_PYTHON_BIN}" -c 'import sysconfig; print(sysconfig.get_path("purelib"))')"
# On Linux (this DGX path), auto-injecting truststore via a .pth collides with
# pip's own vendored truststore and causes RecursionError on HTTPS. Skip the
# autoloader unless the user explicitly opts in (macOS corporate-proxy use case).
if [[ "${DEEPAGENTS_SYSTEM_TRUST:-0}" == "1" ]]; then
    echo "Installing system-trust autoloader into ${SITE_PACKAGES}..."
    mkdir -p "${SITE_PACKAGES}"
    cp "${SCRIPT_DIR}/scripts/truststore_bootstrap.py" "${SITE_PACKAGES}/truststore_bootstrap.py"
    printf 'import truststore_bootstrap\n' > "${SITE_PACKAGES}/aaa_truststore.pth"
else
    echo "Skipping system-trust autoloader (set DEEPAGENTS_SYSTEM_TRUST=1 to enable)."
    rm -f "${SITE_PACKAGES}/aaa_truststore.pth"
fi

chmod 600 "${CONFIG_PATH}"
export DEEPAGENTS_CODE_NO_UPDATE_CHECK=1

# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
echo "Verifying installed CLI..."
"${PIP_PYTHON_BIN}" -m deepagents_code --version

echo "Verifying installed package versions and Ralph overlays..."
"${PIP_PYTHON_BIN}" <<'PY'
from __future__ import annotations

import importlib.metadata as metadata

expected_names = [
    "deepagents",
    "deepagents-acp",
    "deepagents-code",
    "langchain",
    "langchain-core",
    "langchain-openai",
    "langgraph",
    "langgraph-checkpoint",
    "langgraph-sdk",
    "openai",
    "python-dotenv",
    "requests",
    "starlette",
]

for name in expected_names:
    actual = metadata.version(name)
    print(f" {name}=={actual}")

from daz_ralph.main import _configure_ralph_log_env
from deepagents_code.goal import append_iteration_log
from deepagents_code.runtime_install_guard import command_installs_into_ralph_runtime

assert callable(_configure_ralph_log_env)
assert callable(append_iteration_log)
assert command_installs_into_ralph_runtime("python -m pip install -r requirements.txt")
assert not command_installs_into_ralph_runtime(".venv/bin/python -m pip install -r requirements.txt")
print("Ralph overlays ok")
PY

echo "Verifying dependency graph..."
"${PIP_BIN[@]}" check

cat <<EOF
Install complete (ralphdgx / DGX + vLLM path).

Recommended launch from the project directory:
    cd "${SCRIPT_DIR}"
    export DEEPAGENTS_CODE_NO_UPDATE_CHECK=1
    ./ralphdgx run
    # or: dcode --model "$(model_spec)" --no-mcp

Ralph/tenacity launch:
    daz-ralph --model "$(model_spec)" --no-mcp
EOF
