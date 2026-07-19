#!/usr/bin/env bash

DEEPAGENTS_CLI_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
DEEPAGENTS_ENV_FILE="${DEEPAGENTS_ENV_FILE:-${DEEPAGENTS_CLI_ROOT}/.env}"

# Prefer project venv scripts + user-local bins (e.g. ripgrep) over system PATH.
export PATH="${DEEPAGENTS_CLI_ROOT}/.venv/bin:${HOME}/.local/bin:${PATH}"

load_project_env() {
    if [[ ! -f "${DEEPAGENTS_ENV_FILE}" ]]; then
        echo "Missing ${DEEPAGENTS_ENV_FILE}. Copy .env.example to .env and fill in your model provider values." >&2
        exit 1
    fi

    set -a
    # shellcheck disable=SC1090
    source "${DEEPAGENTS_ENV_FILE}"
    set +a

    # An explicit CLI choice (e.g. `ralphdgx run --provider vllm`) must win over
    # the DEEPAGENTS_MODEL_PROVIDER value pinned in .env, which we just re-sourced.
    if [[ -n "${DEEPAGENTS_MODEL_PROVIDER_CLI:-}" ]]; then
        export DEEPAGENTS_MODEL_PROVIDER="${DEEPAGENTS_MODEL_PROVIDER_CLI}"
    fi
}

require_env_vars() {
    local name
    for name in "$@"; do
        if [[ -z "${!name:-}" ]]; then
            echo "Missing ${name} in ${DEEPAGENTS_ENV_FILE}" >&2
            exit 1
        fi
    done
}

# Single source of the unsupported-provider error.
unsupported_provider() {
    echo "Unsupported DEEPAGENTS_MODEL_PROVIDER=${DEEPAGENTS_MODEL_PROVIDER}. Expected vllm or openai." >&2
    exit 1
}

# Canonicalize known providers. This DGX fork only supports local vLLM and
# cloud/OpenAI-compatible endpoints — no Mac OMLX path.
normalize_provider() {
    case "${1:-vllm}" in
        vllm) printf 'vllm\n' ;;
        openai) printf 'openai\n' ;;
        *) printf '%s\n' "${1}" ;;
    esac
}

require_model_provider_env() {
    case "$(normalize_provider "${DEEPAGENTS_MODEL_PROVIDER:-vllm}")" in
        vllm)
            require_env_vars VLLM_MODEL VLLM_BASE_URL
            ;;
        openai)
            require_env_vars OPENAI_MODEL OPENAI_API_KEY
            ;;
        *) unsupported_provider ;;
    esac
}

model_spec() {
    case "$(normalize_provider "${DEEPAGENTS_MODEL_PROVIDER:-vllm}")" in
        vllm)
            # Local vLLM (OpenAI-compatible) reached through dcode's openai provider.
            printf 'openai:%s\n' "${VLLM_MODEL}"
            ;;
        openai)
            printf 'openai:%s\n' "${OPENAI_MODEL}"
            ;;
        *) unsupported_provider ;;
    esac
}

model_params_spec() {
    # Extra --model-params JSON for providers that need it (empty = none).
    # --model-params outranks both the deepagents provider profile and
    # ~/.deepagents/config.toml (profile < config.toml < --model-params).
    case "$(normalize_provider "${DEEPAGENTS_MODEL_PROVIDER:-vllm}")" in
        vllm)
            # deepagents' built-in openai profile may force use_responses_api=True,
            # but vLLM implements chat-completions (/v1/chat/completions), not
            # the Responses API (/v1/responses).
            printf '{"use_responses_api": false}\n'
            ;;
        openai) ;;
        *) unsupported_provider ;;
    esac
}

configure_vllm_defaults() {
    # Local NVIDIA/vLLM OpenAI-compatible server (DGX Spark / GB10 path).
    # Default model matches the coder-next recipe currently served on this box.
    export VLLM_BASE_URL="${VLLM_BASE_URL:-http://127.0.0.1:8000/v1}"
    export VLLM_MODEL="${VLLM_MODEL:-Qwen/Qwen3-Coder-Next-FP8}"
    export VLLM_API_KEY="${VLLM_API_KEY:-test}"
    # Qwen3-Coder-Next-FP8 advertises 131072 max context on this host.
    export VLLM_MAX_INPUT_TOKENS="${VLLM_MAX_INPUT_TOKENS:-131072}"

    # Always pin the OpenAI-compatible client at the local vLLM endpoint.
    # Do not preserve ambient OPENAI_BASE_URL/OPENAI_API_KEY (e.g. cloud xAI
    # leftovers from a previous shell) — those would route the local model id
    # to the wrong host and fail with "Model not found".
    export OPENAI_BASE_URL="${VLLM_BASE_URL}"
    export OPENAI_API_KEY="${VLLM_API_KEY}"

    # Local GPU models can pause between stream chunks longer than langchain's
    # 120s default (big prefills / tool loops). Raise the gap timer; set 0 to
    # disable. Kernel TCP timeout still catches dead peers.
    export LANGCHAIN_OPENAI_STREAM_CHUNK_TIMEOUT_S="${LANGCHAIN_OPENAI_STREAM_CHUNK_TIMEOUT_S:-600}"
}

configure_openai_defaults() {
    # Generic OpenAI provider: real api.openai.com by default, or any
    # OpenAI-compatible endpoint when OPENAI_BASE_URL is set.
    export OPENAI_MODEL="${OPENAI_MODEL:-gpt-5.5}"
    export OPENAI_MAX_INPUT_TOKENS="${OPENAI_MAX_INPUT_TOKENS:-128000}"
    # OPENAI_API_KEY is required (validated by require_model_provider_env).
    # OPENAI_BASE_URL is optional; leave unset to hit the real OpenAI API.
}

configure_deepagents_defaults() {
    export DEEPAGENT_REASONING_EFFORT="${DEEPAGENT_REASONING_EFFORT:-xhigh}"
    export DEEPAGENT_APPROVE_SHELL="${DEEPAGENT_APPROVE_SHELL:-true}"
    export DEEPAGENT_APPROVE_WRITES="${DEEPAGENT_APPROVE_WRITES:-true}"
    export DEEPAGENTS_CODE_LANGSMITH_TRACING="${DEEPAGENTS_CODE_LANGSMITH_TRACING:-false}"
    export DEEPAGENTS_CODE_LANGCHAIN_TRACING_V2="${DEEPAGENTS_CODE_LANGCHAIN_TRACING_V2:-false}"
    export DEEPAGENTS_CODE_DEBUG="${DEEPAGENTS_CODE_DEBUG:-1}"
    export DEEPAGENTS_CODE_DEBUG_FILE="${DEEPAGENTS_CODE_DEBUG_FILE:-/tmp/deepagents_debug.log}"
    export DEEPAGENTS_CODE_NO_UPDATE_CHECK="${DEEPAGENTS_CODE_NO_UPDATE_CHECK:-1}"
    export DAZ_RALPH_LOG_DIR="${DAZ_RALPH_LOG_DIR:-${DEEPAGENTS_CLI_ROOT}/logs/ralph}"
}

configure_patch_pythonpath() {
    export PYTHONPATH="${DEEPAGENTS_CLI_ROOT}/deepagents-main/libs/code:${DEEPAGENTS_CLI_ROOT}/deepagents-main/libs/deepagents${PYTHONPATH:+:${PYTHONPATH}}"
}

require_command() {
    local command_name="$1"
    if ! command -v "${command_name}" >/dev/null 2>&1; then
        echo "${command_name} was not found in PATH." >&2
        exit 1
    fi
}

# Prefer project .venv, then PIP_PYTHON_BIN / RALPHDGX_PYTHON, then python3.12.
# The project venv keeps DeepAgents off the system Python on this DGX.
resolve_python() {
    if [[ -n "${PIP_PYTHON_BIN:-}" ]]; then
        return
    fi
    if [[ -n "${RALPHDGX_PYTHON:-}" ]]; then
        PIP_PYTHON_BIN="${RALPHDGX_PYTHON}"
        return
    fi
    local venv_py="${DEEPAGENTS_CLI_ROOT}/.venv/bin/python"
    if [[ -x "${venv_py}" ]]; then
        PIP_PYTHON_BIN="${venv_py}"
        return
    fi
    local candidate
    for candidate in python3.12 python3; do
        if command -v "${candidate}" >/dev/null 2>&1; then
            # Prefer 3.12 when both exist.
            if [[ "${candidate}" == "python3" ]]; then
                local ver
                ver="$("${candidate}" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
                if [[ "${ver}" != "3.12" ]] && command -v python3.12 >/dev/null 2>&1; then
                    PIP_PYTHON_BIN="python3.12"
                    return
                fi
            fi
            PIP_PYTHON_BIN="${candidate}"
            return
        fi
    done
    echo "No python3 found in PATH. Install Python 3.12." >&2
    exit 1
}

# Create ${DEEPAGENTS_CLI_ROOT}/.venv with Python 3.12 if missing.
ensure_project_venv() {
    local venv_dir="${DEEPAGENTS_CLI_ROOT}/.venv"
    local venv_py="${venv_dir}/bin/python"
    if [[ -x "${venv_py}" ]]; then
        PIP_PYTHON_BIN="${venv_py}"
        export PIP_PYTHON_BIN
        return
    fi
    local bootstrap="python3.12"
    if ! command -v "${bootstrap}" >/dev/null 2>&1; then
        bootstrap="python3"
    fi
    if ! command -v "${bootstrap}" >/dev/null 2>&1; then
        echo "Cannot create .venv: no python3.12/python3 in PATH." >&2
        exit 1
    fi
    echo "Creating project venv at ${venv_dir} with ${bootstrap}..."
    "${bootstrap}" -m venv "${venv_dir}"
    PIP_PYTHON_BIN="${venv_py}"
    export PIP_PYTHON_BIN
    "${PIP_PYTHON_BIN}" -m pip install --upgrade pip
}

# Announce and run a step (shared by setup-and-run.sh and the update workflow).
run_step() {
    local description="$1"
    shift
    echo
    echo "===> ${description}"
    "$@"
}

resolve_dcode_cmd() {
    resolve_python
    DCODE_CMD=("${PIP_PYTHON_BIN}" -m deepagents_code)
    if command -v dcode >/dev/null 2>&1 && dcode --version >/dev/null 2>&1; then
        DCODE_CMD=(dcode)
    fi
}

# ---- Higher-level helpers for the ralphdgx dispatcher ----

resolve_provider() {
    local requested="${1:-}"
    if [[ -n "${requested}" ]]; then
        DEEPAGENTS_MODEL_PROVIDER="${requested}"
    fi
    case "${DEEPAGENTS_MODEL_PROVIDER:-vllm}" in
        vllm|openai) ;;
        *) unsupported_provider ;;
    esac
    export DEEPAGENTS_MODEL_PROVIDER
}

configure_provider_defaults() {
    case "$(normalize_provider "${DEEPAGENTS_MODEL_PROVIDER:-vllm}")" in
        vllm) configure_vllm_defaults ;;
        openai) configure_openai_defaults ;;
        *) unsupported_provider ;;
    esac
}

prepare_run() {
    load_project_env
    configure_provider_defaults
    require_model_provider_env
    configure_deepagents_defaults
    configure_patch_pythonpath
    resolve_dcode_cmd
}

prepare_test() {
    load_project_env
    configure_provider_defaults
    require_model_provider_env
    configure_deepagents_defaults
    configure_patch_pythonpath
}

run_dcode() {
    local extra_args=("$@")
    local cmd_args=("${DCODE_CMD[@]}" --model "$(model_spec)" --no-mcp)
    local model_params
    model_params="$(model_params_spec)"
    if [[ -n "${model_params}" ]]; then
        cmd_args+=(--model-params "${model_params}")
    fi
    # Caller args come last so an explicit --model-params passed through the
    # dispatcher wins (argparse keeps the final occurrence).
    if [[ ${#extra_args[@]} -gt 0 ]]; then
        cmd_args+=("${extra_args[@]}")
    fi
    exec "${cmd_args[@]}"
}
