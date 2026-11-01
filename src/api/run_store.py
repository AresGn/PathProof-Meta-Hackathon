"""Pending runs suspended by ask_student for the E5.1 demo server.

Single-process demo scope: sessions live in this store, so a restart or a
second worker loses them (noted in docs/architecture.md; a shared store is
E5.4 scope). Every access goes through one lock: no module-level mutable
dict, no purge iterating while another thread mutates, and the pending cap
is checked and stored atomically. Entries expire after RUN_TTL_SECONDS so
an unanswered student's photo and voice note never stay on disk.
Claim-before-stream (pop on /answer) keeps two concurrent answers for the
same run_id from mutating the same messages and tmpdir.
"""
import shutil
import threading
import time
from pathlib import Path

RUN_TTL_SECONDS = 30 * 60  # E5.1 review: personal uploads must not linger when the student never answers
MAX_PENDING_RUNS = 100  # E5.1 review: bound simultaneous suspended runs (429 beyond)


def cleanup_tmpdir(tmpdir: Path | None) -> None:
    """Remove one run directory; never raise (called on error paths too)."""
    if tmpdir is None:
        return
    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except OSError:
        pass


class ActiveRunSlot:
    """One in-progress run allowance; release is idempotent (single settle point)."""

    def __init__(self, store: "PendingRunStore"):
        self._store = store
        self._released = False

    def release(self) -> None:
        with self._store._lock:
            if self._released:
                return
            self._released = True
            self._store._active_count = max(0, self._store._active_count - 1)


class PendingRunStore:
    """Locked in-memory store of suspended runs plus the in-progress counter."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: dict[str, dict] = {}
        self._active_count = 0

    def pending_count(self) -> int:
        with self._lock:
            return len(self._runs)

    def active_count(self) -> int:
        with self._lock:
            return self._active_count

    def has_pending_run(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._runs

    def get_pending_entry(self, run_id: str) -> dict | None:
        with self._lock:
            entry = self._runs.get(run_id)
            return dict(entry) if entry is not None else None

    def clear_pending_runs(self) -> None:
        """Forget every pending run and remove its uploads (tests, shutdown)."""
        with self._lock:
            entries = list(self._runs.values())
            self._runs.clear()
        for entry in entries:
            cleanup_tmpdir(entry.get("tmpdir"))

    def _expired_entries_locked(self, now: float) -> list[dict]:
        expired_ids = [run_id for run_id, entry in self._runs.items()
                       if now - entry.get("created_at", now) > RUN_TTL_SECONDS]
        return [self._runs.pop(run_id) for run_id in expired_ids]

    def purge_expired_runs(self, now: float | None = None) -> int:
        """Drop expired pending runs with their tmpdirs; return how many were dropped."""
        now = time.monotonic() if now is None else now
        with self._lock:
            expired = self._expired_entries_locked(now)
        for entry in expired:
            cleanup_tmpdir(entry.get("tmpdir"))
        return len(expired)

    def try_store_pending_run(self, run_id: str, suspended: dict, tmpdir: Path | None,
                              limit: int, now: float | None = None) -> bool:
        """Store a suspended run if the cap allows it (checked under the same lock)."""
        now = time.monotonic() if now is None else now
        with self._lock:
            expired = self._expired_entries_locked(now)
            stored = run_id in self._runs or len(self._runs) < limit
            if stored:
                self._runs[run_id] = {"suspended": suspended, "tmpdir": tmpdir,
                                      "created_at": now}
        for entry in expired:
            cleanup_tmpdir(entry.get("tmpdir"))
        return stored

    def store_pending_run(self, run_id: str, suspended: dict, tmpdir: Path | None,
                          now: float | None = None) -> None:
        """Keep a suspended run unconditionally (restore path: it was already counted)."""
        with self._lock:
            self._runs[run_id] = {"suspended": suspended, "tmpdir": tmpdir,
                                  "created_at": time.monotonic() if now is None else now}

    def claim_pending_run(self, run_id: str) -> dict | None:
        """Atomically pop a pending run; the winner streams it, losers get a 404."""
        with self._lock:
            return self._runs.pop(run_id, None)

    def restore_pending_run(self, run_id: str, entry: dict,
                            now: float | None = None) -> None:
        """Put back a claimed run after a failed resume so the student can retry."""
        self.store_pending_run(run_id, entry["suspended"], entry.get("tmpdir"), now=now)

    def drop_pending_run(self, run_id: str) -> None:
        """Forget a pending run and remove its uploads."""
        with self._lock:
            entry = self._runs.pop(run_id, None)
        if entry is not None:
            cleanup_tmpdir(entry.get("tmpdir"))

    def try_acquire_active_run(self, limit: int) -> ActiveRunSlot | None:
        """Reserve one in-progress slot under the lock; None when the cap is reached."""
        with self._lock:
            if self._active_count >= limit:
                return None
            self._active_count += 1
            return ActiveRunSlot(self)
