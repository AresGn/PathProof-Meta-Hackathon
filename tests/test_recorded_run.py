import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import record_demo
from scripts.record_demo import create_recorded_run
from src.agent import loop

ROOT = Path(__file__).resolve().parents[1]


def test_recorded_run_is_built_from_a_verified_fictional_journal():
    journal_path = ROOT / "evals" / "results" / "e4.4_clear_sheet_d_medecin.json"
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    committed_recording = json.loads(
        (ROOT / "web" / "recorded-run.json").read_text(encoding="utf-8")
    )

    recording = create_recorded_run(journal)

    assert committed_recording == recording
    assert recording["events"][-1]["type"] == "done"
    assert recording["events"][-1]["status"] == "ok"
    assert recording["events"][-1]["report"]
    assert recording["events"][-1]["report"] == journal[-1]["result"]


def test_recorded_run_rejects_journals_without_a_verified_report():
    with pytest.raises(ValueError, match="fictional sample"):
        create_recorded_run([])


def test_recorded_run_rejects_non_sample_inputs():
    journal_path = ROOT / "evals" / "results" / "e4.4_clear_sheet_d_medecin.json"
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    image_step = next(event for event in journal if event["tool"] == "read_grade_sheet")
    image_step["args"]["image_path"] = "tmp/student-photo.jpg"

    with pytest.raises(ValueError, match="fixed fictional sample files"):
        create_recorded_run(journal)


def test_recorded_run_accepts_absolute_paths_to_the_fixed_samples():
    journal_path = ROOT / "evals" / "results" / "e4.4_clear_sheet_d_medecin.json"
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    image_step = next(event for event in journal if event["tool"] == "read_grade_sheet")
    audio_step = next(event for event in journal if event["tool"] == "transcribe_voice")
    image_step["args"]["image_path"] = str(ROOT / "data" / "samples" / "releve_serie_d.jpg")
    audio_step["args"]["audio_path"] = str(ROOT / "data" / "samples" / "note_vocale_coherente.mp3")

    recording = create_recorded_run(journal)

    assert recording["events"][-1]["status"] == "ok"


def test_recorded_run_rejects_mismatched_verified_context():
    journal_path = ROOT / "evals" / "results" / "e4.4_clear_sheet_d_medecin.json"
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    build = journal[-1]
    build["args"]["context"]["serie"] = "C"

    with pytest.raises(ValueError, match="verified report"):
        create_recorded_run(journal)


def test_recorded_run_rejects_a_non_successful_live_outcome(monkeypatch):
    journal_path = ROOT / "evals" / "results" / "e4.4_clear_sheet_d_medecin.json"
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    def fake_run(*args, **kwargs):
        kwargs["journal"].extend(journal)
        return SimpleNamespace(
            outcome=loop.STOPPED_STEP_LIMIT,
            report_text=journal[-1]["result"],
        )

    monkeypatch.setattr(record_demo, "run_cli_session", fake_run)

    with pytest.raises(ValueError, match="successful verified report"):
        record_demo.run_fictional_sample()


def test_unexpected_fictional_question_stops_without_an_answer():
    assert record_demo.answer_fictional_question("What is your favorite color?") == ""


def test_cli_does_not_accept_an_arbitrary_journal_file():
    with pytest.raises(SystemExit):
        record_demo.build_parser().parse_args(["--journal", "untrusted.json"])
