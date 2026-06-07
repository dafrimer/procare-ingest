"""Classify a Procare HTTP failure and report it as an alert via procare-api.

Returns a tuple (exit_code, was_auth_failure) so the runner can decide whether
to short-circuit the rest of the sync (auth failure means every other entity
will fail with 401 too).
"""
import logging
from contextlib import contextmanager

import httpx

from sync.api_client import ApiClient

logger = logging.getLogger(__name__)


class AuthFailure(Exception):
    """Raised when Procare auth is dead and the run should abort."""


def classify_and_report(exc: Exception, api: ApiClient, entity: str) -> bool:
    """Return True if exception is auth-related (caller should abort)."""
    if isinstance(exc, httpx.HTTPStatusError):
        sc = exc.response.status_code
        body_preview = exc.response.text[:300] if exc.response is not None else ""
        if sc in (401, 403):
            api.post_alert(
                severity="critical",
                code="auth_failed",
                entity=entity,
                message=f"Procare returned {sc} for {entity}. Token may be revoked or account locked.",
                details={"status_code": sc, "body": body_preview},
            )
            return True
        if sc == 429:
            api.post_alert(
                severity="warning",
                code="rate_limited",
                entity=entity,
                message=f"Procare rate-limited {entity} (429). Backing off.",
                details={"status_code": sc, "body": body_preview},
            )
            return False
        api.post_alert(
            severity="warning",
            code="http_error",
            entity=entity,
            message=f"Procare HTTP {sc} on {entity}: {body_preview}",
            details={"status_code": sc},
        )
        return False

    if isinstance(exc, httpx.RequestError):
        api.post_alert(
            severity="warning",
            code="network_error",
            entity=entity,
            message=f"Network error syncing {entity}: {exc}",
        )
        return False

    api.post_alert(
        severity="warning",
        code="exception",
        entity=entity,
        message=f"Unhandled exception syncing {entity}: {exc.__class__.__name__}: {exc}",
    )
    return False


@contextmanager
def report_errors(api: ApiClient, entity: str):
    """Context manager: catch + report sync errors. Re-raises AuthFailure to abort run."""
    try:
        yield
    except Exception as e:
        auth = classify_and_report(e, api, entity)
        if auth:
            raise AuthFailure(f"auth failed on {entity}") from e
        logger.warning("Sync of %s failed: %s", entity, e)