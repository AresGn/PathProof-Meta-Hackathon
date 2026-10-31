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
    # Real key shapes only (a bare "sk-" would also match "task-by-task"):
    # long token after a known prefix, a private-key header, an assignment.
    assert not re.search(r"\b(?:sk|ghp|gho)-[A-Za-z0-9_-]{16,}", SYSTEM_PROMPT)
    assert "-----BEGIN" not in SYSTEM_PROMPT
    assert not re.search(r"MUSE_API_KEY\s*=", SYSTEM_PROMPT)
    assert "Bearer " not in SYSTEM_PROMPT


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
    assert "a grade out of the 0-20 range, a subject invalid for the serie" in PROMPT


def test_prompt_sheet_prevails_over_the_declared_average_and_serie():
    assert "the grade sheet prevails until the student provides a new photo" in PROMPT
    assert "a declared serie or declared average" in PROMPT


def test_prompt_only_recommends_offers_returned_as_accessible_by_lookup():
    assert "statut_qualité = ok" in PROMPT
    assert "only recommend offers it returns as accessible" in PROMPT
    assert "offers it returns as excluded are never recommended" in PROMPT
    assert "ce que je n'ai pas pu vérifier" in PROMPT


def test_prompt_never_promises_admission_city_or_unpublished_figures():
    # docs/prd.md section 3.5: what the report never says.
    assert "never promise admission and never give admission chances " \
        "or a probability of admission" in PROMPT
    assert "never add a city of your own" in PROMPT
    assert "never turn a value the guide does not publish into a fact or a zero" in PROMPT


def test_prompt_no_average_for_concours_offers():
    assert "for an offer whose entry mode is concours, compute no ranking average" in PROMPT
    assert "draft no claim about its epreuves" in PROMPT
    assert "les notes du bac ne suffisent pas" in PROMPT


def test_prompt_interests_rank_but_never_grant_access():
    assert "only rank the accessible offers; they never grant access" in PROMPT


def test_prompt_low_or_absent_voice_confidence_asks_to_confirm_the_serie():
    assert "if the voice transcription confidence is low or absent, " \
        "ask the student to confirm the serie" in PROMPT


def test_prompt_every_claim_carries_a_proof_and_context_is_the_tool_context():
    for proof_type in ("grade", "transcript", "filiere", "calc"):
        assert proof_type in PROMPT, proof_type
    assert "schema_version" in PROMPT
    assert "claim" in PROMPT


def test_prompt_ends_with_verify_report_then_build_report_only_when_proven():
    # Order inside the PROVE section itself, not first/last occurrences
    # anywhere in the prompt (tool names also appear in earlier sections).
    prove = PROMPT[PROMPT.index("prove, verify, then build"):]
    assert prove.index("call verify_report") < prove.index(
        "only when verify_report returns an empty list, call build_report")
    assert "only an empty problem list means fully proven" in prove


def test_prompt_on_verify_problems_fixes_or_removes_the_claim_and_never_presents_it():
    assert "fix the claim from the tool results or remove the claim, " \
        "then call verify_report again" in PROMPT
    assert "never present a refused claim as a fact" in PROMPT


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
    assert '"formula" is its "formule"' in PROMPT
    assert '"inputs" is its "details"' in PROMPT
    assert '"result" is its "moyenne_arrondie"' in PROMPT


def test_prompt_step_budget_groups_calls_and_reuses_the_lookup_calcul():
    # One step = one model turn: independent calls share the step, and an
    # average lookup_filieres already computed is never recomputed.
    assert "every tool call you emit in the same turn counts in that single step" in PROMPT
    assert "group every independent tool call in the same turn" in PROMPT
    assert 'the "calcul" that lookup_filieres already returns' in PROMPT
    assert "never recompute one lookup_filieres already gave you" in PROMPT


def test_prompt_a_grade_only_stated_by_the_student_carries_no_proof():
    assert "ask for a new photo of the sheet" in PROMPT
    assert "cannot be proved against the sheet" in PROMPT
    assert "never use it in a grade or calc proof" in PROMPT
    assert "never state a grade you did not read on a grade sheet you received" in PROMPT


def test_prompt_no_accessible_offer_drafts_only_non_offer_claims():
    assert "draft no offer claim at all, only proven non-offer claims" in PROMPT
    assert "build_report then says there is no verified offer" in PROMPT


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
