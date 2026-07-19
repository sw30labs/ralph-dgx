"""Route Python TLS through the OS trust store when available."""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger("truststore_bootstrap")

_INSTALLED = False
_DISABLE_VALUES = {"0", "false", "off", "no"}


def _enabled() -> bool:
    return os.getenv("DEEPAGENTS_SYSTEM_TRUST", "1").strip().lower() not in _DISABLE_VALUES


def install_system_trust() -> bool:
    """Inject the OS trust store into Python ssl. Idempotent."""

    global _INSTALLED
    if _INSTALLED:
        return True
    if not _enabled():
        return False
    if sys.version_info < (3, 10):
        logger.warning("System trust injection requires Python >= 3.10.")
        return False

    try:
        import truststore

        truststore.inject_into_ssl()
    except Exception:
        logger.warning(
            "System trust injection unavailable; falling back to certifi.",
            exc_info=True,
        )
        return False

    _INSTALLED = True
    logger.info("System trust store injected into ssl.")
    return True


try:
    install_system_trust()
except Exception:
    logger.warning("Deferred system-trust install failed at import.", exc_info=True)
