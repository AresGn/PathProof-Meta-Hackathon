"""Demo web interface: one-click samples, clickable proofs, safety (E5.2, issue #31).

No network, no API key: the sample files are fictional and served read-only;
the interface files are checked as text, like test_no_501_stub_left does for
the server. A full browser run is manual (it consumes API credits).
"""
from pathlib import Path
import re

from fastapi.testclient import TestClient

from src.api import server

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
INDEX_HTML = (WEB_DIR / "index.html").read_text(encoding="utf-8")
STYLES_CSS = (WEB_DIR / "styles.css").read_text(encoding="utf-8")
JS_MODULES = ("i18n.js", "format.js", "api.js", "steps.js", "agent-map.js", "motion.js",
              "proofs.js", "report.js", "app.js")
APP_JS = "\n".join((WEB_DIR / "js" / name).read_text(encoding="utf-8") for name in JS_MODULES)
MODULES = {
    name: (WEB_DIR / "js" / name).read_text(encoding="utf-8")
    for name in JS_MODULES
}
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
    assert "@media" in STYLES_CSS and "480px" in STYLES_CSS


def test_interface_keeps_photo_voice_text_question_and_live_steps():
    for element_id in ("photo", "voice", "fallback-text", "steps",
                       "question", "answer-input", "report"):
        assert f'id="{element_id}"' in INDEX_HTML, element_id
    for event_type in ('"step"', '"needs_input"', '"done"', '"error"'):
        assert event_type in APP_JS, event_type


def test_report_proofs_are_clickable_and_open_their_source():
    assert 'id="proof-dialog"' in INDEX_HTML
    for proof_type in ("grade", "transcript", "filiere", "calc"):
        assert f'proof.type === "{proof_type}"' in MODULES["proofs.js"], proof_type
    assert 'row.Offre_ID === offreId' in MODULES["proofs.js"]
    assert '[t("fieldPage"), proof.page_pdf]' in MODULES["proofs.js"]
    # The verified claims come from the streamed verify_report step.
    assert "step.tool !== \"verify_report\"" in MODULES["proofs.js"]


def test_displayed_content_is_escaped():
    assert re.search(r"replace\(\s*/\[&<>\"'\]/", MODULES["format.js"])
    assert "head.textContent = label" in MODULES["proofs.js"]
    assert "cell.textContent = value" in MODULES["proofs.js"]
    assert "text.textContent = claim.text || \"\"" in MODULES["report.js"]
    assert "escapeHtml(formatDetail(step.args))" in MODULES["steps.js"]


def test_health_endpoint_reports_the_demo_server():
    app = TestClient(server.app)
    response = app.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "pathproof-demo"}


def test_server_errors_are_never_shown_empty():
    # A non-OK response without a readable detail still names its HTTP status.
    assert "status: `${response.status}" in MODULES["api.js"]
    assert 'fetch(`${base}/health`)' in MODULES["api.js"]


def test_page_finds_the_local_api_when_served_statically():
    # Opened via Live Server (127.0.0.1:5500) or a file, the page must still
    # reach the uvicorn API instead of calling the static server.
    assert 'const LOCAL_API_BASE = "http://127.0.0.1:8000"' in MODULES["api.js"]
    assert "apiBase = await probeApiBase(LOCAL_API_BASE)" in MODULES["api.js"]


def test_frontend_files_are_split_by_responsibility():
    # Markup, styles and one module per concern (SRP): no monolith left.
    assert "<style>" not in INDEX_HTML
    assert 'href="styles.css"' in INDEX_HTML
    assert 'type="module" src="js/app.js"' in INDEX_HTML
    assert not (WEB_DIR / "app.js").exists()
    for name in JS_MODULES:
        assert (WEB_DIR / "js" / name).is_file(), name
    entry = (WEB_DIR / "js" / "app.js").read_text(encoding="utf-8")
    for module in ("i18n", "api", "steps", "proofs", "report"):
        assert f'from "./{module}.js"' in entry, module


def test_interface_is_english_by_default_with_french_toggle():
    # Anglophone jury: English first, French one click away (docs/decisions.md).
    assert '<html lang="en">' in INDEX_HTML
    assert 'data-set-lang="en"' in INDEX_HTML
    assert 'data-set-lang="fr"' in INDEX_HTML
    assert 'statusDone: "Run complete."' in MODULES["i18n.js"]
    assert 'statusDone: "Exécution terminée."' in MODULES["i18n.js"]
    assert 'const STORAGE_KEY = "pathproof-lang"' in MODULES["i18n.js"]


def test_hidden_verified_banner_stays_hidden_despite_display_rule():
    assert re.search(
        r"#verified-banner\[hidden\]\s*\{\s*display:\s*none\s*!important;\s*\}",
        STYLES_CSS,
    )
    report = MODULES["report.js"]
    assert "view.banner.hidden = !isVerified" in report
    assert "if (isVerified) renderClaims(view, claims, openProof)" in report
    app = MODULES["app.js"]
    assert "showReport(event.report, true)" in app
    assert "showReport(event.report || null, false)" in app


def test_blocked_local_storage_does_not_prevent_language_module_loading():
    i18n = MODULES["i18n.js"]
    assert "function readStoredLanguage()" in i18n
    assert "function storeLanguage(language)" in i18n
    assert "!isStorageUnavailable(error)" in i18n
    assert "let currentLanguage = readStoredLanguage() === \"fr\" ? \"fr\" : \"en\"" in i18n
    assert "storeLanguage(currentLanguage)" in i18n
    assert i18n.count("window.localStorage.getItem(STORAGE_KEY)") == 1
    assert i18n.count("window.localStorage.setItem(STORAGE_KEY") == 1


def test_full_local_storage_does_not_break_language_switch():
    i18n = MODULES["i18n.js"]
    assert '"QuotaExceededError"' in i18n
    assert "function isStorageUnavailable(error)" in i18n


def test_answer_stream_locks_new_runs_until_the_answer_finishes():
    answer_handler = MODULES["app.js"].split(
        'answerBtn.addEventListener("click"', 1
    )[1]
    assert "setRunBusy(true)" in answer_handler
    assert re.search(r"finally\s*\{\s*setRunBusy\(false\)", answer_handler)
    assert "await streamAnswer(currentRunId, answer.trim(), handleEvent)" in answer_handler


def test_expired_answer_session_restores_trace_and_closes_retry_controls():
    app = MODULES["app.js"]
    answer_handler = app.split('answerBtn.addEventListener("click"', 1)[1]
    expired_session = answer_handler.split("if (err?.status === 404)", 1)[1].split(
        "} else if", 1
    )[0]
    assert "restoreAnswerState(retryState)" in expired_session
    assert "closeSession()" in expired_session
    assert "retrySuffix" not in expired_session
    assert "lastRunRecorded" not in app
    assert "lastRecordedError" not in app
    assert "recordedRetryState" not in app


def test_proof_sources_come_from_the_accepted_verifier_context():
    proofs = MODULES["proofs.js"]
    assert "export function verifiedContext(steps)" in proofs
    assert "step.tool !== \"verify_report\"" in proofs
    assert "step.result.length !== 0" in proofs
    assert "step.args.context" in proofs
    assert "getVerifiedContext" in proofs
    assert "context.transcript" in proofs
    assert "context.grades" in proofs
    assert "lastStep(steps, \"read_grade_sheet\")" not in proofs
    assert "lastStep(steps, \"transcribe_voice\")" not in proofs


def test_filiere_proof_finds_any_lookup_result_or_states_that_source_is_missing():
    proofs = MODULES["proofs.js"]
    assert "steps.filter((step) => step.tool === \"lookup_filieres\")" in proofs
    assert "t(\"guideRowUnavailable\")" in proofs
    assert "guideRowUnavailable:" in MODULES["i18n.js"]


def test_calculation_proof_uses_exact_decimal_sums_and_rounded_display():
    proofs = MODULES["proofs.js"]
    format_module = MODULES["format.js"]
    assert "BigInt" in format_module
    assert "formatCalculationNumber(weighted.products[index], weighted.scale)" in proofs
    assert "formatCalculationNumber(weighted.total, weighted.scale)" in proofs
    assert "Number(entry.note) * Number(entry.coefficient)" not in proofs
    assert "t(\"calcUnavailable\")" in proofs
    assert "Number.isFinite(value)" in format_module
    assert "Number.isSafeInteger(coefficient)" in format_module
    assert 'calcUnavailable: "Calculation details are unavailable' in MODULES["i18n.js"]


def test_api_health_probe_can_retry_after_the_server_becomes_available():
    api = MODULES["api.js"]
    assert "const currentPromise = apiBasePromise" in api
    assert "if (!result && apiBasePromise === currentPromise)" in api
    assert "apiBasePromise = null" in api


def test_live_trace_appends_new_cards_and_preserves_open_details():
    steps = MODULES["steps.js"]
    assert "timeline.children[sharedCount].sourceStep === steps[sharedCount]" in steps
    assert "timeline.appendChild(renderStep(steps[index]))" in steps
    assert "timeline.removeChild(timeline.lastElementChild)" in steps
    assert "export function renderSteps(container, steps, busy, force = false)" in steps


def test_backlog_names_the_split_frontend_files():
    backlog = (ROOT / "docs" / "backlog.md").read_text(encoding="utf-8")
    assert "`web/js/`" in backlog
    assert "`web/styles.css`" in backlog
    assert "`web/app.js`" not in backlog


def test_recorded_run_is_served_as_a_fictional_successful_execution():
    response = TestClient(server.app).get("/recorded-run.json")
    assert response.status_code == 200
    recording = response.json()
    events = recording["events"]
    steps = [event for event in events if event["type"] == "step"]
    done = events[-1]
    assert steps
    assert done["type"] == "done"
    assert done["status"] == "ok"
    assert done["report"]
    assert any(step["tool"] == "verify_report" and step["result"] == []
               for step in steps)
    assert any(step["tool"] == "transcribe_voice" for step in steps)
    assert any(step["tool"] == "read_grade_sheet" for step in steps)
    assert "C:\\Users\\" not in response.text
    assert "/Users/" not in response.text


def test_recorded_run_fallback_is_explicit_in_both_languages():
    app = MODULES["app.js"]
    i18n = MODULES["i18n.js"]
    assert 'id="recorded-banner"' in INDEX_HTML
    assert 'data-i18n="recordedRun"' in INDEX_HTML
    assert "exécution enregistrée" in i18n.casefold()
    assert "Recorded execution" in i18n
    assert "fetchRecordedRun" in app
    assert "showRecordedRun" in app
    assert "recordedBanner.hidden = false" in app


def test_live_agent_map_lists_every_tool_and_never_claims_a_running_tool():
    agent_map = MODULES["agent-map.js"]
    for tool in ("transcribe_voice", "read_grade_sheet", "extract_profile", "ask_student",
                 "compute_ranking_average", "lookup_filieres", "verify_report", "build_report"):
        assert f'"{tool}"' in agent_map, tool
    # Steps are streamed after execution: the map shows answered tools only.
    assert "is-done" in agent_map and "is-flash" in agent_map
    assert 'id="agent-map"' in INDEX_HTML
    assert "agentMap.update(seenSteps" in MODULES["app.js"]


def test_interface_layout_is_responsive_and_respects_reduced_motion():
    assert "@media (min-width: 960px)" in STYLES_CSS
    assert "@media (min-width: 640px)" in STYLES_CSS
    assert "prefers-reduced-motion: reduce" in STYLES_CSS
    assert "prefers-reduced-motion" in MODULES["motion.js"]
