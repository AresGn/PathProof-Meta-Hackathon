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
    UsageTrackingClient,
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


def test_build_user_message_passes_fallback_text_without_a_grade_sheet():
    message = build_user_message(None, None, "Je suis en série ... (bruit)")
    assert "read_grade_sheet" not in message
    assert "transcribe_voice" in message  # told to skip it
    assert "Je suis en série ... (bruit)" in message


def test_default_journal_path_names_every_given_input():
    path = default_journal_path(None, None, None, Path("intention_pilote.txt"))
    assert path == Path("evals/results/intention_pilote.json")


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
    report = {"claims": [{"claim_id": "x"}]}
    context = {"grades": [{"matiere": "SVT", "note": 15}]}
    journal = [
        {"step": 5, "tool": "verify_report", "args": {"report": report, "context": context},
         "result": [], "decision": "continue"},
        {"step": 6, "tool": "build_report", "args": {"report": report, "context": context},
         "result": "OK report.", "decision": "continue"},
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


def test_wonder_responses_calls_are_counted():
    usage = TokenUsage()
    response = SimpleNamespace(usage=SimpleNamespace(input_tokens=40, output_tokens=60, total_tokens=100))
    inner = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=None)),
                            responses=SimpleNamespace(create=lambda **kwargs: response))
    client = UsageTrackingClient(inner, usage)
    assert client.responses.create(model="muse-wonder-1.0") is response
    assert (usage.prompt_tokens, usage.completion_tokens, usage.total_tokens) == (40, 60, 100)


def test_answers_from_lines_keeps_blank_lines_so_answers_stay_aligned():
    ask = answers_from_lines(["oui", "", "médecin"])
    assert ask("?") == "oui"
    assert ask("?") == ""
    assert ask("?") == "médecin"
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
        journal=[{"step": 1, "tool": "read_grade_sheet", "result": {},
                  "model": "muse-spark-1.3-contributor"},
                 {"step": 2, "tool": "verify_report", "result": [], "model": "muse-wonder-1.0"},
                 {"step": 3, "tool": "verify_report", "result": [], "model": "muse-wonder-1.0"}],
        outcome={"status": "unverified"},
        report_text=None,
        duration_seconds=1.0,
    )
    write_run_summary(journal_path, result)
    summary = tmp_path / "run.json.summary.txt"
    assert summary.is_file()
    text = summary.read_text(encoding="utf-8")
    assert "Report: not verified (unverified stop)" in text
    assert ("Models that decided the steps: muse-spark-1.3-contributor (1), "
            "muse-wonder-1.0 (2)") in text


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


def test_print_outcome_prints_a_verified_report_when_the_step_limit_ended_the_loop():
    result = SimpleNamespace(journal=[], report_text="Verified.", outcome=loop.STOPPED_STEP_LIMIT)
    buffer = StringIO()
    assert print_outcome(result, stream=buffer) == 0
    assert buffer.getvalue() == "Verified.\n"


def test_verified_report_rejects_a_build_of_another_draft_than_the_verified_one():
    journal = [
        {"step": 1, "tool": "verify_report",
         "args": {"report": {"claims": ["A"]}, "context": {"serie": "D"}},
         "result": [], "decision": "continue"},
        {"step": 2, "tool": "build_report",
         "args": {"report": {"claims": ["B"]}, "context": {"serie": "D"}},
         "result": "Report B.", "decision": "continue"},
    ]
    assert verified_report_from_journal(journal) is None
    journal[1]["args"]["report"] = {"claims": ["A"]}
    assert verified_report_from_journal(journal) == "Report B."


def test_verified_report_rejects_a_build_with_a_different_context():
    journal = [
        {"step": 1, "tool": "verify_report",
         "args": {"report": {"claims": []}, "context": {"serie": "D"}},
         "result": [], "decision": "continue"},
        {"step": 2, "tool": "build_report",
         "args": {"report": {"claims": []}, "context": {"serie": "C"}},
         "result": "Report.", "decision": "continue"},
    ]

    assert verified_report_from_journal(journal) is None


@pytest.mark.parametrize("label", ["../../x", "a/b", "..", "."])
def test_default_journal_path_rejects_a_label_that_is_not_a_plain_file_name(label):
    with pytest.raises(CliInputError, match="run-label"):
        default_journal_path(Path("a.jpg"), None, label)


def test_duration_excludes_the_time_spent_waiting_for_the_student(monkeypatch):
    clock = iter([0.0, 10.0, 70.0, 100.0])  # start, ask start, ask end, end
    monkeypatch.setattr("src.cli_run.time.monotonic", lambda: next(clock))
    ask = assistant_message(tool_calls=[tool_call("call-ask", "ask_student", {"question": "Série ?"})])
    client = ScriptedFakeClient([ask, assistant_message(content="Fin.")])
    result = run_cli_session(client, "fake-model", Path("img.jpg"), None,
                             lambda _q: "D", tool_schemas=[])
    assert result.duration_seconds == 40.0


def test_main_returns_2_when_the_client_cannot_be_created(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sheet.jpg").write_bytes(b"x")

    def broken_client():
        raise ValueError("malformed base URL")

    monkeypatch.setattr(main_module, "get_client", broken_client)
    assert main_module.main(["--image", "sheet.jpg"]) == 2
    assert "ValueError" in capsys.readouterr().err


def test_main_returns_2_for_an_unsafe_run_label(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sheet.jpg").write_bytes(b"x")
    assert main_module.main(["--image", "sheet.jpg", "--run-label", "../../x"]) == 2


def test_main_runs_the_same_models_as_the_demo_server(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sheet.jpg").write_bytes(b"x")
    seen = {}

    def fake_session(client, model, image_path, audio_path, ask, **kwargs):
        seen.update(model=model, **kwargs)
        raise RuntimeError("stop after recording the arguments")

    monkeypatch.setattr(main_module, "get_client", lambda: object())
    monkeypatch.setattr(main_module, "run_cli_session", fake_session)
    monkeypatch.setattr(main_module, "persist_run_artifacts", lambda *args: None)
    assert main_module.main(["--image", "sheet.jpg", "--language", "en"]) == 1
    assert seen["model"] == "muse-spark-1.3-contributor"
    assert seen["drafting_model"] == "muse-wonder-1.0"
    assert seen["language"] == "en"


def test_main_rejects_a_run_without_any_input():
    with pytest.raises(SystemExit) as error:
        main_module.main([])
    assert error.value.code == 2


def test_main_sends_the_voice_text_file_without_a_grade_sheet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "voix.txt").write_text("Je veux devenir pilote de ligne.", encoding="utf-8")
    seen = {}

    def fake_session(_client, _model, image_path, audio_path, _ask, *, voice_text, **_kwargs):
        seen.update(image=image_path, audio=audio_path, text=voice_text)
        raise RuntimeError("stop after capture")

    monkeypatch.setattr(main_module, "get_client", lambda: object())
    monkeypatch.setattr(main_module, "run_cli_session", fake_session)
    assert main_module.main(["--voice-text", "voix.txt"]) == 1
    assert seen == {"image": None, "audio": None, "text": "Je veux devenir pilote de ligne."}
