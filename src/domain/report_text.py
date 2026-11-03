"""Fixed sentences of the verified report, in the student's interface language.

Pure data, no network and no model: `build_report` fills these templates from
verified proofs, so a translation can never add a claim. Guide fields and
student quotes are cited as published (they stay in their original language,
inside « ... »). French is the default and the reference wording.
"""

DEFAULT_LANGUAGE = "fr"  # docs/prd.md: the student report is written for Beninese students
SUPPORTED_LANGUAGES = ("fr", "en")  # docs/decisions.md E5.6: the report follows the interface language

REPORT_TEXT: dict[str, dict[str, str]] = {
    "fr": {
        "title": "PathProof — rapport vérifié\nSérie : {serie}",
        "h_access": "## Accessibilité",
        "h_match": "## Correspondance",
        "h_quotas": "## Quotas du guide",
        "h_average": "## Moyenne de classement",
        "h_choices": "## 3 choix pour apresmonbac.bj",
        "h_unverified": "## Ce que je n'ai pas pu vérifier",
        "no_offer": "Aucune offre vérifiée pour ce profil ; aucune recommandation.",
        "fewer_than_three": "Seules {count} offres vérifiées pour ce profil ; {count} choix proposés.",
        "no_faculte": ("Aucune des offres vérifiées n'est en Faculté classique : "
                       "la page 9 du guide en demande au moins une parmi les 3 choix."),
        "concours_note": "les notes du Bac ne suffisent pas",
        "allocation_reminder": "tout changement de filière fait perdre l'allocation",
        "official_site_reminder": "apresmonbac.bj est le seul site officiel",
        "entry_not_published": "le guide ne publie pas le mode d'entrée",
        "entry_mode": "Mode d'entrée : {mode}",
        "access_line": ("- {filiere} ({etablissement}) — {offre_id}, page {page} du guide officiel — "
                        "série {serie} dans Bac_recommandé ({bac}) — {entry}"),
        "you_said": "- Tu as dit : « {quote} ».",
        "outlets_line": "- {filiere} ({offre_id}) : Débouchés « {debouches} ».",
        "no_match": "Aucun rapprochement vérifié à afficher.",
        "no_offer_quotas": "Sans offre vérifiée, aucun quota à afficher.",
        "quotas_unpublished": ("- {filiere} ({offre_id}) : le guide ne publie pas les quotas "
                               "(Bourse, Aide_FPP), page {page}."),
        "quotas_line": ("- {filiere} ({offre_id}) : {bourse} bourses et {aide} aides FPP prévues "
                        "(guide, page {page})."),
        "formula_line": ("Formule : {formula} (guide, page 8). "
                         "Coefficients : {source}, série {serie}."),
        "no_offer_average": "Sans offre vérifiée, aucune moyenne à afficher.",
        "concours_line": "- {filiere} ({offre_id}) : Concours : {note}, par épreuve séparée.",
        "average_not_computed": "- {filiere} ({offre_id}) : moyenne non calculée pour cette offre.",
        "average_line": "- {filiere} ({offre_id}) : {detail} : {result} / 20.",
        "choice_line": ("{rank}. {filiere} ({etablissement}) — {offre_id}, page {page} "
                        "(Faculté classique : {classique})"),
        "faculte_yes": "oui",
        "faculte_no": "non",
        "reminder": "Rappel : {text}.",
        "stay_free": "Tu restes libre : l'agent explique, il ne choisit pas à ta place.",
        "unverified_claim": ("- {claim_id} : affirmation non vérifiée, non retenue "
                             "(preuve {kinds})."),
        "unverified_proof_kind": "non typée",
        "unverified_quotas": "- {offre_id} : quotas non publiés par le guide (Bourse, Aide_FPP).",
        "all_verified": "Toutes les affirmations ci-dessus sont vérifiées.",
        "decimal_separator": ",",
    },
    "en": {
        "title": "PathProof — verified report\nSeries: {serie}",
        "h_access": "## Accessibility",
        "h_match": "## Match with what you said",
        "h_quotas": "## Guide quotas",
        "h_average": "## Ranking average",
        "h_choices": "## 3 choices for apresmonbac.bj",
        "h_unverified": "## What I could not verify",
        "no_offer": "No verified offer for this profile; no recommendation.",
        "fewer_than_three": "Only {count} verified offer(s) for this profile; {count} choice(s) proposed.",
        "no_faculte": ("None of the verified offers is a classic Faculty: "
                       "page 9 of the guide asks for at least one among the 3 choices."),
        "concours_note": "Bac grades alone are not enough",
        "allocation_reminder": "any change of programme loses the allocation",
        "official_site_reminder": "apresmonbac.bj is the only official site",
        "entry_not_published": "the guide does not publish the entry mode",
        "entry_mode": "Entry mode: {mode}",
        "access_line": ("- {filiere} ({etablissement}) — {offre_id}, page {page} of the official guide — "
                        "series {serie} in Bac_recommandé ({bac}) — {entry}"),
        "you_said": "- You said: « {quote} ».",
        "outlets_line": "- {filiere} ({offre_id}): Career paths « {debouches} ».",
        "no_match": "No verified match to show.",
        "no_offer_quotas": "Without a verified offer, there is no quota to show.",
        "quotas_unpublished": ("- {filiere} ({offre_id}): the guide does not publish the quotas "
                               "(Bourse, Aide_FPP), page {page}."),
        "quotas_line": ("- {filiere} ({offre_id}): {bourse} scholarships and {aide} FPP aids planned "
                        "(guide, page {page})."),
        "formula_line": ("Formula: {formula} (guide, page 8). "
                         "Coefficients: {source}, series {serie}."),
        "no_offer_average": "Without a verified offer, there is no average to show.",
        "concours_line": "- {filiere} ({offre_id}): Concours: {note}, a separate exam.",
        "average_not_computed": "- {filiere} ({offre_id}): average not computed for this offer.",
        "average_line": "- {filiere} ({offre_id}): {detail}: {result} / 20.",
        "choice_line": ("{rank}. {filiere} ({etablissement}) — {offre_id}, page {page} "
                        "(classic Faculty: {classique})"),
        "faculte_yes": "yes",
        "faculte_no": "no",
        "reminder": "Reminder: {text}.",
        "stay_free": "You stay free to choose: the agent explains, it does not choose for you.",
        "unverified_claim": ("- {claim_id}: unverified claim, not kept "
                             "(proof: {kinds})."),
        "unverified_proof_kind": "untyped",
        "unverified_quotas": "- {offre_id}: quotas not published by the guide (Bourse, Aide_FPP).",
        "all_verified": "All the claims above are verified.",
        "decimal_separator": ".",
    },
}


def report_text(language: str) -> dict[str, str]:
    """Templates of `language`; an unsupported language is an error, never French by default."""
    if language not in REPORT_TEXT:
        raise ValueError(f"unsupported report language: {language!r}")
    return REPORT_TEXT[language]
