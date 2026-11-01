"""Demo web interface: one-click samples, clickable proofs, safety (E5.2, issue #31).

No network, no API key: the sample files are fictional and served read-only;
the interface files are checked as text, like test_no_501_stub_left does for
the server. A full browser run is manual (it consumes API credits).
"""
from pathlib import Path

from fastapi.testclient import TestClient

from src.api import server

ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
APP_JS = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
SAMPLE_NAMES = (
    "releve_serie_d.jpg",
    "releve_serie_c.jpg",
    "releve_serie_d_flou.jpg",
    "note_vocale_coherente.mp3",
    "note_vocale_contradictoire.mp3",
)


def test_samples_are_served_read_only():
    app = TestClient(server.app)
    for name in SAMPLE_NAMES:
        response = app.get(f"/samples/{name}")
        assert response.status_code == 200, name
        assert len(response.content) > 1000, name


def test_samples_reject_unknown_names_and_traversal():
    app = TestClient(server.app)
    assert app.get("/samples/README.md").status_code == 404
    assert app.get("/samples/unknown.jpg").status_code == 404
    assert app.get("/samples/..%2fserver.py").status_code == 404


def test_interface_offers_the_three_one_click_examples():
    # releve D + voix coherente, releve flou, voix contradictoire (issue #31).
    for name in ("releve_serie_d.jpg", "note_vocale_coherente.mp3",
                 "releve_serie_d_flou.jpg", "note_vocale_contradictoire.mp3"):
        assert name in APP_JS, name
    assert "/samples/" in APP_JS
    assert INDEX_HTML.count("data-example") >= 3


def test_interface_forbidden_word_is_absent():
    assert "chatbot" not in INDEX_HTML.casefold()
    assert "chatbot" not in APP_JS.casefold()


def test_interface_is_readable_at_375_px():
    assert 'name="viewport"' in INDEX_HTML
    assert "@media" in INDEX_HTML and "480px" in INDEX_HTML


def test_interface_keeps_photo_voice_text_question_and_live_steps():
    for element_id in ("photo", "voice", "fallback-text", "steps",
                       "question", "answer-input", "report"):
        assert f'id="{element_id}"' in INDEX_HTML, element_id
    for event_type in ('"step"', '"needs_input"', '"done"', '"error"'):
        assert event_type in APP_JS, event_type


def test_report_proofs_are_clickable_and_open_their_source():
    assert 'id="proof-dialog"' in INDEX_HTML
    for proof_type in ("grade", "transcript", "filiere", "calc"):
        assert f'"{proof_type}"' in APP_JS, proof_type
    # The source of a filiere proof is its guide row: Offre_ID and guide page.
    assert "Offre_ID" in APP_JS and "page" in APP_JS
    # The verified claims come from the streamed verify_report step.
    assert "verify_report" in APP_JS


def test_displayed_content_is_escaped():
    assert "escapeHtml" in APP_JS
    # Report and proof sources are written as text, never as raw markup.
    assert "textContent" in APP_JS
