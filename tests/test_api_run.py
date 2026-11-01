"""POST /run SSE flux and POST /answer resume (E5.1, issue #30).

No network, no API key: the Meta client is faked, only the loop wiring,
ordering, limits and error mapping are exercised.
"""
import io
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.agent import loop
from src.api import server
from tests.fake_client import ScriptedFakeClient


def tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments, ensure_ascii=False)),
    )


def assistant_message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def parse_sse(text):
    """Parse a text/event-stream body into a list of JSON payloads."""
    events = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        for line in block.splitlines():
            if line.startswith("data:"):
                events.append(json.loads(line[len("data:"):].strip()))
    return events


def step_events(events):
    return [event for event in events if event.get("type") == "step"]


def make_client(monkeypatch):
    app = TestClient(server.app)
    # Isolate runs between tests (in-memory sessions + temp dirs).
    server.RUNS.clear()
    return app


def test_run_streams_steps_in_order(monkeypatch):
    app = make_client(monkeypatch)
    lookup = {"accessible": [], "excluded": []}
    monkeypatch.setitem(loop.TOOLS, "lookup_filieres", lambda **kwargs: dict(lookup))
    client = ScriptedFakeClient([
        assistant_message(tool_calls=[tool_call("c1", "lookup_filieres", {"serie": "D"})]),
        assistant_message(tool_calls=[tool_call("c2", "lookup_filieres", {"serie": "D"})]),
        assistant_message(content="Terminé."),
    ])
    monkeypatch.setattr(server, "get_client", lambda: client)

    response = app.post(
        "/run",
        files={"image": ("sheet.jpg", b"fake-image", "image/jpeg")},
        data={"text": "fallback"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    events = parse_sse(response.text)
    steps = step_events(events)
    assert [event["step"] for event in steps] == [1, 2]
    assert [event["tool"] for event in steps] == ["lookup_filieres", "lookup_filieres"]
    for event in steps:
        assert set(("step", "tool", "args", "result", "decision")) <= set(event)
        assert event["decision"] == "continue"
    # The stub 501 is gone: no event carries it and the status is 200.
    assert response.status_code != 501
    assert "not implemented" not in response.text


def test_run_accepts_image_audio_and_text(monkeypatch):
    app = make_client(monkeypatch)
    monkeypatch.setitem(loop.TOOLS, "lookup_filieres", lambda **kwargs: {"accessible": [], "excluded": []})
    client = ScriptedFakeClient([
        assistant_message(tool_calls=[tool_call("c1", "lookup_filieres", {"serie": "D"})]),
        assistant_message(content="Terminé."),
    ])
    monkeypatch.setattr(server, "get_client", lambda: client)

    response = app.post(
        "/run",
        files={
            "image": ("sheet.jpg", b"fake-image", "image/jpeg"),
            "audio": ("note.mp3", b"fake-audio", "audio/mpeg"),
        },
        data={"text": "je suis en D, je veux être médecin"},
    )
    assert response.status_code == 200
    events = parse_sse(response.text)
    assert step_events(events), "expected at least one streamed step"


def test_ask_student_produces_needs_input_then_answer_resumes(monkeypatch):
    app = make_client(monkeypatch)
    question = "Quelle est ta série ?"
    monkeypatch.setitem(loop.TOOLS, "lookup_filieres", lambda **kwargs: {"accessible": [], "excluded": []})
    client = ScriptedFakeClient([
        assistant_message(tool_calls=[tool_call("ask-1", "ask_student", {"question": question})]),
        assistant_message(tool_calls=[tool_call("c2", "lookup_filieres", {"serie": "D"})]),
        assistant_message(content="Merci, je continue."),
    ])
    monkeypatch.setattr(server, "get_client", lambda: client)

    first = app.post(
        "/run",
        files={"image": ("sheet.jpg", b"fake-image", "image/jpeg")},
    )
    assert first.status_code == 200
    first_events = parse_sse(first.text)
    needs = [event for event in first_events if event.get("type") == "needs_input"]
    assert len(needs) == 1
    assert needs[0]["question"] == question
    run_id = needs[0]["run_id"]
    assert run_id

    second = app.post("/answer", json={"run_id": run_id, "answer": "Série D."})
    assert second.status_code == 200
    second_events = parse_sse(second.text)
    second_steps = step_events(second_events)
    # The resumed tool call is streamed after the suspension (step 2).
    assert [event["step"] for event in second_steps] == [2]
    assert second_steps[0]["tool"] == "lookup_filieres"
    done = [event for event in second_events if event.get("type") == "done"]
    assert done, "expected a final done event after resume"


def test_image_too_large_returns_413(monkeypatch):
    app = make_client(monkeypatch)
    monkeypatch.setattr(server, "MAX_IMAGE_BYTES", 10)
    response = app.post(
        "/run",
        files={"image": ("sheet.jpg", b"x" * 11, "image/jpeg")},
    )
    assert response.status_code == 413


def test_audio_too_large_returns_413(monkeypatch):
    app = make_client(monkeypatch)
    monkeypatch.setattr(server, "MAX_AUDIO_BYTES", 10)
    response = app.post(
        "/run",
        files={
            "image": ("sheet.jpg", b"ok", "image/jpeg"),
            "audio": ("note.mp3", b"y" * 11, "audio/mpeg"),
        },
    )
    assert response.status_code == 413


def test_unsupported_image_type_returns_415():
    app = TestClient(server.app)
    server.RUNS.clear()
    response = app.post(
        "/run",
        files={"image": ("sheet.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 415


def test_unsupported_audio_type_returns_415():
    app = TestClient(server.app)
    server.RUNS.clear()
    response = app.post(
        "/run",
        files={
            "image": ("sheet.jpg", b"ok", "image/jpeg"),
            "audio": ("note.txt", b"not audio", "text/plain"),
        },
    )
    assert response.status_code == 415


def test_tool_error_becomes_error_event_not_500(monkeypatch):
    app = make_client(monkeypatch)

    def broken_client():
        raise RuntimeError("boom from the client factory")

    monkeypatch.setattr(server, "get_client", broken_client)
    response = app.post(
        "/run",
        files={"image": ("sheet.jpg", b"fake-image", "image/jpeg")},
    )
    assert response.status_code == 200
    events = parse_sse(response.text)
    errors = [event for event in events if event.get("type") == "error"]
    assert errors, "expected an error event, not a raw 500"
    assert "boom from the client factory" in errors[0]["error"]


def test_api_key_never_appears_in_responses(monkeypatch):
    app = make_client(monkeypatch)
    secret = "sk-test-secret-abcdef-12345"
    monkeypatch.setenv("MUSE_API_KEY", secret)

    def leaking_client():
        raise RuntimeError(f"auth failed with {secret} inside")

    monkeypatch.setattr(server, "get_client", leaking_client)
    response = app.post(
        "/run",
        files={"image": ("sheet.jpg", b"fake-image", "image/jpeg")},
    )
    assert response.status_code == 200
    assert secret not in response.text
    assert "MUSE_API_KEY" not in response.text


def test_no_501_stub_left():
    source = Path(server.__file__).read_text(encoding="utf-8")
    assert "501" not in source
    assert "not implemented" not in source
