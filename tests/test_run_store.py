"""Pending-run store for the E5.1 demo server: locked TTL, caps, claim.

No network, no API key: only the in-memory session bookkeeping is exercised.
"""
import threading
import time

from src.api.run_store import (
    MAX_PENDING_RUNS,
    RUN_TTL_SECONDS,
    PendingRunStore,
)


def make_suspended():
    return {"status": "needs_input", "question": "Série ?", "journal": []}


def test_store_and_claim_roundtrip(tmp_path):
    store = PendingRunStore()
    tmpdir = tmp_path / "run-1"
    tmpdir.mkdir()
    assert store.try_store_pending_run("run-1", make_suspended(), tmpdir,
                                       limit=MAX_PENDING_RUNS)
    entry = store.claim_pending_run("run-1")
    assert entry["suspended"]["question"] == "Série ?"
    assert entry["tmpdir"] == tmpdir
    assert store.claim_pending_run("run-1") is None


def test_drop_removes_entry_and_tmpdir(tmp_path):
    store = PendingRunStore()
    tmpdir = tmp_path / "run-2"
    tmpdir.mkdir()
    (tmpdir / "image.jpg").write_bytes(b"x")
    store.store_pending_run("run-2", make_suspended(), tmpdir)
    store.drop_pending_run("run-2")
    assert not store.has_pending_run("run-2")
    assert not tmpdir.exists()


def test_purge_expired_drops_old_and_cleans_tmpdir(tmp_path):
    store = PendingRunStore()
    old_dir = tmp_path / "old"
    old_dir.mkdir()
    fresh_dir = tmp_path / "fresh"
    fresh_dir.mkdir()
    now = time.monotonic()
    store.store_pending_run("old", make_suspended(), old_dir, now=now - RUN_TTL_SECONDS - 1)
    store.store_pending_run("fresh", make_suspended(), fresh_dir, now=now)
    assert store.purge_expired_runs(now=now) == 1
    assert not store.has_pending_run("old")
    assert not old_dir.exists()
    assert store.has_pending_run("fresh")
    assert fresh_dir.is_dir()


def test_restore_refreshes_expiry(tmp_path):
    store = PendingRunStore()
    tmpdir = tmp_path / "run-3"
    tmpdir.mkdir()
    old = time.monotonic() - RUN_TTL_SECONDS - 1
    entry = {"suspended": make_suspended(), "tmpdir": tmpdir, "created_at": old}
    store.restore_pending_run("run-3", entry)
    assert store.purge_expired_runs() == 0
    assert store.has_pending_run("run-3")


def test_pending_cap_is_enforced_atomically(tmp_path):
    store = PendingRunStore()
    tmpdir = tmp_path / "run-4"
    tmpdir.mkdir()
    assert store.try_store_pending_run("only", make_suspended(), tmpdir, limit=1)
    assert not store.try_store_pending_run("extra", make_suspended(), tmpdir, limit=1)
    assert store.pending_count() == 1


def test_claim_has_a_single_winner_under_threads(tmp_path):
    store = PendingRunStore()
    tmpdir = tmp_path / "run-5"
    tmpdir.mkdir()
    store.store_pending_run("race", make_suspended(), tmpdir)
    winners = []
    threads = [threading.Thread(target=lambda: winners.append(store.claim_pending_run("race")))
               for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(entry is not None for entry in winners) == 1


def test_active_slot_cap_and_idempotent_release():
    store = PendingRunStore()
    slot = store.try_acquire_active_run(limit=1)
    assert slot is not None
    assert store.try_acquire_active_run(limit=1) is None
    slot.release()
    slot.release()  # stream end + response background must not double-count
    assert store.active_count() == 0
    assert store.try_acquire_active_run(limit=1) is not None
