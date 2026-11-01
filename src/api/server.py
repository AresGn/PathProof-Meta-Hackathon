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
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.agent import loop
from src.agent.tool_schemas import TOOL_SCHEMAS
from src.api.run_store import (
    MAX_PENDING_RUNS,
    RUNS,
    claim_pending_run,
    cleanup_tmpdir,
    drop_pending_run,
    purge_expired_runs,
    restore_pending_run,
    store_pending_run,
)
from src.cli_run import path_for_agent, verified_report_from_journal
from src.clients.meta_client import get_client
from src.clients.muse_spark import MUSE_SPARK_MODEL

WEB_DIR = Path(__file__).resolve().parents[2] / "web"

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # demo upload cap for grade-sheet photos (E5.1)
MAX_AUDIO_BYTES = 32 * 1024 * 1024  # docs/decisions.md E0.5: transcribe endpoint body limit
READ_CHUNK_BYTES = 1024 * 1024  # E5.1 review: enforce caps while reading so one upload stays bounded
POLL_INTERVAL_SECONDS = 0.01  # E5.1 review: live SSE polling between the worker thread and the response
SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}  # src/clients/vision.py MEDIA_TYPES
SUPPORTED_AUDIO_SUFFIXES = {".flac", ".m4a", ".mp3", ".ogg", ".opus", ".wav", ".webm"}  # src/tools/transcribe_voice.py SUPPORTED_AUDIO_TYPES


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
                     restore_entry: dict | None, box: dict) -> dict:
    """Bookkeep one finished worker (store, forget or restore) and return its terminal frame."""
    error = box.get("error")
    if error is not None:
        if restore_entry is not None:
            restore_pending_run(run_id, restore_entry)
        else:
            cleanup_tmpdir(tmpdir)
        return {"type": "error", "error": describe_run_error(error)}
    outcome = box.get("outcome")
    if isinstance(outcome, dict) and outcome.get("status") == "needs_input":
        store_pending_run(run_id, outcome, tmpdir)
        return {"type": "needs_input", "run_id": run_id,
                "question": outcome.get("question"),
                "step": outcome.get("steps_used")}
    drop_pending_run(run_id)
    cleanup_tmpdir(tmpdir)
    return build_done_payload(run_id, outcome, journal)


def stream_agent_run(*, run_id: str, journal: list, start: int, tmpdir: Path | None,
                     restore_entry: dict | None, call: Callable[[], str | dict]):
    """Stream a worker thread's journal steps live, then its terminal frame.

    restore_entry is None for /run; for /answer it is the claimed entry put
    back when the worker fails, so a retry resumes from the pre-answer state
    instead of duplicating tool answers. Bookkeeping is idempotent, so a
    client disconnect mid-stream still settles silently (TTL bounds orphans).
    """
    box: dict = {}
    worker = threading.Thread(target=run_worker_call, args=(call, box), daemon=True)
    worker.start()
    settled = False
    try:
        position = start
        while True:
            while position < len(journal):
                yield format_sse_frame(build_step_frame(journal[position]))
                position += 1
            if box.get("done"):
                break
            time.sleep(POLL_INTERVAL_SECONDS)
        worker.join()
        while position < len(journal):
            yield format_sse_frame(build_step_frame(journal[position]))
            position += 1
        yield format_sse_frame(settle_agent_run(
            run_id=run_id, journal=journal, tmpdir=tmpdir,
            restore_entry=restore_entry, box=box))
        settled = True
    except GeneratorExit:
        worker.join()
        if not settled:
            settle_agent_run(run_id=run_id, journal=journal, tmpdir=tmpdir,
                             restore_entry=restore_entry, box=box)
        raise


app = FastAPI(title="PathProof Demo API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/run")
async def run_agent(
    image: UploadFile | None = File(default=None),
    photo: UploadFile | None = File(default=None),
    audio: UploadFile | None = File(default=None),
    voice: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
) -> StreamingResponse:
    """Accept image + optional audio + fallback text, stream the loop as SSE."""
    purge_expired_runs()
    if len(RUNS) >= MAX_PENDING_RUNS:
        raise HTTPException(status_code=429, detail="too many pending runs, retry later")
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
                         restore_entry=None, call=call),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/answer")
async def answer_agent(payload: AnswerRequest) -> StreamingResponse:
    """Resume a run suspended by ask_student, streaming the follow-up steps."""
    if not isinstance(payload.answer, str) or not payload.answer.strip():
        raise HTTPException(status_code=400, detail="answer must be a non-empty text")
    purge_expired_runs()
    entry = claim_pending_run(payload.run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="unknown run_id")
    suspended = entry["suspended"]
    tmpdir = entry.get("tmpdir")
    journal = suspended.get("journal") or []
    start = len(journal)
    answer = payload.answer.strip()

    def call() -> str | dict:
        messages = suspended.get("messages")
        message_count = len(messages) if isinstance(messages, list) else None
        journal_count = len(journal)
        try:
            client = get_client()
            return loop.resume(client, MUSE_SPARK_MODEL, TOOL_SCHEMAS, suspended, answer)
        except Exception:
            if message_count is not None and isinstance(suspended.get("messages"), list):
                del suspended["messages"][message_count:]
            del journal[journal_count:]
            raise

    return StreamingResponse(
        stream_agent_run(run_id=payload.run_id, journal=journal, start=start,
                         tmpdir=tmpdir, restore_entry=entry, call=call),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
