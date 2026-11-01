"""FastAPI demo server: real agent loop streamed as SSE (E5.1, issue #30).

Orchestration only: validate uploads, save them under a repo-relative
tmp dir (so journals never carry a personal absolute path), run
`src/agent/loop.py` and stream its journal as `{step, tool, args, result,
decision}` events. No average, no filtering, no proof check lives here.
"""
import json
import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.agent import loop
from src.agent.tool_schemas import TOOL_SCHEMAS
from src.cli_run import path_for_agent, verified_report_from_journal
from src.clients.meta_client import get_client
from src.clients.muse_spark import MUSE_SPARK_MODEL

WEB_DIR = Path(__file__).resolve().parents[2] / "web"

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # demo upload cap for grade-sheet photos (E5.1)
MAX_AUDIO_BYTES = 32 * 1024 * 1024  # docs/decisions.md E0.5: transcribe endpoint body limit
SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}  # src/clients/vision.py MEDIA_TYPES
SUPPORTED_AUDIO_SUFFIXES = {".flac", ".m4a", ".mp3", ".ogg", ".opus", ".wav", ".webm"}  # src/tools/transcribe_voice.py SUPPORTED_AUDIO_TYPES

RUNS: dict[str, dict] = {}  # run_id -> {"suspended", "tmpdir"} for ask_student resume (E5.1)


class AnswerRequest(BaseModel):
    """Student answer resuming a run suspended by ask_student."""

    run_id: str
    answer: str


def _sanitize_text(message: str) -> str:
    """Strip the API key value and its env name so they never reach a response."""
    secret = os.environ.get("MUSE_API_KEY", "")
    if secret and secret in message:
        message = message.replace(secret, "[redacted]")
    return message.replace("MUSE_API_KEY", "API key")


def _sse(payload: dict) -> str:
    """Format one SSE data frame, sanitized so the key never leaks."""
    return f"data: {_sanitize_text(json.dumps(payload, ensure_ascii=False))}\n\n"


def _suffix(filename: str | None) -> str:
    return Path(filename or "").suffix.lower()


def _check_suffix(suffix: str, allowed: set[str], label: str) -> None:
    if suffix not in allowed:
        raise HTTPException(status_code=415, detail=f"unsupported {label} type: {suffix or '(none)'}")


def _check_size(data: bytes, limit: int, label: str) -> None:
    if len(data) > limit:
        raise HTTPException(status_code=413, detail=f"{label} too large ({len(data)} bytes)")
    if not data:
        raise HTTPException(status_code=400, detail=f"empty {label} file")


def _new_tmpdir(run_id: str) -> Path:
    tmpdir = Path.cwd() / "tmp" / f"pathproof-{run_id}"
    tmpdir.mkdir(parents=True, exist_ok=True)
    return tmpdir


def _cleanup_tmpdir(tmpdir: Path | None) -> None:
    if tmpdir is None:
        return
    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except OSError:
        pass


def _build_user_message(image_path: Path | None, audio_path: Path | None,
                        text: str | None) -> str:
    """Describe the student inputs for the model; paths stay repo-relative."""
    lines = ["The student submitted a grade-sheet photo and a voice note (fictional sample)."]
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


def _done_payload(run_id: str, outcome: str | dict, journal: list) -> dict:
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


def _stream_steps(journal: list, start: int = 0):
    for event in journal[start:]:
        yield _sse({"type": "step", "step": event.get("step"), "tool": event.get("tool"),
                    "args": event.get("args"), "result": event.get("result"),
                    "decision": event.get("decision")})


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
    image_file = image or photo
    audio_file = audio or voice
    if image_file is None and (text is None or not text.strip()):
        raise HTTPException(status_code=400, detail="provide an image or a text fallback")

    image_bytes: bytes | None = None
    image_suffix = ""
    if image_file is not None:
        image_suffix = _suffix(image_file.filename)
        _check_suffix(image_suffix, SUPPORTED_IMAGE_SUFFIXES, "image")
        image_bytes = await image_file.read()
        _check_size(image_bytes, MAX_IMAGE_BYTES, "image")

    audio_bytes: bytes | None = None
    audio_suffix = ""
    if audio_file is not None:
        audio_suffix = _suffix(audio_file.filename)
        _check_suffix(audio_suffix, SUPPORTED_AUDIO_SUFFIXES, "audio")
        audio_bytes = await audio_file.read()
        _check_size(audio_bytes, MAX_AUDIO_BYTES, "audio")

    run_id = uuid.uuid4().hex
    tmpdir = _new_tmpdir(run_id)
    image_path = tmpdir / f"image{image_suffix}" if image_bytes is not None else None
    if image_path is not None and image_bytes is not None:
        image_path.write_bytes(image_bytes)
    audio_path = tmpdir / f"audio{audio_suffix}" if audio_bytes is not None else None
    if audio_path is not None and audio_bytes is not None:
        audio_path.write_bytes(audio_bytes)
    user_input = _build_user_message(image_path, audio_path, text)

    def generate():
        journal: list = []
        try:
            client = get_client()
            outcome = loop.run(client, MUSE_SPARK_MODEL, TOOL_SCHEMAS, user_input,
                               journal=journal)
        except Exception as error:
            yield _sse({"type": "error", "error": _sanitize_text(str(error))})
            _cleanup_tmpdir(tmpdir)
            return
        yield from _stream_steps(journal, 0)
        if isinstance(outcome, dict) and outcome.get("status") == "needs_input":
            RUNS[run_id] = {"suspended": outcome, "tmpdir": tmpdir}
            yield _sse({"type": "needs_input", "run_id": run_id,
                        "question": outcome.get("question"),
                        "step": outcome.get("steps_used")})
            return
        yield _sse(_done_payload(run_id, outcome, journal))
        _cleanup_tmpdir(tmpdir)
        RUNS.pop(run_id, None)

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.post("/answer")
async def answer_agent(payload: AnswerRequest) -> StreamingResponse:
    """Resume a run suspended by ask_student, streaming the follow-up steps."""
    entry = RUNS.get(payload.run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="unknown run_id")
    if not isinstance(payload.answer, str) or not payload.answer.strip():
        raise HTTPException(status_code=400, detail="answer must be a non-empty text")
    suspended = entry["suspended"]
    tmpdir = entry.get("tmpdir")
    journal = suspended.get("journal") or []
    start = len(journal)

    def generate():
        try:
            client = get_client()
            outcome = loop.resume(client, MUSE_SPARK_MODEL, TOOL_SCHEMAS, suspended,
                                  payload.answer.strip())
        except Exception as error:
            yield _sse({"type": "error", "error": _sanitize_text(str(error))})
            return
        yield from _stream_steps(journal, start)
        if isinstance(outcome, dict) and outcome.get("status") == "needs_input":
            entry["suspended"] = outcome
            yield _sse({"type": "needs_input", "run_id": payload.run_id,
                        "question": outcome.get("question"),
                        "step": outcome.get("steps_used")})
            return
        yield _sse(_done_payload(payload.run_id, outcome, journal))
        _cleanup_tmpdir(tmpdir)
        RUNS.pop(payload.run_id, None)

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
