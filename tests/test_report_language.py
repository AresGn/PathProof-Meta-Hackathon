"""The verified report and the agent follow the interface language (E5.6).

No network, no API key. `build_report` fills fixed templates from verified
proofs, so the English report carries the same facts as the French one; the
loop pins the language like it pins the verified draft.
"""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.agent import loop
from src.agent.prompts import SYSTEM_PROMPT, system_prompt_for
from src.api import server
from src.domain.report_text import REPORT_TEXT, SUPPORTED_LANGUAGES
from src.tools.build_report import build_report
from tests.fake_client import ScriptedFakeClient
from tests.test_build_report import CONTEXT, valid_report
from tests.test_loop import assistant_message, stub_verify_report, tool_call


def test_french_stays_the_default_wording():
    report = valid_report()
    assert build_report(report, CONTEXT) == build_report(report, CONTEXT, language="fr")
    assert "## Accessibilité" in build_report(report, CONTEXT)


def test_english_report_has_english_sections_and_the_same_facts():
    report = valid_report()
    french = build_report(report, CONTEXT, language="fr")
    english = build_report(report, CONTEXT, language="en")
    for heading in ("## Accessibility", "## Guide quotas", "## Ranking average",
                    "## 3 choices for apresmonbac.bj", "## What I could not verify"):
        assert heading in english, heading
    assert "95 scholarships and 20 FPP aids planned" in english
    assert "13.15" in english and "13,15" in french
    # Same offers, same guide pages: only the wording changes.
    for offre_id in ("PUB-062",):
        assert offre_id in french and offre_id in english
    assert "Série" not in english and "Accessibilité" not in english


def test_english_report_keeps_student_quotes_word_for_word():
    english = build_report(valid_report(), CONTEXT, language="en")
    assert "You said: « peut-être médecin »" in english


def test_unsupported_language_is_refused_not_defaulted():
    with pytest.raises(ValueError, match="unsupported report language"):
        build_report(valid_report(), CONTEXT, language="de")


def test_both_languages_define_the_same_templates():
    assert set(REPORT_TEXT["fr"]) == set(REPORT_TEXT["en"])
    assert set(REPORT_TEXT) == set(SUPPORTED_LANGUAGES)


def test_english_report_never_promises_admission():
    draft = valid_report()
    draft["claims"][1]["text"] = "You will be admitted to Medicine."
    with pytest.raises(ValueError, match="promises admission"):
        build_report(draft, CONTEXT, language="en")


def test_english_prompt_overrides_the_french_question_rule():
    assert system_prompt_for("fr") == SYSTEM_PROMPT
    english = system_prompt_for("en")
    assert english.startswith(SYSTEM_PROMPT)
    assert "in English" in english and "word for word" in english
    with pytest.raises(ValueError):
        system_prompt_for("de")


def test_loop_pins_the_language_on_build_report(monkeypatch):
    verified = {"schema_version": 1, "claims": [{"claim_id": "c1", "text": "ok", "proofs": []}]}
    context = {"grades": [], "serie": "D"}
    stub_verify_report(monkeypatch, [[]])
    received = {}
    monkeypatch.setitem(loop.TOOLS, "build_report",
                        lambda **kwargs: received.update(kwargs) or "Report.")
    client = ScriptedFakeClient([
        assistant_message(tool_calls=[tool_call("v", "verify_report", {"report": verified, "context": context})]),
        # The model tries to pick French: the harness decides the wording.
        assistant_message(tool_calls=[tool_call("b", "build_report", {"report": verified, "context": context, "language": "fr"})]),
        assistant_message(content="Report.")])
    loop.run(client, "fake-model", None, "Draft.", journal=[], language="en")
    assert received["language"] == "en"
    assert client.calls[0]["messages"][0]["content"] == system_prompt_for("en")


def test_language_survives_a_question_to_the_student(monkeypatch):
    client = ScriptedFakeClient([
        assistant_message(tool_calls=[tool_call("q", "ask_student", {"question": "Which serie are you in?"})]),
    ])
    suspended = loop.run(client, "fake-model", None, "Draft.", journal=[], language="en")
    assert suspended["language"] == "en"
    verified = {"schema_version": 1, "claims": []}
    stub_verify_report(monkeypatch, [[]])
    received = {}
    monkeypatch.setitem(loop.TOOLS, "build_report",
                        lambda **kwargs: received.update(kwargs) or "Report.")
    resumed = ScriptedFakeClient([
        assistant_message(tool_calls=[tool_call("v", "verify_report", {"report": verified, "context": {}})]),
        assistant_message(tool_calls=[tool_call("b", "build_report", {"report": verified, "context": {}})]),
        assistant_message(content="Report.")])
    loop.resume(resumed, "fake-model", None, suspended, "D")
    assert received["language"] == "en"


def test_run_endpoint_rejects_an_unknown_language():
    app = TestClient(server.app)
    response = app.post("/run", files={"image": ("sheet.jpg", b"fake-image", "image/jpeg")},
                        data={"text": "x", "language": "de"})
    assert response.status_code == 400


def test_run_endpoint_passes_the_language_to_the_loop(monkeypatch):
    app = TestClient(server.app)
    server.pending_run_store.clear_pending_runs()
    seen = {}

    def fake_run(client, model, schemas, user_input, journal=None, language="fr"):
        seen["language"] = language
        return "Done."

    monkeypatch.setattr(loop, "run", fake_run)
    monkeypatch.setattr(server, "get_client", lambda: SimpleNamespace())
    response = app.post("/run", files={"image": ("sheet.jpg", b"fake-image", "image/jpeg")},
                        data={"text": "x", "language": "en"})
    assert response.status_code == 200
    assert json.loads(response.text.split("data:")[-1].strip())["type"] == "done"
    assert seen["language"] == "en"
