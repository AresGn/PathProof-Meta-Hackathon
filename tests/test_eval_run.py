import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from evals import checks, run, summary
from src.cli_run import CliRunResult, TokenUsage

ROOT = Path(__file__).resolve().parents[1]
# Frozen copy of a verified fictional run: evals/results/ is rerun by hand and may change.
VERIFIED_JOURNAL = ROOT / "tests" / "fixtures" / "verified_fictional_journal.json"


def _case(**assertions) -> dict:
    base = {"required_tools": [], "forbidden_strings": [], "required_strings": [],
            "expected_offer_ids": [], "expected_question": None}
    return {"id": "case", "input": {"files": []}, "assertions": {**base, **assertions}}


def _record(report: str | None = None, questions: list[str] | None = None,
            tools: list[str] | None = None) -> dict:
    return {"case_id": "case", "date": "2026-11-03", "outcome_status": "finished",
            "report_text": report, "questions": questions or [], "duration_seconds": 12.0,
            "usage": {"prompt_tokens": 800_000, "completion_tokens": 100_000,
                      "total_tokens": 900_000, "streaming_calls": 0,
                      "by_model": {"muse-spark-1.3-contributor":
                                   {"prompt_tokens": 500_000, "completion_tokens": 50_000},
                                   "muse-wonder-1.0":
                                   {"prompt_tokens": 300_000, "completion_tokens": 50_000}}},
            "error": None,
            "journal": [{"step": index, "tool": tool, "args": {}, "result": None,
                         "decision": "suspend" if tool == "ask_student" else "continue",
                         "model": "model-a"} for index, tool in enumerate(tools or [])]}


def _outcomes(case: dict, record: dict) -> dict[str, bool]:
    return {result.name: result.is_passed for result in checks.evaluate_case(case, record)}


def test_required_tools_must_all_appear_in_the_journal():
    case = _case(required_tools=["read_grade_sheet", "ask_student"])

    outcomes = _outcomes(case, _record(tools=["read_grade_sheet"]))

    assert outcomes == {"required_tool: read_grade_sheet": True,
                        "required_tool: ask_student": False}


def test_strings_ignore_case_accents_and_no_break_spaces():
    case = _case(required_strings=["Faculté classique : oui", "13,15 / 20"])
    report = "FACULTE CLASSIQUE : OUI\n13,15 / 20"

    assert all(_outcomes(case, _record(report=report)).values())


def test_forbidden_strings_are_checked_in_the_report_and_in_the_questions():
    case = _case(forbidden_strings=["PUB-064", "admission garantie"])

    outcomes = _outcomes(case, _record(report="Offre PUB-064", questions=["Admission garantie ?"]))

    assert outcomes == {"forbidden_string: PUB-064": False,
                        "forbidden_string: admission garantie": False}


def test_missing_report_fails_required_strings_and_offer_ids():
    case = _case(required_strings=["13,15 / 20"], expected_offer_ids=["PUB-062"])

    assert not any(_outcomes(case, _record(report=None)).values())


def test_expected_question_accepts_any_alternative():
    case = _case(expected_question=["Mathématiques", "maths"])

    assert all(_outcomes(case, _record(questions=["Quelle est ta note de maths ?"])).values())
    assert not any(_outcomes(case, _record(questions=["Quelle est ta série ?"])).values())


def test_null_expected_question_is_not_asserted():
    assert checks.evaluate_case(_case(), _record(questions=["Confirmes-tu la série D ?"])) == []


def test_case_is_conform_only_when_every_assertion_passes():
    passed = checks.AssertionResult("a", True)
    failed = checks.AssertionResult("b", False)

    assert checks.is_conform([passed])
    assert not checks.is_conform([passed, failed])


def test_replay_gives_the_recorded_verifier_problems():
    journal = json.loads(VERIFIED_JOURNAL.read_text(encoding="utf-8"))

    outcome = checks.replay_verification({"journal": journal})

    assert outcome["is_same"]
    assert outcome["replayed"] == outcome["recorded"] == []


def test_replay_flags_a_recorded_result_that_the_verifier_no_longer_gives():
    journal = json.loads(VERIFIED_JOURNAL.read_text(encoding="utf-8"))
    last_verify = [event for event in journal if event["tool"] == "verify_report"][-1]
    last_verify["result"] = [{"claim_id": "x", "type": "grade", "reason": "forged"}]

    assert not checks.replay_verification({"journal": journal})["is_same"]


def test_replay_needs_a_recorded_verifier_call():
    with pytest.raises(ValueError, match="no verify_report call"):
        checks.replay_verification({"journal": []})


def test_summary_table_reports_conformity_counts_duration_tokens_and_cost():
    case = _case(required_tools=["ask_student"], required_strings=["13,15 / 20"],
                 expected_question=["série"])
    record = _record(report="13,15 / 20", questions=["Quelle série ?"],
                     tools=["read_grade_sheet", "ask_student"])

    text = summary.render_summary("2026-11-03", [(case, record)])

    # 0.5 M x 0.10 + 0.05 M x 0.20 (Contributor) + 0.3 M x 4 + 0.05 M x 20 (Wonder)
    assert "| case | pass | 3/3 | 2 | 1 | 12 s | 900,000 | $2.26 |" in text
    assert "1 of 1 cases conform" in text
    assert "- pass `required_tool: ask_student`" in text


def test_summary_leaves_the_cost_open_without_per_model_tokens_or_with_an_unpriced_model():
    older = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2, "streaming_calls": 0}
    unpriced = {**older, "by_model": {"some-new-model": {"prompt_tokens": 1,
                                                          "completion_tokens": 1}}}

    assert summary.estimate_cost(older) is None
    assert summary.estimate_cost(unpriced) is None


def test_summary_marks_failures():
    case = _case(required_tools=["ask_student"])

    text = summary.render_summary("2026-11-03", [(case, _record())])

    assert "| case | FAIL | 0/1 |" in text
    assert "- FAIL `required_tool: ask_student` (never called)" in text


NO_FILES = {"image_path": None, "audio_path": None, "voice_text": None}


def _fake_result(journal: list, usage: TokenUsage) -> CliRunResult:
    usage.add(SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15), "model-a")
    return CliRunResult(image_path=None, audio_path=None, journal=journal, outcome="done",
                        report_text="13,15 / 20", usage=usage, duration_seconds=3.5,
                        questions=["Quelle série ?"])


def test_run_case_records_the_raw_output_with_the_scripted_answers(monkeypatch):
    def fake_session(client, model, *, ask_student, journal, usage, **kwargs):
        ask_student("Quelle est votre série ?")
        journal.append({"step": 1, "tool": "ask_student", "args": {}, "result": None,
                        "decision": "suspend", "model": "model-a"})
        return _fake_result(journal, usage)

    monkeypatch.setattr(run, "run_cli_session", fake_session)
    monkeypatch.setattr(run, "case_inputs", lambda case: NO_FILES)
    script = [{"when": ["serie"], "answer": "Oui, série D."}]

    record = run.run_case(object(), {**_case(), "student_answers": script}, "2026-11-03")

    assert record["exchanges"] == [{"question": "Quelle est votre série ?",
                                    "answer": "Oui, série D."}]
    assert record["usage"]["total_tokens"] == 15
    assert record["usage"]["by_model"] == {"model-a": {"prompt_tokens": 10, "completion_tokens": 5}}
    assert record["questions"] == ["Quelle série ?"]
    assert record["journal"][0]["tool"] == "ask_student"
    assert record["error"] is None


def test_run_case_keeps_tokens_duration_and_questions_when_the_run_crashes(monkeypatch):
    def failing_session(client, model, *, journal, usage, **kwargs):
        usage.add(SimpleNamespace(prompt_tokens=100, completion_tokens=20, total_tokens=120),
                  "model-a")
        journal.append({"step": 1, "tool": "ask_student", "args": {"question": "Quelle série ?"},
                        "result": None, "decision": "suspend", "model": "model-a"})
        raise RuntimeError("upstream down")

    monkeypatch.setattr(run, "run_cli_session", failing_session)
    monkeypatch.setattr(run, "case_inputs", lambda case: NO_FILES)

    record = run.run_case(object(), _case(), "2026-11-03")

    assert record["outcome_status"] == "error"
    assert record["error"] == "RuntimeError: upstream down"
    assert record["usage"]["total_tokens"] == 120
    assert summary.estimate_cost(record["usage"]) is None  # model-a has no rate: never guessed
    assert record["questions"] == ["Quelle série ?"]
    assert record["duration_seconds"] >= 0


def test_a_finished_run_without_a_verified_report_is_not_called_finished():
    usage = TokenUsage()
    result = _fake_result([], usage)
    result.report_text = None

    assert run.status_of(result) == "no_verified_report"
    assert run.status_of(None) == "error"


def test_scripted_answers_follow_the_question_not_the_order():
    exchanges: list[dict] = []
    script = [{"when": ["serie", "series"], "answer": "série D"},
              {"when": ["moyenne"], "answer": "garder 11,2"}]
    ask = run.answers_from_script(script, exchanges)

    assert ask("Quelle est votre MOYENNE ?") == "garder 11,2"
    assert ask("Confirmez-vous la série ?") == "série D"
    assert ask("Une autre question ?") == ""  # nothing matches: blank answer, the run stops
    assert ask("Et la série encore ?") == ""  # each scripted answer is given once
    assert [exchange["answer"] for exchange in exchanges] == ["garder 11,2", "série D", "", ""]


def test_a_failed_or_unsuspended_ask_student_is_not_a_tool_call():
    failed = {"tool": "ask_student", "args": {}, "result": {"error": "invalid question"},
              "decision": "continue"}
    unfinished = {"tool": "ask_student", "args": {}, "result": None, "decision": "stop_step_limit"}
    suspended = {"tool": "ask_student", "args": {}, "result": {"status": "needs_input"},
                 "decision": "suspend"}

    assert checks.called_tools({"journal": [failed, unfinished]}) == set()
    assert checks.called_tools({"journal": [failed, suspended]}) == {"ask_student"}


def test_write_summary_rebuilds_the_table_from_raw_results_in_case_order(tmp_path):
    cases = [{**_case(), "id": "second"}, {**_case(), "id": "first"}]
    for case in cases:
        run.write_record(tmp_path / "2026-11-03", {**_record(tools=["read_grade_sheet"]), "case_id": case["id"]})

    path = run.write_summary("2026-11-03", cases, results_root=tmp_path)

    text = path.read_text(encoding="utf-8")
    assert path == tmp_path / "summary.md"
    assert text.index("| second |") < text.index("| first |")
    assert "model-a (" in text  # deciding models are read from the journals


def test_unknown_case_id_is_refused():
    with pytest.raises(ValueError, match="unknown case id"):
        run.select_cases(run.load_cases(), ["nope"])


@pytest.mark.parametrize("value", ["../../tmp", "2026-13-01", "today", ""])
def test_date_must_be_a_calendar_date(value, capsys):
    with pytest.raises(SystemExit):
        run.build_parser().parse_args(["--date", value])
    assert "YYYY-MM-DD" in capsys.readouterr().err


def test_committed_cases_with_a_voice_note_script_the_series_confirmation():
    cases = {case["id"]: case for case in run.load_cases()}

    for case_id in ("clear_sheet_d_medecin", "voice_contradicts_sheet",
                    "english_voice_d_medecin", "noisy_voice"):
        script = cases[case_id]["student_answers"]
        assert script
        for entry in script:
            assert entry["answer"] and entry["when"]
            assert all(isinstance(word, str) and word for word in entry["when"])


def test_without_live_nothing_reaches_the_api(monkeypatch, capsys):
    def forbidden_client():
        raise AssertionError("a dry run must not create the API client")

    monkeypatch.setattr(run, "get_client", forbidden_client)
    monkeypatch.setattr(run, "run_live", forbidden_client)

    assert run.main([]) == 0
    assert run.main(["--case", "clear_sheet_d_medecin"]) == 0

    assert "Dry run" in capsys.readouterr().out


def _live_with_fake_cases(monkeypatch, tmp_path):
    """Real run_live and write_summary, redirected to tmp_path; only the agent is faked."""
    monkeypatch.setattr(run, "get_client", lambda: "fake-client")
    monkeypatch.setattr(run, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(run, "run_case",
                        lambda client, case, date: {**_record(), "case_id": case["id"],
                                                    "date": date})


def test_full_live_run_writes_one_raw_result_per_case_and_the_summary(monkeypatch, tmp_path):
    _live_with_fake_cases(monkeypatch, tmp_path)

    assert run.main(["--live", "--date", "2026-11-03"]) == 0

    cases = run.load_cases()
    assert len(list((tmp_path / "2026-11-03").glob("*.json"))) == len(cases)
    assert f"of {len(cases)} cases conform" in (tmp_path / "summary.md").read_text(encoding="utf-8")


def test_partial_live_run_writes_its_result_but_leaves_the_summary_alone(monkeypatch, tmp_path):
    _live_with_fake_cases(monkeypatch, tmp_path)
    (tmp_path / "summary.md").write_text("full table", encoding="utf-8")

    assert run.main(["--live", "--case", "clear_sheet_d_medecin", "--date", "2026-11-03"]) == 0

    assert (tmp_path / "2026-11-03" / "clear_sheet_d_medecin.json").is_file()
    assert (tmp_path / "summary.md").read_text(encoding="utf-8") == "full table"


def test_neither_pytest_nor_the_ci_launch_the_evaluations():
    workflow_text = "\n".join(path.read_text(encoding="utf-8")
                              for path in (ROOT / ".github" / "workflows").glob("*.yml"))
    assert "evals.run" not in workflow_text
    assert "--live" not in workflow_text
    assert "testpaths = tests" in (ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert not list((ROOT / "evals").rglob("test_*.py"))
    for test_path in (ROOT / "tests").glob("test_*.py"):
        if test_path.name == "test_eval_run.py":
            continue
        assert "evals.run" not in test_path.read_text(encoding="utf-8")
