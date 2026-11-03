"""Classify failures of the Meta API client so the demo can pick its fallback."""
from openai import APIConnectionError

from src.clients.meta_client import MissingApiKeyError

# Upstream statuses that mean our deployment is broken (revoked key, retired
# model, upstream timeout), not that the student's request is wrong (E5.3).
SERVER_SIDE_UPSTREAM_STATUSES = {401, 403, 404, 408}
CAPACITY_STATUS = 429


def classify_run_error(error: Exception) -> str:
    """Return capacity, infrastructure, request or application for one run failure."""
    status = getattr(error, "status_code", getattr(error, "status", None))
    if isinstance(status, int):
        if status == CAPACITY_STATUS:
            return "capacity"
        if 500 <= status <= 599 or status in SERVER_SIDE_UPSTREAM_STATUSES:
            return "infrastructure"
        if 400 <= status <= 499:
            return "request"
    # APIConnectionError also covers APITimeoutError; OSError is deliberately
    # absent so local file errors (disk full, permissions) are not hidden by the fallback.
    if isinstance(error, (APIConnectionError, ConnectionError, TimeoutError, MissingApiKeyError)):
        return "infrastructure"
    return "application"
