"""Report templates of src/domain/report_text.py."""
import pytest

from src.domain.report_text import REPORT_TEXT, SUPPORTED_LANGUAGES
from src.tools.build_report import build_report
from tests.test_build_report import CONTEXT


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_untyped_refused_claim_does_not_repeat_the_proof_word(language):
    text_of = REPORT_TEXT[language]
    line = text_of["unverified_claim"].format(
        claim_id="C3", kinds=text_of["unverified_proof_kind"])
    assert "proof proof" not in line and "preuve preuve" not in line


def test_no_outlet_sentence_is_defined_in_both_languages():
    assert "aucun débouché" in REPORT_TEXT["fr"]["no_outlet"].casefold()
    assert "no career path" in REPORT_TEXT["en"]["no_outlet"].casefold()


def test_english_no_offer_report_does_not_claim_medecin_is_uncited():
    report = {"schema_version": 1,
              "claims": [
                  {"claim_id": "svt-grade", "text": "SVT: 15/20 on the sheet.",
                   "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]},
                  {"claim_id": "doctor-goal",
                   "text": "You said you want to be a doctor.",
                   "proofs": [{"type": "transcript",
                               "quote": "peut-être médecin"}]},
              ]}
    english = build_report(report, CONTEXT, language="en")
    french = build_report(report, CONTEXT, language="fr")
    assert REPORT_TEXT["en"]["no_outlet"] not in english
    assert REPORT_TEXT["fr"]["no_outlet"] not in french
