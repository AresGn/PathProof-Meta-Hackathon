import json
from pathlib import Path

import pytest

from scripts.record_demo import create_recorded_run

ROOT = Path(__file__).resolve().parents[1]


def test_recorded_run_is_built_from_a_verified_fictional_journal():
    journal_path = ROOT / "evals" / "results" / "e4.4_clear_sheet_d_medecin.json"
    journal = json.loads(journal_path.read_text(encoding="utf-8"))

    recording = create_recorded_run(journal)

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
