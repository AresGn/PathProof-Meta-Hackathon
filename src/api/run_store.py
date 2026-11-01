"""Pending runs suspended by ask_student for the E5.1 demo server.

Single-process demo scope: sessions live in this dict, so a restart or a
second worker loses them (noted in docs/architecture.md; a shared store is
E5.4 scope). Entries expire after RUN_TTL_SECONDS so an unanswered student's
photo and voice note never stay on disk; MAX_PENDING_RUNS bounds memory and
disk. Claim-before-stream (pop on /answer) keeps two concurrent answers for
the same run_id from mutating the same messages and tmpdir.
"""
import shutil
import time
from pathlib import Path

RUN_TTL_SECONDS = 30 * 60  # E5.1 review: personal uploads must not linger when the student never answers
MAX_PENDING_RUNS = 100  # E5.1 review: bound simultaneous suspended runs (429 beyond)

RUNS: dict[str, dict] = {}  # run_id -> {"suspended", "tmpdir", "created_at"} (monotonic clock)


def cleanup_tmpdir(tmpdir: Path | None) -> None:
    """Remove one run directory; never raise (called on error paths too)."""
    if tmpdir is None:
        return
    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except OSError:
        pass


def purge_expired_runs(now: float | None = None) -> int:
    """Drop expired pending runs with their tmpdirs; return how many were dropped."""
    now = time.monotonic() if now is None else now
    expired = [run_id for run_id, entry in RUNS.items()
               if now - entry.get("created_at", now) > RUN_TTL_SECONDS]
    for run_id in expired:
        drop_pending_run(run_id)
    return len(expired)


def store_pending_run(run_id: str, suspended: dict, tmpdir: Path | None,
                      now: float | None = None) -> None:
    """Keep a suspended run (and refresh its expiry so a retry gets a full TTL)."""
    RUNS[run_id] = {"suspended": suspended, "tmpdir": tmpdir,
                    "created_at": time.monotonic() if now is None else now}


def claim_pending_run(run_id: str) -> dict | None:
    """Atomically pop a pending run; the winner streams it, losers get a 404."""
    return RUNS.pop(run_id, None)


def restore_pending_run(run_id: str, entry: dict, now: float | None = None) -> None:
    """Put back a claimed run after a failed resume so the student can retry."""
    store_pending_run(run_id, entry["suspended"], entry.get("tmpdir"), now=now)


def drop_pending_run(run_id: str) -> None:
    """Forget a pending run and remove its uploads."""
    entry = RUNS.pop(run_id, None)
    if entry is not None:
        cleanup_tmpdir(entry.get("tmpdir"))
