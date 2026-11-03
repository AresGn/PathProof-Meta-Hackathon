import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import record_demo
from scripts.record_demo import create_recorded_run
from src.agent import loop

ROOT = Path(__file__).resolve().parents[1]
# Frozen copy of a verified fictional run: evals/results/ is rerun by hand and may change.
VERIFIED_JOURNAL = ROOT / "tests" / "fixtures" / "verified_fictional_journal.json"


def test_recorded_run_is_built_from_a_verified_fictional_journal():
    journal_path = VERIFIED_JOURNAL
    journal = json.loads(journal_path.read_text(encoding="utf-8"))

    recording = create_recorded_run(journal)

    assert recording["events"][-1]["type"] == "done"
    assert recording["events"][-1]["status"] == "ok"
    assert recording["events"][-1]["report"]
    assert recording["events"][-1]["report"] != journal[-1]["result"]
    assert recording["events"][-1]["report"].startswith("PathProof — rapport enregistré")
    assert all(event["tool"] != "ask_student" for event in recording["events"][:-1])
    assert "vérifié" not in recording["events"][-1]["report"].casefold()


def _recording(name):
    return json.loads((ROOT / "web" / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["recorded-run.json", "recorded-run.en.json"])
def test_committed_recordings_name_the_model_that_decided_each_step(name):
    steps = _recording(name)["events"][:-1]
    models = [step["model"] for step in steps]
    assert all(models), "a step without its deciding model would show a made-up one"
    # Real run of 3 nov: the contributor reads, Wonder (effort high) drafts and verifies.
    assert models[0] == "muse-spark-1.3-contributor"
    assert next(step for step in steps if step["tool"] == "verify_report")["model"] == "muse-wonder-1.0"
    assert steps[-1]["tool"] == "build_report" and steps[-1]["model"] == "muse-wonder-1.0"


def test_french_recording_is_a_verified_french_run():
    events = _recording("recorded-run.json")["events"]
    assert events[-1]["report"].startswith("PathProof — rapport enregistré")
    assert "vérifié" not in events[-1]["report"].casefold()
    assert events[-2]["tool"] == "build_report" and events[-2]["result"] == events[-1]["report"]
    assert any(step["tool"] == "verify_report" and step["result"] == [] for step in events[:-1])


def test_recorded_run_rejects_journals_without_a_verified_report():
    with pytest.raises(ValueError, match="fictional sample"):
        create_recorded_run([])


def test_recorded_run_rejects_non_sample_inputs():
    journal_path = VERIFIED_JOURNAL
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    image_step = next(event for event in journal if event["tool"] == "read_grade_sheet")
    image_step["args"]["image_path"] = "tmp/student-photo.jpg"

    with pytest.raises(ValueError, match="fixed fictional sample files"):
        create_recorded_run(journal)


def test_recorded_run_accepts_absolute_paths_to_the_fixed_samples():
    journal_path = VERIFIED_JOURNAL
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    image_step = next(event for event in journal if event["tool"] == "read_grade_sheet")
    audio_step = next(event for event in journal if event["tool"] == "transcribe_voice")
    image_step["args"]["image_path"] = str(ROOT / "data" / "samples" / "releve_serie_d.jpg")
    audio_step["args"]["audio_path"] = str(ROOT / "data" / "samples" / "note_vocale_coherente.mp3")

    recording = create_recorded_run(journal)

    assert recording["events"][-1]["status"] == "ok"


def test_recorded_run_rejects_mismatched_verified_context():
    journal_path = VERIFIED_JOURNAL
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    build = journal[-1]
    build["args"]["context"]["serie"] = "C"

    with pytest.raises(ValueError, match="verified report"):
        create_recorded_run(journal)


def test_recorded_run_rejects_a_non_successful_live_outcome(monkeypatch):
    journal_path = VERIFIED_JOURNAL
    journal = json.loads(journal_path.read_text(encoding="utf-8"))

    def fake_run(*args, **kwargs):
        kwargs["journal"].extend(journal)
        return SimpleNamespace(
            outcome=loop.STOPPED_STEP_LIMIT,
            report_text=journal[-1]["result"],
        )

    monkeypatch.setattr(record_demo, "get_client", lambda: object())
    monkeypatch.setattr(record_demo, "run_cli_session", fake_run)

    with pytest.raises(ValueError, match="successful verified report"):
        record_demo.run_fictional_sample()


def test_recorded_run_rejects_unexpected_question_sequence(monkeypatch):
    journal_path = VERIFIED_JOURNAL
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    question_event = next(event for event in journal if event["tool"] == "ask_student")
    question_event["args"]["question"] = "Quelle est votre série ?"
    question_event["result"]["question"] = "Quelle est votre série ?"

    def fake_run(*args, **kwargs):
        kwargs["journal"].extend(journal)
        return SimpleNamespace(
            outcome="Merci.",
            report_text=journal[-1]["result"],
        )

    monkeypatch.setattr(record_demo, "get_client", lambda: object())
    monkeypatch.setattr(record_demo, "run_cli_session", fake_run)

    with pytest.raises(ValueError, match="expected fictional question"):
        record_demo.run_fictional_sample()


def test_unexpected_fictional_question_stops_without_an_answer():
    assert record_demo.answer_fictional_question(
        "Pouvez-vous confirmer que vous êtes bien en série D, comme indiqué sur votre relevé ?"
    ) == "Oui, série D."
    assert record_demo.answer_fictional_question("Quelle est votre série ?") == ""


def test_cli_does_not_accept_an_arbitrary_journal_file():
    with pytest.raises(SystemExit):
        record_demo.build_parser().parse_args(["--journal", "untrusted.json"])


def _english_recording():
    return json.loads(
        (ROOT / "web" / "recorded-run.en.json").read_text(encoding="utf-8"))


def test_english_recording_is_a_real_run_with_an_english_recorded_report():
    events = _english_recording()["events"]
    done = events[-1]
    steps = events[:-1]
    assert done["type"] == "done" and done["status"] == "ok"
    assert done["report"].startswith("PathProof — recorded report")
    assert "## Accessibility" in done["report"] and "## Accessibilité" not in done["report"]
    assert "verif" not in done["report"].casefold()
    assert steps[-1]["tool"] == "build_report" and steps[-1]["result"] == done["report"]
    assert steps[-1]["args"]["language"] == "en"  # pinned by the loop, not by the model
    assert any(step["tool"] == "transcribe_voice" for step in steps)
    assert any(step["tool"] == "verify_report" and step["result"] == [] for step in steps)
    text = json.dumps(events)
    assert "C:\\Users" not in text and "/Users/" not in text


def test_english_recording_claims_are_written_in_english():
    events = _english_recording()["events"]
    verified = next(step for step in reversed(events[:-1])
                    if step["tool"] == "verify_report" and step["result"] == [])
    texts = [claim["text"] for claim in verified["args"]["report"]["claims"]]
    padded = [f" {text.casefold()} " for text in texts]
    assert texts and any(" you " in text or " your " in text for text in padded)
    french_words = (" est ", " vous ", " tu ", " votre ", " ton ", " ta ")  # guide names stay French
    assert not any(word in text for text in padded for word in french_words)


def test_english_question_is_accepted_only_when_it_asks_about_the_serie():
    assert record_demo.is_expected_question("Can you confirm you are in serie D?", "en")
    assert record_demo.is_expected_question("Are you in series D, as on your sheet?", "en")
    assert not record_demo.is_expected_question("What is your favourite subject?", "en")
    assert not record_demo.is_expected_question("Is your series C or D?", "en")
    assert not record_demo.is_expected_question(
        "Which series are you in? I'd like to confirm it.", "en")
    assert record_demo.answer_fictional_question("Please send a new photo.", "en") == ""
    assert record_demo.answer_fictional_question(
        "Can you confirm you are in serie D?", "en") == "Yes, serie D."


def test_recorded_report_wording_is_language_specific():
    english = ("PathProof — verified report\nSeries: D\n\n"
               "## What I could not verify\nAll the claims above are verified.")
    recorded = record_demo.make_recorded_report(english, "en")
    assert recorded.startswith("PathProof — recorded report")
    assert "## Limits of the recorded report" in recorded
    with pytest.raises(ValueError, match="must not claim verification"):
        record_demo.make_recorded_report(english + "\nverified offer", "en")


def test_record_script_offers_a_language_option():
    parser = record_demo.build_parser()
    assert parser.parse_args(["--language", "en"]).language == "en"
    assert parser.parse_args([]).language == "fr"
