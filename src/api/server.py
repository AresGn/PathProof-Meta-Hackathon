"""FastAPI demo server: real agent loop streamed as SSE (E5.1, issue #30).

Orchestration only: validate uploads, save them under a repo-relative
tmp dir (so journals never carry a personal absolute path), run
`src/agent/loop.py` in a worker thread while the response streams its
journal as `{step, tool, args, result, decision}` events live. No average,
no filtering, no proof check lives here.
"""
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.agent import loop
from src.agent.tool_schemas import TOOL_SCHEMAS
from src.api.run_store import MAX_PENDING_RUNS, PendingRunStore, cleanup_tmpdir
from src.cli_run import path_for_agent, verified_report_from_journal
from src.clients.meta_client import get_client
from src.clients.muse_spark import MUSE_SPARK_MODEL

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"
# Fictional demo files the judges can launch in one click (E5.2, data/samples/README.md).
SAMPLE_MEDIA_TYPES = {
    "releve_serie_d.jpg": "image/jpeg",
    "releve_serie_c.jpg": "image/jpeg",
    "releve_serie_d_flou.jpg": "image/jpeg",
    "note_vocale_coherente.mp3": "audio/mpeg",
    "note_vocale_contradictoire.mp3": "audio/mpeg",
}

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # demo upload cap for grade-sheet photos (E5.1)
MAX_AUDIO_BYTES = 32 * 1024 * 1024  # docs/decisions.md E0.5: transcribe endpoint body limit
READ_CHUNK_BYTES = 1024 * 1024  # E5.1 review: enforce caps while reading so one upload stays bounded
POLL_INTERVAL_SECONDS = 0.01  # E5.1 review: live SSE polling between the worker thread and the response
SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}  # src/clients/vision.py MEDIA_TYPES
SUPPORTED_AUDIO_SUFFIXES = {".flac", ".m4a", ".mp3", ".ogg", ".opus", ".wav", ".webm"}  # src/tools/transcribe_voice.py SUPPORTED_AUDIO_TYPES
MAX_CONCURRENT_RUNS = 5  # E5.1 review (2nd pass): bound simultaneous paid API runs on the public demo

pending_run_store = PendingRunStore()  # locked sessions + active-run slots (src/api/run_store.py)


class AnswerRequest(BaseModel):
    """Student answer resuming a run suspended by ask_student."""

    run_id: str
    answer: str


def sanitize_text_value(value: str) -> str:
    """Strip the API key value from one string (before JSON encoding)."""
    secret = os.environ.get("MUSE_API_KEY", "")
    if secret and secret in value:
        value = value.replace(secret, "[redacted]")
    return value


def sanitize_payload_value(payload: object) -> object:
    """Strip the API key value from every string of a payload, before dumps."""
    if isinstance(payload, str):
        return sanitize_text_value(payload)
    if isinstance(payload, list):
        return [sanitize_payload_value(item) for item in payload]
    if isinstance(payload, dict):
        return {key: sanitize_payload_value(item) for key, item in payload.items()}
    return payload


def describe_run_error(error: Exception) -> str:
    """Error text safe for SSE: key redacted, env name never echoed."""
    message = sanitize_text_value(str(error) or "agent run failed")
    if "MUSE_API_KEY" in message:
        return "API key is not set (server misconfiguration)"
    return message


def format_sse_frame(payload: dict) -> str:
    """Format one SSE data frame from an already sanitized payload."""
    return f"data: {json.dumps(sanitize_payload_value(payload), ensure_ascii=False)}\n\n"


def suffix_of(filename: str | None) -> str:
    return Path(filename or "").suffix.lower()


def check_upload_suffix(suffix: str, allowed: set[str], label: str) -> None:
    if suffix not in allowed:
        raise HTTPException(status_code=415, detail=f"unsupported {label} type: {suffix or '(none)'}")


async def read_limited_upload(upload: UploadFile, limit: int, label: str) -> bytes:
    """Read an upload in chunks; 413 as soon as the cap is exceeded, 400 when empty."""
    declared = getattr(upload, "size", None)
    if isinstance(declared, int) and declared > limit:
        raise HTTPException(status_code=413, detail=f"{label} too large (over {limit} bytes)")
    if isinstance(declared, int) and declared == 0:
        raise HTTPException(status_code=400, detail=f"empty {label} file")
    data = bytearray()
    while True:
        chunk = await upload.read(READ_CHUNK_BYTES)
        if not chunk:
            break
        data += chunk
        if len(data) > limit:
            raise HTTPException(status_code=413, detail=f"{label} too large (over {limit} bytes)")
    if not data:
        raise HTTPException(status_code=400, detail=f"empty {label} file")
    return bytes(data)


def new_run_tmpdir(run_id: str) -> Path:
    tmpdir = Path.cwd() / "tmp" / f"pathproof-{run_id}"
    tmpdir.mkdir(parents=True, exist_ok=True)
    return tmpdir


def build_user_message(image_path: Path | None, audio_path: Path | None,
                       text: str | None) -> str:
    """Describe the student inputs for the model; paths stay repo-relative."""
    if image_path is not None and audio_path is not None:
        first = "The student submitted a grade-sheet photo and a voice note (fictional sample)."
    elif image_path is not None:
        first = "The student submitted a grade-sheet photo (fictional sample)."
    elif audio_path is not None:
        first = "The student submitted a voice note (fictional sample)."
    else:
        first = "The student submitted a written fallback text (fictional sample)."
    lines = [first]
    if image_path is not None:
        lines.append("Grade sheet image path (pass verbatim to read_grade_sheet): "
                     f"{path_for_agent(image_path)}")
    if audio_path is not None:
        lines.append("Voice note audio path (pass verbatim to transcribe_voice): "
                     f"{path_for_agent(audio_path)}")
    if text is not None and text.strip():
        lines.append("Student fallback text (use as transcript, skip transcribe_voice "
                     f"when there is no audio): {text.strip()}")
    lines.append("Run the full tool loop and produce a verified orientation report via "
                 "verify_report then build_report.")
    return "\n".join(lines)


def build_step_frame(event: dict) -> dict:
    return {"type": "step", "step": event.get("step"), "tool": event.get("tool"),
            "args": event.get("args"), "result": event.get("result"),
            "decision": event.get("decision")}


def build_done_payload(run_id: str, outcome: str | dict, journal: list) -> dict:
    """Final SSE payload for a finished (non-suspended) run."""
    base: dict = {"type": "done", "run_id": run_id}
    if isinstance(outcome, dict) and outcome.get("status") == "unverified":
        return {**base, "status": "unverified",
                "problems": outcome.get("problems", []),
                "steps_used": outcome.get("steps_used", len(journal))}
    if outcome == loop.STOPPED_STEP_LIMIT:
        return {**base, "status": "step_limit", "report": None}
    report = verified_report_from_journal(journal)
    if report:
        return {**base, "status": "ok", "report": report}
    if isinstance(outcome, str) and outcome.strip():
        return {**base, "status": "no_verified_report", "report": None,
                "model_text": outcome[:2000]}
    return {**base, "status": "no_verified_report", "report": None}


def run_worker_call(call: Callable[[], str | dict], box: dict) -> None:
    """Run the agent loop; the polling thread only reads box and the journal."""
    try:
        box["outcome"] = call()
    except Exception as error:  # worker failure becomes an error frame, never a 500
        box["error"] = error
    finally:
        box["done"] = True


def settle_agent_run(*, run_id: str, journal: list, tmpdir: Path | None,
                     restore_entry: dict | None, box: dict,
                     pending_limit: int = MAX_PENDING_RUNS,
                     rollback_state: dict | None = None) -> dict:
    """Bookkeep one finished worker (store, forget or restore) and return its terminal frame."""
    error = box.get("error")
    if error is not None:
        if rollback_state is not None:
            # Undo the failed attempt only now: its steps were streamed (and
            # announced by a rollback frame), so truncating earlier would race.
            suspended = rollback_state["suspended"]
            if isinstance(suspended.get("messages"), list):
                del suspended["messages"][rollback_state["message_count"]:]
            del journal[rollback_state["journal_count"]:]
        if restore_entry is not None:
            pending_run_store.restore_pending_run(run_id, restore_entry)
        else:
            cleanup_tmpdir(tmpdir)
        return {"type": "error", "run_id": run_id, "error": describe_run_error(error)}
    outcome = box.get("outcome")
    if isinstance(outcome, dict) and outcome.get("status") == "needs_input":
        if not pending_run_store.try_store_pending_run(
                run_id, outcome, tmpdir, limit=pending_limit):
            cleanup_tmpdir(tmpdir)
            return {"type": "error", "run_id": run_id,
                    "error": "too many pending runs, retry later"}
        return {"type": "needs_input", "run_id": run_id,
                "question": outcome.get("question"),
                "step": outcome.get("steps_used")}
    pending_run_store.drop_pending_run(run_id)
    cleanup_tmpdir(tmpdir)
    return build_done_payload(run_id, outcome, journal)


def settle_agent_run_safely(*, run_id: str, journal: list, tmpdir: Path | None,
                            restore_entry: dict | None, box: dict,
                            pending_limit: int = MAX_PENDING_RUNS,
                            rollback_state: dict | None = None) -> dict:
    """Settle without raising: a bookkeeping failure still frees or restores the run."""
    try:
        return settle_agent_run(run_id=run_id, journal=journal, tmpdir=tmpdir,
                                restore_entry=restore_entry, box=box,
                                pending_limit=pending_limit,
                                rollback_state=rollback_state)
    except Exception as error:  # last-resort bookkeeping, still no 500
        try:
            if restore_entry is not None:
                pending_run_store.restore_pending_run(run_id, restore_entry)
            else:
                cleanup_tmpdir(tmpdir)
        except Exception:
            pass
        return {"type": "error", "run_id": run_id, "error": describe_run_error(error)}


SETTLE_DRAIN_TIMEOUT_SECONDS = 2.0  # E5.1 review (3rd pass): grace for a live consumer to drain before the background settle


class AgentRunHandle:
    """One agent run: eager worker, background finisher, single idempotent settle.

    The worker and finisher start at creation, not at first iteration, so a
    client that disconnects before the stream starts still gets settled
    (tmpdir cleaned or session stored, slot released) once the loop ends.
    The slot is released only inside settle, i.e. after the worker finished:
    a disconnect never frees capacity while the paid API is still running.
    settle_once is the unique settlement point (concurrent calls share it).
    """

    def __init__(self, *, run_id: str, journal: list, start: int, tmpdir: Path | None,
                 restore_entry: dict | None, call: Callable[[], str | dict],
                 pending_limit: int = MAX_PENDING_RUNS, run_slot=None,
                 rollback_state: dict | None = None):
        self.run_id = run_id
        self.journal = journal
        self.start = start
        self.tmpdir = tmpdir
        self.restore_entry = restore_entry
        self.pending_limit = pending_limit
        self.run_slot = run_slot
        self.rollback_state = rollback_state
        self.box: dict = {}
        self._settle_lock = threading.Lock()
        self._settled = False
        self._terminal: dict | None = None
        self._consumer_finished = threading.Event()
        self.worker = threading.Thread(target=run_worker_call, args=(call, self.box),
                                       daemon=True)
        self.worker.start()
        self._finisher = threading.Thread(target=self._finish_in_background, daemon=True)
        self._finisher.start()

    def _finish_in_background(self) -> None:
        self.worker.join()
        # A live consumer drains and settles first; a gone one signals via
        # frames() finally, an absent one falls back to this timeout.
        self._consumer_finished.wait(timeout=SETTLE_DRAIN_TIMEOUT_SECONDS)
        self.settle_once()

    def settle_once(self) -> dict:
        """Settle exactly once and release the slot (worker already finished)."""
        with self._settle_lock:
            if self._settled:
                return self._terminal
            self._settled = True
            try:
                self._terminal = settle_agent_run_safely(
                    run_id=self.run_id, journal=self.journal, tmpdir=self.tmpdir,
                    restore_entry=self.restore_entry, box=self.box,
                    pending_limit=self.pending_limit,
                    rollback_state=self.rollback_state)
            finally:
                if self.run_slot is not None:
                    self.run_slot.release()
            return self._terminal

    def frames(self):
        """Yield step frames live, then rollback (answer only), then terminal."""
        position = self.start
        try:
            while True:
                while position < len(self.journal):
                    try:
                        event = self.journal[position]
                    except IndexError:  # background settle truncated a failed attempt
                        break
                    yield format_sse_frame(build_step_frame(event))
                    position += 1
                if self.box.get("done"):
                    break
                time.sleep(POLL_INTERVAL_SECONDS)
            self.worker.join()
            while position < len(self.journal):
                yield format_sse_frame(build_step_frame(self.journal[position]))
                position += 1
            terminal = self.settle_once()
            if (self.box.get("error") is not None and self.rollback_state is not None
                    and position > self.start):
                yield format_sse_frame({"type": "rollback", "run_id": self.run_id,
                                        "steps": position - self.start})
            yield format_sse_frame(terminal)
        finally:
            # Consumer gone or done: the finisher may settle (idempotent).
            self._consumer_finished.set()


def stream_agent_run(*, run_id: str, journal: list, start: int, tmpdir: Path | None,
                     restore_entry: dict | None, call: Callable[[], str | dict],
                     pending_limit: int = MAX_PENDING_RUNS, run_slot=None,
                     rollback_state: dict | None = None):
    """Start a run eagerly and return its SSE frames iterator."""
    handle = AgentRunHandle(run_id=run_id, journal=journal, start=start, tmpdir=tmpdir,
                            restore_entry=restore_entry, call=call,
                            pending_limit=pending_limit, run_slot=run_slot,
                            rollback_state=rollback_state)
    return handle.frames()


app = FastAPI(title="PathProof Demo API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/samples/{name}")
async def get_sample(name: str) -> FileResponse:
    """Serve one fictional demo file by its allowlisted name (E5.2)."""
    media_type = SAMPLE_MEDIA_TYPES.get(name)
    path = SAMPLES_DIR / name
    if media_type is None or not path.is_file():
        raise HTTPException(status_code=404, detail="unknown sample")
    return FileResponse(path, media_type=media_type, filename=name)


@app.post("/run")
async def run_agent(
    image: UploadFile | None = File(default=None),
    photo: UploadFile | None = File(default=None),
    audio: UploadFile | None = File(default=None),
    voice: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
) -> StreamingResponse:
    """Accept image + optional audio + fallback text, stream the loop as SSE."""
    pending_run_store.purge_expired_runs()
    if pending_run_store.pending_count() >= MAX_PENDING_RUNS:
        raise HTTPException(status_code=429, detail="too many pending runs, retry later")
    run_slot = pending_run_store.try_acquire_active_run(MAX_CONCURRENT_RUNS)
    if run_slot is None:
        raise HTTPException(status_code=429, detail="too many runs in progress, retry later")
    tmpdir: Path | None = None
    try:
        image_file = image or photo
        audio_file = audio or voice
        if image_file is None and (text is None or not text.strip()):
            raise HTTPException(status_code=400, detail="provide an image or a text fallback")

        image_bytes: bytes | None = None
        image_suffix = ""
        if image_file is not None:
            image_suffix = suffix_of(image_file.filename)
            check_upload_suffix(image_suffix, SUPPORTED_IMAGE_SUFFIXES, "image")
            image_bytes = await read_limited_upload(image_file, MAX_IMAGE_BYTES, "image")

        audio_bytes: bytes | None = None
        audio_suffix = ""
        if audio_file is not None:
            audio_suffix = suffix_of(audio_file.filename)
            check_upload_suffix(audio_suffix, SUPPORTED_AUDIO_SUFFIXES, "audio")
            audio_bytes = await read_limited_upload(audio_file, MAX_AUDIO_BYTES, "audio")

        run_id = uuid.uuid4().hex
        tmpdir = new_run_tmpdir(run_id)
        image_path = tmpdir / f"image{image_suffix}" if image_bytes is not None else None
        if image_path is not None and image_bytes is not None:
            image_path.write_bytes(image_bytes)
        audio_path = tmpdir / f"audio{audio_suffix}" if audio_bytes is not None else None
        if audio_path is not None and audio_bytes is not None:
            audio_path.write_bytes(audio_bytes)
        user_input = build_user_message(image_path, audio_path, text)

        journal: list = []

        def call() -> str | dict:
            client = get_client()
            return loop.run(client, MUSE_SPARK_MODEL, TOOL_SCHEMAS, user_input, journal=journal)

        return StreamingResponse(
            stream_agent_run(run_id=run_id, journal=journal, start=0, tmpdir=tmpdir,
                             restore_entry=None, call=call,
                             pending_limit=MAX_PENDING_RUNS, run_slot=run_slot),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    except BaseException:
        cleanup_tmpdir(tmpdir)
        run_slot.release()
        raise


@app.post("/answer")
async def answer_agent(payload: AnswerRequest) -> StreamingResponse:
    """Resume a run suspended by ask_student, streaming the follow-up steps."""
    if not isinstance(payload.answer, str) or not payload.answer.strip():
        raise HTTPException(status_code=400, detail="answer must be a non-empty text")
    pending_run_store.purge_expired_runs()
    entry = pending_run_store.claim_pending_run(payload.run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="unknown run_id")
    run_slot = pending_run_store.try_acquire_active_run(MAX_CONCURRENT_RUNS)
    if run_slot is None:
        pending_run_store.restore_pending_run(payload.run_id, entry)
        raise HTTPException(status_code=429, detail="too many runs in progress, retry later")
    try:
        suspended = entry["suspended"]
        tmpdir = entry.get("tmpdir")
        journal = suspended.get("journal") or []
        start = len(journal)
        answer = payload.answer.strip()
        messages = suspended.get("messages")
        rollback_state = {
            "suspended": suspended,
            "message_count": len(messages) if isinstance(messages, list) else 0,
            "journal_count": start,
        }

        def call() -> str | dict:
            client = get_client()
            return loop.resume(client, MUSE_SPARK_MODEL, TOOL_SCHEMAS, suspended, answer)

        return StreamingResponse(
            stream_agent_run(run_id=payload.run_id, journal=journal, start=start,
                             tmpdir=tmpdir, restore_entry=entry, call=call,
                             pending_limit=MAX_PENDING_RUNS, run_slot=run_slot,
                             rollback_state=rollback_state),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    except BaseException:
        pending_run_store.restore_pending_run(payload.run_id, entry)
        run_slot.release()
        raise


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
