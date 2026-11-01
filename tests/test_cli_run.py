import json
from pathlib import Path
from types import SimpleNamespace

from src.agent import loop
from src.cli_run import (
    build_user_message,
    default_journal_path,
    report_from_journal,
    resolve_path,
    run_cli_session,
)
from tests.fake_client import ScriptedFakeClient


def tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments, ensure_ascii=False)),
    )


def assistant_message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def test_build_user_message_includes_resolved_paths(tmp_path):
    image = tmp_path / "releve_serie_d.jpg"
    audio = tmp_path / "note.mp3"
    image.write_bytes(b"x")
    audio.write_bytes(b"y")
    message = build_user_message(image.resolve(), audio.resolve())
    assert str(image.resolve()) in message
    assert str(audio.resolve()) in message
    assert "read_grade_sheet" in message
    assert "transcribe_voice" in message


def test_resolve_path_raises_for_missing_file(tmp_path):
    try:
        resolve_path(tmp_path / "missing.jpg", "Grade sheet")
    except Exception as error:
        assert "not found" in str(error)
    else:
        raise AssertionError("expected CliInputError")


def test_default_journal_path_uses_run_label():
    path = default_journal_path(Path("a.jpg"), Path("b.mp3"), "e4.4_clear_sheet_d_medecin")
    assert path == Path("evals/results/e4.4_clear_sheet_d_medecin.json")


def test_report_from_journal_reads_last_build_report():
    journal = [
        {"tool": "verify_report", "result": [], "decision": "continue"},
        {"tool": "build_report", "result": "Rapport vérifié.", "decision": "continue"},
    ]
    assert report_from_journal(journal) == "Rapport vérifié."


def test_run_cli_session_resumes_ask_student(monkeypatch):
    report = "## Accessibilité\nPUB-062"
    ask_question = "Confirmez la série D ?"
    ask = assistant_message(tool_calls=[
        tool_call("call-ask", "ask_student", {"question": ask_question}),
    ])
    verify = assistant_message(tool_calls=[
        tool_call("call-verify", "verify_report",
                  {"report": {"schema_version": 1, "claims": []}, "context": {}}),
    ])
    build = assistant_message(tool_calls=[
        tool_call("call-build", "build_report",
                  {"report": {"schema_version": 1, "claims": []}, "context": {}}),
    ])
    client = ScriptedFakeClient([
        ask,
        verify,
        build,
        assistant_message(content="Terminé."),
    ])

    def fake_verify_report(**kwargs):
        return []

    def fake_build_report(**kwargs):
        return report

    monkeypatch.setitem(loop.TOOLS, "verify_report", fake_verify_report)
    monkeypatch.setitem(loop.TOOLS, "build_report", fake_build_report)
    answers = []

    def scripted_ask(question):
        answers.append(question)
        return "Oui, série D."

    result = run_cli_session(
        client, "fake-model", Path("img.jpg"), Path("voice.mp3"), scripted_ask,
        tool_schemas=[],
    )
    assert answers == [ask_question]
    assert result.report_text == report
    assert result.distinct_tool_count >= 3
    assert any(event["tool"] == "ask_student" for event in result.journal)


def test_blank_answer_stops_resume_loop(monkeypatch):
    ask_question = "Quelle série ?"
    ask = assistant_message(tool_calls=[
        tool_call("call-ask", "ask_student", {"question": ask_question}),
    ])
    client = ScriptedFakeClient([ask])

    def scripted_ask(_question):
        return "   "

    result = run_cli_session(
        client, "fake-model", Path("img.jpg"), None, scripted_ask, tool_schemas=[],
    )
    assert result.outcome["status"] == "needs_input"
    assert len(client.calls) == 1
