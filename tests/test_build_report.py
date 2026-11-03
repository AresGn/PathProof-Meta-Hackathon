"""build_report acceptance tests (E4.2, issue #27).

Deterministic: no network, no API key. Every criterion of the issue is
checked with its proof in comment or in the test itself.
"""

import copy

import pytest

from src.domain.guide import (
    NOT_PUBLISHED,
    load_offer_rows,
    load_pages_by_id,
)
from src.tools.build_report import (
    ALLOCATION_REMINDER,
    FEWER_THAN_THREE_NOTE,
    NO_FACULTE_NOTE,
    OFFICIAL_SITE_REMINDER,
    _CITY_MARKERS,
    build_report,
)
from src.tools.compute_ranking_average import COEFFICIENT_SOURCE, FORMULA
from src.tools.verify_report import verify_report

TRANSCRIPT = "je suis en série D, peut-être médecin"
GRADES = [{"matiere": "SVT", "note": 15, "lisible": True},
          {"matiere": "Mathématiques", "note": 12, "lisible": True},
          {"matiere": "Sciences Physiques (PCT/SPCT)", "note": 12, "lisible": True}]
CALC_INPUTS = [{"matiere": "SVT", "note": 15, "coefficient": 5},
               {"matiere": "Mathématiques", "note": 12, "coefficient": 4},
               {"matiere": "Sciences Physiques (PCT/SPCT)", "note": 12, "coefficient": 4}]
CONTEXT = {"serie": "D", "grades": GRADES, "transcript": TRANSCRIPT}

ROWS_BY_ID = {row["Offre_ID"]: row for row in load_offer_rows()}
PAGES_BY_ID = load_pages_by_id()


def _filiere_proof(offre_id, champ):
    row = ROWS_BY_ID[offre_id]
    raw = row[champ]
    valeur: object = int(raw) if raw.strip().isdigit() else raw
    return {"type": "filiere", "offre_id": offre_id,
            "page_pdf": int(PAGES_BY_ID[offre_id]),
            "champ": champ, "valeur": valeur}


def _offre_claim(offre_id, with_calc=True):
    # Access is backed by verified proofs: Bac_recommandé (serie line)
    # and Mode_entrée (entry-mode line), plus the quotas when published
    # (a "non publié" field can never be a filiere proof, E3.5).
    proofs = [_filiere_proof(offre_id, "Filière"),
              _filiere_proof(offre_id, "Établissement"),
              _filiere_proof(offre_id, "Bac_recommandé")]
    row = ROWS_BY_ID[offre_id]
    if row["Mode_entrée"].strip() != NOT_PUBLISHED:
        proofs.append(_filiere_proof(offre_id, "Mode_entrée"))
    if row["Bourse"].strip() != NOT_PUBLISHED:
        proofs.append(_filiere_proof(offre_id, "Bourse"))
    if with_calc:
        proofs.append({"type": "calc", "formula": FORMULA,
                       "inputs": copy.deepcopy(CALC_INPUTS), "result": 13.15})
    return {"claim_id": f"offre-{offre_id.lower()}",
            "text": f"{row['Filière']} ({offre_id}).",
            "proofs": proofs}


def valid_report():
    return {"schema_version": 1,
            "claims": [
                {"claim_id": "svt-grade", "text": "SVT : 15/20 au relevé.",
                 "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]},
                {"claim_id": "doctor-goal",
                 "text": "Tu as dit vouloir être médecin.",
                 "proofs": [{"type": "transcript", "quote": "peut-être médecin"}]},
                _offre_claim("PUB-062"),
            ]}


def test_verified_report_renders_all_required_sections():
    # Sections: accessibilité, correspondance, quotas du guide, moyenne de
    # classement (formule et provenance), 3 choix pour apresmonbac.bj,
    # « Ce que je n'ai pas pu vérifier ». Quotas PUB-062: 95 et 20.
    report = valid_report()
    assert verify_report(report, CONTEXT) == []
    text = build_report(report, CONTEXT)
    lowered = text.casefold()
    for section in ("accessibilité", "correspondance", "quotas du guide",
                    "moyenne de classement", "3 choix pour apresmonbac.bj",
                    "ce que je n'ai pas pu vérifier"):
        assert section in lowered, section
    assert "95 bourses et 20 aides FPP prévues" in text  # guide quotas
    assert FORMULA in text  # formule page 8
    assert "page 8" in text
    assert COEFFICIENT_SOURCE in text  # provenance des coefficients
    assert "série D" in text


def test_three_choices_include_faculte_classique_and_reminders():
    # Au moins une Faculté classique (PUB-062 et PUB-133 sont oui) ;
    # rappels allocation et site officiel (PRD §3.4).
    report = valid_report()
    report["claims"].append(_offre_claim("PUB-133"))
    assert verify_report(report, CONTEXT) == []
    text = build_report(report, CONTEXT)
    assert "Faculté classique : oui" in text
    assert ALLOCATION_REMINDER in text  # tout changement de filière...
    assert OFFICIAL_SITE_REMINDER in text  # apresmonbac.bj seul site officiel


def test_choices_keep_draft_order_with_faculte_first():
    # L'ordre du brouillon (classement de l'agent) est préservé, les
    # Facultés classiques d'abord : PUB-133 (oui) devant PUB-001 (non)
    # même si le brouillon cite PUB-001 en premier.
    report = {"schema_version": 1,
              "claims": [
                  {"claim_id": "svt-grade", "text": "SVT : 15/20 au relevé.",
                   "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]},
                  _offre_claim("PUB-001", with_calc=False),
                  _offre_claim("PUB-133"),
              ]}
    assert verify_report(report, CONTEXT) == []
    text = build_report(report, CONTEXT)
    choices = text.split("## 3 choix")[1]
    assert choices.index("PUB-133") < choices.index("PUB-001")


def test_fewer_than_three_choices_says_so():
    # Moins de 3 offres = liste plus courte, signalée.
    text = build_report(valid_report(), CONTEXT)
    assert FEWER_THAN_THREE_NOTE.format(count=1) in text


def test_no_faculte_classique_warns():
    # Aucune Faculté classique (PUB-001 et PUB-002 sont non) : la
    # consigne de la page 9 est rappelée au lieu d'être tue.
    report = {"schema_version": 1,
              "claims": [
                  {"claim_id": "svt-grade", "text": "SVT : 15/20 au relevé.",
                   "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]},
                  _offre_claim("PUB-001", with_calc=False),
                  _offre_claim("PUB-002", with_calc=False),
              ]}
    assert verify_report(report, CONTEXT) == []
    text = build_report(report, CONTEXT)
    assert NO_FACULTE_NOTE in text
    assert FEWER_THAN_THREE_NOTE.format(count=2) in text


def test_raises_when_verify_reports_a_problem():
    # Lève une erreur si verify_report renvoie un problème (FR-8).
    report = valid_report()
    report["claims"][0]["proofs"][0]["note"] = 14  # note modifiée
    assert verify_report(report, CONTEXT)
    with pytest.raises(ValueError):
        build_report(report, CONTEXT)


def test_unverified_lists_refused_without_values_never_as_facts():
    # Statut unverified (#26): seules les affirmations vérifiées sont
    # présentées ; la refusée va sous « Ce que je n'ai pas pu vérifier »,
    # sans valeur attendue et jamais comme un fait.
    report = valid_report()
    report["claims"][0]["proofs"][0]["note"] = 19
    report["claims"][0]["text"] = "SVT : 19/20 au relevé."
    problems = verify_report(report, CONTEXT)
    assert [(p["claim_id"], p["type"]) for p in problems] == [("svt-grade", "grade")]
    refused = [claim for claim in report["claims"]
               if claim["claim_id"] == "svt-grade"]
    text = build_report(report, CONTEXT, refused_claims=refused)
    assert "svt-grade" in text  # listée sous non vérifié
    assert "19" not in text  # sans valeur refusée ni valeur attendue
    assert "13,15" in text  # la vérifiée reste présentée
    assert "PUB-062, page 36" in text
    # Jamais comme un fait : la refusée n'apparaît que sous non vérifié.
    verified_part = text.split("Ce que je n'ai pas pu vérifier")[0]
    assert "svt-grade" not in verified_part


def test_undeclared_problem_still_raises_in_unverified_path():
    report = valid_report()
    report["claims"][0]["proofs"][0]["note"] = 14
    assert verify_report(report, CONTEXT)
    with pytest.raises(ValueError):
        build_report(report, CONTEXT, refused_claims=[])


def test_no_admission_sentence_nor_city_in_agent_sentences():
    # Aucune phrase d'admission ni de ville dans les phrases de l'agent
    # (citations « ... » et noms du guide cités tels que publiés exclus) ;
    # les établissements des offres de test ne portent pas de ville.
    text = build_report(valid_report(), CONTEXT)
    folded = text.casefold()
    for marker in ("seras admis", "serez admis", "admis", "admission",
                   "chances", "probabilité", "probabilite"):
        assert marker not in folded, marker
    for offre_id in ("PUB-062", "PUB-133"):
        assert ROWS_BY_ID[offre_id]["Établissement"].casefold() not in ("cotonou",)
    for city in _CITY_MARKERS:
        assert city not in folded, city


def test_admission_sentence_in_draft_fails_the_report():
    report = valid_report()
    report["claims"].append(
        {"claim_id": "promesse", "text": "Tu seras admis.",
         "proofs": [{"type": "transcript", "quote": "peut-être médecin"}]})
    assert verify_report(report, CONTEXT) == []  # prouvé mais interdit
    with pytest.raises(ValueError):
        build_report(report, CONTEXT)


@pytest.mark.parametrize("promise", [
    "You have a good chance of getting in.",
    "You will likely be accepted.",
    "Your place is guaranteed.",
])
def test_english_admission_promise_fails_the_report(promise):
    report = valid_report()
    report["claims"].append(
        {"claim_id": "promise", "text": promise,
         "proofs": [{"type": "transcript", "quote": "peut-être médecin"}]})
    with pytest.raises(ValueError):
        build_report(report, CONTEXT)


def test_student_quote_with_admission_word_is_cited_not_promised():
    # Une citation de l'élève (« je veux être admis ») se cite entre
    # « ... » sans faire planter le rapport : le rapport répète ses mots,
    # il ne promet rien (revue PR #72).
    transcript = "je suis en série D, je veux être admis en médecine"
    context = {"serie": "D", "grades": GRADES, "transcript": transcript}
    report = {"schema_version": 1,
              "claims": [
                  {"claim_id": "wish",
                   "text": "Tu as dit vouloir être admis.",
                   "proofs": [{"type": "transcript",
                               "quote": "veux être admis"}]},
              ]}
    # La phrase du brouillon promet l'admission : refusée comme toute
    # phrase générée ; seule la citation serait rendable.
    with pytest.raises(ValueError):
        build_report(report, context)
    quoted = {"schema_version": 1,
              "claims": [
                  {"claim_id": "wish",
                   "text": "Tu as dit vouloir être médecin.",
                   "proofs": [{"type": "transcript",
                               "quote": "veux être admis"}]},
              ]}
    assert verify_report(quoted, context) == []
    text = build_report(quoted, context)
    assert "« veux être admis »" in text


def test_each_offer_shows_offre_id_and_page():
    # Aucune offre sans Offre_ID et sans page.
    text = build_report(valid_report(), CONTEXT)
    assert "PUB-062" in text
    assert "page 36" in text


def test_accessibility_requires_bac_and_mode_proofs():
    # La ligne « série D dans Bac_recommandé » et le mode d'entrée sont
    # adossés à des preuves filiere vérifiées, sinon le rapport refuse.
    report = {"schema_version": 1,
              "claims": [
                  {"claim_id": "offre-pub-062",
                   "text": "Médecine Générale (PUB-062).",
                   "proofs": [_filiere_proof("PUB-062", "Filière"),
                              _filiere_proof("PUB-062", "Établissement")]},
              ]}
    assert verify_report(report, CONTEXT) == []  # forme et valeurs OK...
    with pytest.raises(ValueError, match="Bac_recommandé"):  # ...mais accès non prouvé
        build_report(report, CONTEXT)


def test_offer_closed_to_serie_is_refused():
    # Une offre prouvée mais fermée à la série ne s'affiche pas : la ligne
    # « série X dans Bac_recommandé » est adossée à la preuve et revérifiée.
    report = {"schema_version": 1,
              "claims": [
                  {"claim_id": "svt-grade", "text": "SVT : 15/20 au relevé.",
                   "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]},
                  _offre_claim("PUB-062", with_calc=False),
              ]}
    assert verify_report(report, CONTEXT) == []
    context_a1 = {"serie": "A1", "grades": GRADES, "transcript": TRANSCRIPT}
    assert verify_report(report, context_a1) == []  # formes et valeurs OK...
    with pytest.raises(ValueError, match="non ouverte"):  # ...mais série fermée
        build_report(report, context_a1)


def test_calc_shared_by_two_offers_is_refused():
    # Un calcul rattaché à deux offres afficherait la même moyenne aux
    # deux : le cas ambigu est refusé (revue PR #72).
    proofs = [_filiere_proof("PUB-062", "Filière"),
              _filiere_proof("PUB-062", "Établissement"),
              _filiere_proof("PUB-062", "Bac_recommandé"),
              _filiere_proof("PUB-062", "Mode_entrée"),
              _filiere_proof("PUB-133", "Filière"),
              _filiere_proof("PUB-133", "Établissement"),
              _filiere_proof("PUB-133", "Bac_recommandé"),
              _filiere_proof("PUB-133", "Mode_entrée"),
              {"type": "calc", "formula": "M = Σ(mi·ci) / Σci",
               "inputs": copy.deepcopy(CALC_INPUTS), "result": 13.15}]
    report = {"schema_version": 1,
              "claims": [{"claim_id": "deux-offres-un-calcul",
                          "text": "Deux offres, un calcul.",
                          "proofs": proofs}]}
    assert verify_report(report, CONTEXT) == []
    with pytest.raises(ValueError):
        build_report(report, CONTEXT)


def test_no_verified_offer_says_so_instead_of_recommending():
    # FR-9 : aucune offre vérifiée → le rapport le dit, sans recommander.
    report = {"schema_version": 1,
              "claims": [
                  {"claim_id": "svt-grade", "text": "SVT : 15/20 au relevé.",
                   "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]},
                  {"claim_id": "doctor-goal",
                   "text": "Tu as dit vouloir être médecin.",
                   "proofs": [{"type": "transcript",
                               "quote": "peut-être médecin"}]},
              ]}
    assert verify_report(report, CONTEXT) == []
    text = build_report(report, CONTEXT)
    assert "Aucune offre vérifiée" in text
    # The guide cites médecin (PUB-062): do not claim the opposite.
    assert "Aucun débouché du guide ne cite ce métier." not in text
    assert "PUB-" not in text.split("## 3 choix")[1].split("Rappel")[0]


def test_no_offer_report_says_no_outlet_only_when_the_guide_is_silent():
    transcript = "je suis en série D. Mon métier préféré serait pilote de ligne."
    context = {"serie": "D", "grades": GRADES, "transcript": transcript}
    report = {"schema_version": 1,
              "claims": [
                  {"claim_id": "svt-grade", "text": "SVT : 15/20 au relevé.",
                   "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]},
                  {"claim_id": "pilot-goal",
                   "text": "Tu as dit vouloir être pilote de ligne.",
                   "proofs": [{"type": "transcript",
                               "quote": "Mon métier préféré serait pilote de ligne"}]},
              ]}
    assert verify_report(report, context) == []
    french = build_report(report, context, language="fr")
    english = build_report(report, context, language="en")
    assert "Aucun débouché du guide ne cite ce métier." in french
    assert "No career path in the guide cites this job." in english


def test_at_most_five_offers():
    # Au plus 5 offres : 6 vérifiées lèvent une erreur.
    candidates = [row["Offre_ID"] for row in load_offer_rows()
                  if row["Statut_qualité"] == "OK" and row["Offre_ID"] in PAGES_BY_ID]
    assert len(candidates) >= 6
    claims = [{"claim_id": "svt-grade", "text": "SVT : 15/20 au relevé.",
               "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]}]
    for offre_id in candidates[:6]:
        row = ROWS_BY_ID[offre_id]
        proofs = [_filiere_proof(offre_id, "Filière"),
                  _filiere_proof(offre_id, "Établissement"),
                  _filiere_proof(offre_id, "Bac_recommandé")]
        if row["Mode_entrée"].strip() != NOT_PUBLISHED:
            proofs.append(_filiere_proof(offre_id, "Mode_entrée"))
        claims.append({"claim_id": f"offre-{offre_id.lower()}",
                       "text": f"{row['Filière']} ({offre_id}).",
                       "proofs": proofs})
    report = {"schema_version": 1, "claims": claims}
    assert verify_report(report, CONTEXT) == []
    with pytest.raises(ValueError, match="au plus 5"):
        build_report(report, CONTEXT)


def test_five_offers_pass():
    candidates = [row["Offre_ID"] for row in load_offer_rows()
                  if row["Statut_qualité"] == "OK" and row["Offre_ID"] in PAGES_BY_ID]
    claims = [{"claim_id": "svt-grade", "text": "SVT : 15/20 au relevé.",
               "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]}]
    for offre_id in candidates[:5]:
        row = ROWS_BY_ID[offre_id]
        proofs = [_filiere_proof(offre_id, "Filière"),
                  _filiere_proof(offre_id, "Établissement"),
                  _filiere_proof(offre_id, "Bac_recommandé")]
        if row["Mode_entrée"].strip() != NOT_PUBLISHED:
            proofs.append(_filiere_proof(offre_id, "Mode_entrée"))
        claims.append({"claim_id": f"offre-{offre_id.lower()}",
                       "text": f"{row['Filière']} ({offre_id}).",
                       "proofs": proofs})
    report = {"schema_version": 1, "claims": claims}
    assert verify_report(report, CONTEXT) == []
    text = build_report(report, CONTEXT)
    assert "## 3 choix pour apresmonbac.bj" in text.casefold()


def test_non_published_quotas_are_said_not_affirmed():
    # PUB-211 (UADC) : Bourse non publiée (E3.5) → le rapport le dit.
    offre_id = "PUB-211"
    assert ROWS_BY_ID[offre_id]["Bourse"].strip() == NOT_PUBLISHED
    report = {"schema_version": 1,
              "claims": [
                  {"claim_id": "svt-grade", "text": "SVT : 15/20 au relevé.",
                   "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]},
                  _offre_claim(offre_id, with_calc=False),
              ]}
    assert verify_report(report, CONTEXT) == []
    text = build_report(report, CONTEXT)
    assert "le guide ne publie pas" in text.casefold()
    assert "le guide ne publie pas le mode d'entrée" in text.casefold()
    assert "PUB-211" in text
