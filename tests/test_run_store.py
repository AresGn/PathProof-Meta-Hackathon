"""Pending-run store for the E5.1 demo server: TTL, cap, claim/restore.

No network, no API key: only the in-memory session bookkeeping is exercised.
"""
import time

from src.api import run_store
from src.api.run_store import (
    MAX_PENDING_RUNS,
    RUN_TTL_SECONDS,
    claim_pending_run,
    drop_pending_run,
    purge_expired_runs,
    restore_pending_run,
    store_pending_run,
)


def suspended():
    return {"status": "needs_input", "question": "Série ?", "journal": []}


def test_store_and_claim_roundtrip(tmp_path):
    run_store.RUNS.clear()
    tmpdir = tmp_path / "run-1"
    tmpdir.mkdir()
    store_pending_run("run-1", suspended(), tmpdir)
    entry = claim_pending_run("run-1")
    assert entry["suspended"]["question"] == "Série ?"
    assert entry["tmpdir"] == tmpdir
    assert claim_pending_run("run-1") is None


def test_drop_removes_entry_and_tmpdir(tmp_path):
    run_store.RUNS.clear()
    tmpdir = tmp_path / "run-2"
    tmpdir.mkdir()
    (tmpdir / "image.jpg").write_bytes(b"x")
    store_pending_run("run-2", suspended(), tmpdir)
    drop_pending_run("run-2")
    assert "run-2" not in run_store.RUNS
    assert not tmpdir.exists()


def test_purge_expired_drops_old_and_cleans_tmpdir(tmp_path):
    run_store.RUNS.clear()
    old_dir = tmp_path / "old"
    old_dir.mkdir()
    fresh_dir = tmp_path / "fresh"
    fresh_dir.mkdir()
    now = time.monotonic()
    store_pending_run("old", suspended(), old_dir, now=now - RUN_TTL_SECONDS - 1)
    store_pending_run("fresh", suspended(), fresh_dir, now=now)
    assert purge_expired_runs(now=now) == 1
    assert "old" not in run_store.RUNS
    assert not old_dir.exists()
    assert "fresh" in run_store.RUNS
    assert fresh_dir.is_dir()


def test_restore_refreshes_expiry(tmp_path):
    run_store.RUNS.clear()
    tmpdir = tmp_path / "run-3"
    tmpdir.mkdir()
    old = time.monotonic() - RUN_TTL_SECONDS - 1
    entry = {"suspended": suspended(), "tmpdir": tmpdir, "created_at": old}
    restore_pending_run("run-3", entry)
    assert purge_expired_runs() == 0
    assert "run-3" in run_store.RUNS


def test_pending_cap_counts_stored_runs(tmp_path):
    run_store.RUNS.clear()
    assert len(run_store.RUNS) < MAX_PENDING_RUNS
