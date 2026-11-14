# ADR-0012: System-trust (truststore) autoloader is opt-in on Linux

## Status

Accepted (retrospective, inferred 2026-11-14)

## Context

ralph_install.sh says that on Linux "auto-injecting truststore via a .pth collides with pip's own vendored truststore and causes RecursionError on HTTPS", and that the autoloader exists for a "macOS corporate-proxy use case".

## Decision

Only when `DEEPAGENTS_SYSTEM_TRUST=1` does install copy `scripts/truststore_bootstrap.py` into site-packages and write `aaa_truststore.pth`; otherwise it removes any existing `aaa_truststore.pth`. The bootstrap injects the OS trust store via `truststore.inject_into_ssl()` and falls back to certifi on failure.

## Consequences

### Positive

- Default DGX installs avoid the RecursionError.

### Negative

- Hosts behind a TLS-intercepting proxy must opt in explicitly.

## Alternatives considered

- Always install the autoloader (the Mac behaviour; rejected for Linux).

## Evidence

- scripts/ralph_install.sh (Configure section)
- scripts/truststore_bootstrap.py
