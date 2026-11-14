# ADR-0016: Offline unit tests for helpers, plus shell/compile/smoke validation gates

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

Most behaviour depends on a downloaded, patched DeepAgents and a live model server, which are not available in a plain checkout.

## Decision

`tests/` holds offline checks only: `test_common_sh.py` sources `common.sh` in a scrubbed environment (model spec, Responses-API flag, unsupported provider exits) and `test_model_param_filter.py` loads the overlay module by path. `pytest.ini` sets `testpaths = tests` and declares an `integration` marker. Upgrade validation is the prompt's gate list: `bash -n` on shell scripts, `python -m py_compile` on scripts, `dcode --version`, `./ralphdgx test vllm|openai`, and `./setup-and-run.sh --vllm --no-run`; install itself asserts versions, overlay imports and `pip check`.

## Consequences

### Positive

- Tests run anywhere without a GPU or model server.

### Negative

- The goal loop, patches and guard middleware have no automated tests in the repo; they are covered only by install-time asserts and smoke runs.
- No CI workflow exists in the repo.

## Alternatives considered

- Live integration tests (marker exists, none present).

## Evidence

- tests/test_common_sh.py
- tests/test_model_param_filter.py
- tests/requirements.txt
- pytest.ini
- docs/upgradeLangGraphDeepAgentsStackSafely.md (step 5)
- scripts/ralph_install.sh (Verify)
