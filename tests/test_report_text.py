"""Report templates of src/domain/report_text.py."""
import pytest

from src.domain.report_text import REPORT_TEXT, SUPPORTED_LANGUAGES


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_untyped_refused_claim_does_not_repeat_the_proof_word(language):
    text_of = REPORT_TEXT[language]
    line = text_of["unverified_claim"].format(
        claim_id="C3", kinds=text_of["unverified_proof_kind"])
    assert "proof proof" not in line and "preuve preuve" not in line
