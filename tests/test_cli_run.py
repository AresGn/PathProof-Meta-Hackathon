import json
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.agent import loop
from src.cli_run import (
    CliInputError,
    CliRunResult,
    TokenUsage,
    answers_from_lines,
    build_user_message,
    default_journal_path,
    path_for_agent,
    persist_run_artifacts,
    print_outcome,
    report_from_journal,
    resolve_path,
    run_cli_session,
    summary_path_for_journal,
    verified_report_from_journal,
    write_run_summary,
)
from src import main as main_module
from tests.fake_client import ScriptedFakeClient


def tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments, ensure_ascii=False)),
    )


def assistant_message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def test_build_user_message_uses_repo_relative_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    image = tmp_path / "data" / "samples" / "releve.jpg"
    audio = tmp_path / "data" / "samples" / "note.mp3"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"x")
    audio.write_bytes(b"y")
    message = build_user_message(image, audio)
    assert "data/samples/releve.jpg" in message.replace("\\", "/")
    assert "data/samples/note.mp3" in message.replace("\\", "/")
    assert "AresDev" not in message


def test_path_for_agent_prefers_relative(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "data" / "x.jpg"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"")
    assert path_for_agent(path).replace("\\", "/") == "data/x.jpg"


def test_resolve_path_raises_cli_input_error(tmp_path):
    with pytest.raises(CliInputError, match="not found"):
        resolve_path(tmp_path / "missing.jpg", "Grade sheet")


def test_default_journal_path_uses_run_label():
    path = default_journal_path(Path("a.jpg"), Path("b.mp3"), "e4.4_clear_sheet_d_medecin")
    assert path == Path("evals/results/e4.4_clear_sheet_d_medecin.json")


def test_summary_path_uses_full_journal_name():
    assert summary_path_for_journal(Path("evals/results/run.json")) == (
        Path("evals/results/run.json.summary.txt"))
    assert summary_path_for_journal(Path("evals/results/run.txt")) == (
        Path("evals/results/run.txt.summary.txt"))


def test_verified_report_requires_empty_verify_before_build():
    journal = [
        {"step": 1, "tool": "verify_report", "result": [{"claim_id": "x"}], "decision": "continue"},
        {"step": 2, "tool": "build_report", "result": "Stale report.", "decision": "continue"},
    ]
    assert report_from_journal(journal) == "Stale report."
    assert verified_report_from_journal(journal) is None


def test_verified_report_accepts_proven_draft():
    journal = [
        {"step": 5, "tool": "verify_report", "result": [], "decision": "continue"},
        {"step": 6, "tool": "build_report", "result": "OK report.", "decision": "continue"},
    ]
    assert verified_report_from_journal(journal) == "OK report."


def test_verified_report_rejects_tool_calls_after_build():
    journal = [
        {"step": 4, "tool": "verify_report", "result": [], "decision": "continue"},
        {"step": 5, "tool": "build_report", "result": "OK report.", "decision": "continue"},
        {"step": 6, "tool": "verify_report", "result": [{"claim_id": "x"}], "decision": "continue"},
    ]
    assert report_from_journal(journal) == "OK report."
    assert verified_report_from_journal(journal) is None


def test_print_outcome_rejects_stale_report_after_unverified():
    journal = [
        {"step": 1, "tool": "verify_report", "result": [], "decision": "continue"},
        {"step": 2, "tool": "build_report", "result": "Old report.", "decision": "continue"},
    ]
    result = SimpleNamespace(
        journal=journal,
        report_text=None,
        outcome={"status": "unverified"},
    )
    buffer = StringIO()
    assert print_outcome(result, stream=buffer) == 1
    assert buffer.getvalue() == ""


def test_print_outcome_prints_verified_report():
    journal = [
        {"step": 1, "tool": "verify_report", "result": [], "decision": "continue"},
        {"step": 2, "tool": "build_report", "result": "Verified.", "decision": "continue"},
    ]
    result = SimpleNamespace(journal=journal, report_text="Verified.", outcome="done")
    buffer = StringIO()
    assert print_outcome(result, stream=buffer) == 0
    assert buffer.getvalue() == "Verified.\n"


def test_token_usage_adds_fields():
    usage = TokenUsage()
    usage.add(SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15))
    assert usage.total_tokens == 15


def test_answers_from_lines_skips_blanks():
    ask = answers_from_lines(["", "  first  ", "second"])
    assert ask("?") == "  first  "
    assert ask("?") == "second"
    assert ask("?") == ""


def test_print_outcome_prints_model_text_on_stderr_when_unverified(capsys):
    result = SimpleNamespace(
        journal=[],
        report_text=None,
        outcome="Le modèle s'arrête ici.",
    )
    assert print_outcome(result, stream=StringIO()) == 1
    captured = capsys.readouterr()
    assert "without a verified report" in captured.err
    assert "Le modèle s'arrête ici." in captured.err


def test_write_run_summary_uses_summary_suffix(tmp_path):
    journal_path = tmp_path / "run.json"
    result = CliRunResult(
        image_path=Path("data/samples/a.jpg"),
        audio_path=None,
        journal=[{"step": 1, "tool": "read_grade_sheet", "result": {}}],
        outcome={"status": "unverified"},
        report_text=None,
        duration_seconds=1.0,
    )
    write_run_summary(journal_path, result)
    summary = tmp_path / "run.json.summary.txt"
    assert summary.is_file()
    text = summary.read_text(encoding="utf-8")
    assert "Report: not verified (unverified stop)" in text


def test_persist_run_artifacts_writes_journal_only_when_result_missing(tmp_path, capsys):
    journal_path = tmp_path / "run.json"
    journal = [{"step": 1, "tool": "read_grade_sheet", "result": {}}]
    persist_run_artifacts(journal_path, journal, None)
    assert journal_path.is_file()
    captured = capsys.readouterr()
    assert "Journal written" in captured.err
    assert "Summary written" not in captured.err


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


def test_blank_answer_stops_resume_loop():
    ask_question = "Quelle série ?"
    ask = assistant_message(tool_calls=[
        tool_call("call-ask", "ask_student", {"question": ask_question}),
    ])
    client = ScriptedFakeClient([ask])

    result = run_cli_session(
        client, "fake-model", Path("img.jpg"), None, lambda _q: "   ", tool_schemas=[],
    )
    assert result.outcome["status"] == "needs_input"
    assert len(client.calls) == 1


def test_main_returns_2_when_image_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main_module.main(["--image", "missing.jpg"]) == 2
