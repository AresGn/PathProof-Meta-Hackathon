"""SYSTEM_PROMPT coverage of docs/prd.md sections 0 and 3.5 (E4.3, #28).

No network, no API key: the prompt is data, checked as data. Each test
translates one acceptance criterion of issue #28 (or one FR of the PRD
the prompt must make the model apply) into a string check, so a prompt
edit that drops a rule fails here before any manual eval replay.
"""
import re

from src.agent.prompts import SYSTEM_PROMPT

PROMPT = SYSTEM_PROMPT.casefold()


def test_prompt_has_no_forbidden_word_secret_or_real_data_marker():
    assert "chatbot" not in PROMPT
    assert "api_key" not in PROMPT
    assert "sk-" not in PROMPT
    assert "muse_api_key" not in PROMPT


def test_prompt_agent_decides_the_next_tool_step_by_step():
    assert "choose the next tool" in PROMPT
    assert "one step at a time" in PROMPT
    assert "after each" in PROMPT and "observation" in PROMPT


def test_prompt_model_never_computes_and_always_uses_the_deterministic_tool():
    assert "never compute" in PROMPT
    assert "compute_ranking_average" in PROMPT
    assert "lookup_filieres" in PROMPT


def test_prompt_asks_student_when_unreadable_missing_or_contradictory():
    assert "ask_student" in PROMPT
    for trigger in ("unreadable", "missing", "contradict"):
        assert trigger in PROMPT, trigger
    assert "never invent" in PROMPT
    assert "never guess" in PROMPT


def test_prompt_asks_when_grade_is_out_of_range_or_subject_is_invalid():
    assert "0" in PROMPT and "20" in PROMPT
    assert "out of" in PROMPT or "outside" in PROMPT
    assert "invalid" in PROMPT


def test_prompt_sheet_prevails_over_the_declared_average_and_serie():
    assert "grade sheet" in PROMPT
    assert "prevail" in PROMPT or "takes precedence" in PROMPT or "fait foi" in PROMPT
    assert "declared" in PROMPT


def test_prompt_only_recommends_offers_returned_as_accessible_by_lookup():
    assert "statut_qualité = ok" in PROMPT or "statut_qualite = ok" in PROMPT \
        or "only" in PROMPT and "accessible" in PROMPT
    assert "excluded" in PROMPT
    assert "ce que je n'ai pas pu vérifier" in PROMPT


def test_prompt_never_promises_admission_city_or_unpublished_figures():
    # docs/prd.md section 3.5: what the report never says.
    assert "admission" in PROMPT
    assert "chances" in PROMPT or "probabilit" in PROMPT
    assert "city" in PROMPT or "ville" in PROMPT
    assert "not published" in PROMPT or "ne publie pas" in PROMPT \
        or "does not publish" in PROMPT


def test_prompt_no_average_for_concours_offers():
    assert "concours" in PROMPT
    assert "not enough" in PROMPT or "ne suffisent pas" in PROMPT \
        or "separate" in PROMPT


def test_prompt_interests_rank_but_never_grant_access():
    assert "interest" in PROMPT
    assert "rank" in PROMPT
    assert "never" in PROMPT and "access" in PROMPT


def test_prompt_low_or_absent_voice_confidence_asks_to_confirm_the_serie():
    assert "confidence" in PROMPT
    assert "confirm" in PROMPT
    assert "serie" in PROMPT


def test_prompt_every_claim_carries_a_proof_and_context_is_the_tool_context():
    for proof_type in ("grade", "transcript", "filiere", "calc"):
        assert proof_type in PROMPT, proof_type
    assert "schema_version" in PROMPT
    assert "claim" in PROMPT


def test_prompt_ends_with_verify_report_then_build_report_only_when_proven():
    verify_at = PROMPT.index("verify_report")
    build_at = PROMPT.rindex("build_report")
    assert verify_at < build_at
    assert "empty" in PROMPT  # verify_report returns [] when fully proven
    assert "build_report" in PROMPT[verify_at:]


def test_prompt_on_verify_problems_fixes_or_removes_the_claim_and_never_presents_it():
    assert "remove" in PROMPT or "withdraw" in PROMPT or "retire" in PROMPT
    assert "never present" in PROMPT or "not present" in PROMPT \
        or "never as a fact" in PROMPT or "jamais" in PROMPT


def test_prompt_asks_one_question_at_a_time_in_french_and_waits():
    assert "one question at a time" in PROMPT
    assert "french" in PROMPT
    assert "wait" in PROMPT


def test_prompt_tools_are_named_exactly_as_the_loop_tools():
    for tool in ("transcribe_voice", "extract_profile", "read_grade_sheet",
                 "compute_ranking_average", "lookup_filieres", "ask_student",
                 "verify_report", "build_report"):
        assert tool in SYSTEM_PROMPT, tool
    # No tool invented by the prompt (zoom_cell was abandoned, E0.6 NO GO).
    assert "zoom_cell" not in PROMPT


def test_prompt_is_plain_instructions_without_code_or_personal_path():
    assert "```" not in SYSTEM_PROMPT
    assert not re.search(r"/home/|/Users/|C:\\", SYSTEM_PROMPT)


def test_prompt_gives_the_exact_claim_and_proof_field_names():
    for fragment in ('"claim_id"', '"proofs"', '"matiere"', '"quote"',
                     '"offre_id"', '"page_pdf"', '"champ"', '"valeur"',
                     '"formula"', '"inputs"', '"result"'):
        assert fragment in SYSTEM_PROMPT, fragment


def test_prompt_maps_compute_result_keys_to_calc_proof_keys():
    assert "moyenne_arrondie" in PROMPT
    assert '"formule"' in PROMPT or "its \"formule\"" in PROMPT
    assert '"details"' in PROMPT or "its \"details\"" in PROMPT


def test_prompt_context_grades_are_the_matieres_of_read_grade_sheet():
    assert '"matieres"' in PROMPT
    assert '"serie"' in PROMPT and '"grades"' in PROMPT and '"transcript"' in PROMPT
    assert "moyenne_affichee" in PROMPT


def test_prompt_passes_metier_and_interets_to_lookup_for_ranking():
    assert "metier_vise" in PROMPT
    assert "interets" in PROMPT


def test_prompt_requires_access_proofs_for_each_drafted_offer():
    assert "bac_recommandé" in PROMPT
    assert "mode_entrée" in PROMPT


def test_prompt_caps_the_draft_at_five_offers_and_handles_no_offer():
    assert "at most 5" in PROMPT
    assert "no accessible offer" in PROMPT
    assert "no verified offer" in PROMPT


def test_prompt_unsupported_serie_asks_and_never_reaches_lookup():
    assert "not c or d" in PROMPT


def test_prompt_text_input_replaces_the_voice_note():
    assert "text instead of a voice note" in PROMPT
    assert "skip transcribe_voice" in PROMPT
