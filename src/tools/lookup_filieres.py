"""Filter the guide offers accessible to a serie, then rank them (E3.5).

Access is strict and deterministic (docs/prd.md section 3.1): an offer is
accessible only when its row has Statut_qualité = OK, the serie appears in
Bac_recommandé (or the row is open to all series), and its page of the
official PDF is established. Ranking is soft and explained (section 3.2):
the metier_vise is matched as whole words against Débouchés_Métiers
and Filière (French plural s/es only: infirmier ↔ infirmiers, not
pharmacien ↔ Pharmacie and not médecin ↔ Médecine). An interest
phrase ranks on any of its content words (prepositions like « dans »
are stopwords). Then the ranking average. Remaining ties keep Offre_ID.
If the targeted job is cited on a guide row that is not recommendable
and no accessible row matches that job, ranking falls back to the
average (PRD §3.2); equal averages are then ordered by the published
Bourse figure, only on that fallback.

Returns {"accessible": [...], "excluded": [...]}: the excluded rows are
the ones open to the serie that strict access rejected, with the reason
and their Statut_qualité, for the "Ce que je n'ai pas pu vérifier"
section. No city and no admission chance is ever produced: the guide
publishes neither. Pure code: no network, no SDK.
"""

import re
import unicodedata

from src.domain.guide import NOT_PUBLISHED, OK_STATUS, load_offer_rows, load_pages_by_id
from src.domain.offer_subjects import ALL_SERIES_HEADER, STATUS_CONCOURS, subjects_for_serie
from src.tools.compute_ranking_average import compute_ranking_average

MAX_ACCESSIBLE = 5  # docs/prd.md section 3.2: the report shows at most 5 offers
CONCOURS_NOTE = "les notes du Bac ne suffisent pas"  # docs/prd.md section 3.1, Concours entry
MODE_NOT_PUBLISHED_REASON = "mode d'entrée non publié par le guide"  # dash cell, page 86/87/89
_STOPWORDS = {
    "de", "des", "du", "la", "le", "les", "en", "et", "d", "au", "aux",
    "un", "une", "dans", "pour", "avec", "sur", "par", "que", "qui", "dont",
    "mais", "pas", "plus", "moins", "comme", "son", "sa", "ses", "leur",
    "vos", "nos", "cette", "cet", "ces", "je", "tu", "il", "elle", "nous",
    "vous", "ils", "on", "mon", "ma", "mes", "ton", "ta", "tes",
    "etre", "suis", "est", "sont", "serais", "serait", "voudrais",
    "veux", "veut", "faire", "fait", "devenir", "travailler", "travaille",
    "prefere", "preferee", "metier", "peut", "etre", "aussi", "bien",
}
# Ranking weights only order the accessible offers (PRD section 3.2 lists
# metier, then interets, then the average): a metier match in the careers
# outweighs one in the program name, which outweighs a single interest.
_SCORE_METIER_DEBOUCHES = 100
_SCORE_METIER_FILIERE = 50
_SCORE_INTERET = 20
# pharmacien / Pharmacie share this prefix; marin / marine do not.
_MIN_FAMILY_PREFIX = 7


def lookup_filieres(serie: str | None = None, metier_vise: str | None = None,
                    interets: list[str] | str | None = None,
                    grades: list[dict] | None = None) -> dict:
    """Return {"accessible", "excluded"} for `serie`, ranked and explained.

    `metier_vise` and each of `interets` are phrases matched as whole
    words (accents and case ignored). When grades are given, each
    Classement offer also carries its ranking average; a Concours offer
    never does. A missing serie raises ValueError: asking, not guessing.
    """
    if not isinstance(serie, str) or not serie.strip():
        raise ValueError("serie is required: asking, not guessing")
    serie = serie.strip()
    pages = load_pages_by_id()
    accessible, excluded = [], []
    for row in load_offer_rows():
        failures = _access_failures(row, serie, pages)
        if failures:
            if _is_open_to_serie(row, serie) or _bac_is_unpublished(row):
                excluded.append(_excluded_entry(row, pages, failures))
            continue
        entry = _accessible_entry(row, serie, pages, metier_vise, interets, grades)
        if entry is not None:
            accessible.append(entry)
    if _should_rank_by_average_only(metier_vise, accessible):
        accessible = _accessible_by_average(serie, pages, grades, metier_vise)
    else:
        accessible.sort(key=lambda offer: (-offer["score"],
                                           -(offer["moyenne_classement"] or -1),
                                           offer["Offre_ID"]))
    return {"accessible": accessible[:MAX_ACCESSIBLE],
            "excluded": sorted(excluded, key=lambda offer: offer["Offre_ID"])}


def _access_failures(row: dict, serie: str, pages: dict) -> list[str]:
    failures = []
    if row.get("Statut_qualité") != OK_STATUS:
        failures.append(f"Statut_qualité = {row.get('Statut_qualité')} "
                        f"(seules les lignes {OK_STATUS} sont recommandées)")
    if row.get("Bac_recommandé", "").strip() == NOT_PUBLISHED:
        failures.append("Bac_recommandé non publié par le guide : série non vérifiable")
    elif not _is_open_to_serie(row, serie):
        failures.append(f"série {serie} absente de Bac_recommandé")
    if row.get("Offre_ID") not in pages:
        failures.append("page du guide non établie")
    return failures


def _is_open_to_serie(row: dict, serie: str) -> bool:
    values = [value.strip() for value in row.get("Bac_recommandé", "").split(",")]
    return serie in values or any(value.startswith(ALL_SERIES_HEADER) for value in values)


def _bac_is_unpublished(row: dict) -> bool:
    return row.get("Bac_recommandé", "").strip() == NOT_PUBLISHED


def _accessible_entry(row: dict, serie: str, pages: dict, metier_vise: str | None,
                      interets: list[str] | str | None, grades: list[dict] | None) -> dict | None:
    score, raisons = _ranking_reasons(row, metier_vise, interets)
    if (metier_vise or interets) and score == 0:
        return None  # no whole-word match: not a recommendation for this student
    entry = _base_entry(row, pages)
    entry["raisons"] = _access_reasons(row, serie, pages) + raisons
    entry["score"] = score
    entry.update(_average_fields(row, serie, grades, entry))
    return entry


def _average_fields(row: dict, serie: str, grades: list[dict] | None, entry: dict) -> dict:
    subjects = subjects_for_serie(row, serie)
    if subjects["status"] == STATUS_CONCOURS or row.get("Mode_entrée") == "Concours":
        entry["raisons"].append(f"Concours : {CONCOURS_NOTE}, admission par épreuve séparée")
        return {"moyenne_classement": None, "calcul": None,
                "epreuves": subjects["epreuves"]}
    if row.get("Mode_entrée", "").strip() == NOT_PUBLISHED:
        # A ranking average would imply admission by ranking, which the
        # guide does not state for these rows (dash cell, audit E3.3).
        return {"moyenne_classement": None, "calcul": None, "epreuves": [],
                "calcul_non_fait": MODE_NOT_PUBLISHED_REASON}
    if grades is None:
        return {"moyenne_classement": None, "calcul": None, "epreuves": []}
    if subjects["status"] != "calculable":
        return {"moyenne_classement": None, "calcul": None, "epreuves": [],
                "calcul_non_fait": subjects["reason"]}
    result = compute_ranking_average(serie, subjects["subjects"], grades)
    if result.get("status") != "calculé":
        return {"moyenne_classement": None, "calcul": None, "epreuves": [],
                "calcul_non_fait": result.get("reason")}
    entry["raisons"].append(
        f"moyenne de classement {result['moyenne_arrondie']} calculée sur "
        f"{', '.join(subjects['subjects'])}")
    return {"moyenne_classement": result["moyenne_arrondie"], "calcul": result,
            "epreuves": []}


def _base_entry(row: dict, pages: dict) -> dict:
    page = pages.get(row["Offre_ID"])
    return {"Offre_ID": row["Offre_ID"], "Filière": row.get("Filière", ""),
            "Établissement": row.get("Établissement", ""),
            "page_pdf": int(page) if page else None,
            "Mode_entrée": row.get("Mode_entrée", ""),
            "Bac_recommandé": row.get("Bac_recommandé", ""),
            "Statut_qualité": row.get("Statut_qualité", ""),
            "Bourse": row.get("Bourse", ""), "Aide_FPP": row.get("Aide_FPP", ""),
            "Débouchés_Métiers": row.get("Débouchés_Métiers", "")}


def _access_reasons(row: dict, serie: str, pages: dict) -> list[str]:
    raisons = [f"série {serie} dans Bac_recommandé ({row.get('Bac_recommandé')})",
               f"Statut_qualité = {OK_STATUS}",
               f"page {pages[row['Offre_ID']]} du guide officiel",
               f"Mode d'entrée : {row.get('Mode_entrée')}"]
    for champ in ("Bourse", "Aide_FPP"):
        if row.get(champ, "").strip() == NOT_PUBLISHED:
            raisons.append(f"{champ} : {NOT_PUBLISHED} par le guide")
    return raisons


def _excluded_entry(row: dict, pages: dict, failures: list[str]) -> dict:
    entry = _base_entry(row, pages)
    entry["raisons"] = failures
    return entry


def _ranking_reasons(row: dict, metier_vise: str | None,
                     interets: list[str] | str | None) -> tuple[int, list[str]]:
    score, raisons = 0, []
    if metier_vise:
        if _phrase_matches(metier_vise, row.get("Débouchés_Métiers", "")):
            score += _SCORE_METIER_DEBOUCHES
            raisons.append(f"métier visé « {metier_vise} » retrouvé comme mots entiers "
                           f"dans Débouchés_Métiers")
        if _phrase_matches(metier_vise, row.get("Filière", "")):
            score += _SCORE_METIER_FILIERE
            raisons.append(f"métier visé « {metier_vise} » retrouvé comme mots entiers "
                           f"dans Filière")
    for interet in _as_phrases(interets):
        haystack = f"{row.get('Filière', '')} {row.get('Débouchés_Métiers', '')}"
        matched = _matched_content_words(interet, haystack)
        if matched:
            score += _SCORE_INTERET
            found = ", ".join(matched)
            raisons.append(f"intérêt « {found} » (de « {interet} ») retrouvé "
                           f"comme mot entier dans Filière ou Débouchés_Métiers")
    return score, raisons


def _as_phrases(interets: list[str] | str | None) -> list[str]:
    if not interets:
        return []
    return [interets] if isinstance(interets, str) else list(interets)


def content_words(phrase: str) -> list[str]:
    """Meaningful words of `phrase` (stopwords removed, accents folded)."""
    return _content_words(phrase)


def folded_words(text: str) -> list[str]:
    """Lowercased, accent-folded tokens of `text`."""
    return _words(text)


def guide_cites_metier(metier: str) -> bool:
    """True when any guide row (any Statut_qualité) cites `metier`.

    Ranking stays on whole words. This check also treats a single-token
    job and a field name that share a long prefix as the same career
    (pharmacien / Pharmacie), so the report never says the guide is
    silent about a job it actually publishes.
    """
    if not isinstance(metier, str) or not metier.strip():
        return False
    for row in load_offer_rows():
        haystack = f"{row.get('Filière', '')} {row.get('Débouchés_Métiers', '')}"
        if _phrase_matches(metier, haystack) or _family_cites(metier, haystack):
            return True
    return False


def _should_rank_by_average_only(metier_vise: str | None, accessible: list) -> bool:
    if not metier_vise or not guide_cites_metier(metier_vise):
        return False
    return not any(_phrase_matches(metier_vise, offer.get("Filière", ""))
                   or _phrase_matches(metier_vise, offer.get("Débouchés_Métiers", ""))
                   for offer in accessible)


def _accessible_by_average(serie: str, pages: dict, grades: list[dict] | None,
                           metier_vise: str) -> list[dict]:
    accessible = []
    for row in load_offer_rows():
        if _access_failures(row, serie, pages):
            continue
        entry = _base_entry(row, pages)
        entry["raisons"] = _access_reasons(row, serie, pages) + [
            f"métier visé « {metier_vise} » cité par le guide hors ligne OK ; "
            f"classement par moyenne de classement"]
        entry["score"] = 0
        entry.update(_average_fields(row, serie, grades, entry))
        accessible.append(entry)
    # Same three BAC grades yield the same page-8 average on every
    # calculable Classement offer: Offre_ID would bury PUB-133. The
    # published Bourse figure is the remaining official number; it is
    # not used in the normal metier / interets ranking (PRD §3.2).
    accessible.sort(key=lambda offer: (-(offer["moyenne_classement"] or -1),
                                       -_published_quota(offer),
                                       offer["Offre_ID"]))
    return accessible


def _published_quota(offer: dict) -> int:
    raw = str(offer.get("Bourse") or "").strip()
    return int(raw) if raw.isdigit() else -1


def _phrase_matches(phrase: str, text: str, *, every: bool = True) -> bool:
    """True when meaningful words of `phrase` are whole words of `text`.

    Whole words only, never substrings: "pilote de ligne" needs both
    "pilote" and "ligne", so the drone operator of Foresterie Tropicale
    does not match (docs/prd.md section 3.2, case false_friend). French
    plural is s/es only ("infirmier" in "Soins infirmiers"); "pharmacien"
    is not "Pharmacie" and "médecin" is not "Médecine".
    """
    wanted = _content_words(phrase)
    if not wanted:
        return False
    stems = _text_stems(text)
    hits = (_plural_stem(word) in stems for word in wanted)
    return all(hits) if every else any(hits)


def _matched_content_words(phrase: str, text: str) -> list[str]:
    stems = _text_stems(text)
    matched = []
    for token in re.findall(r"[A-Za-zÀ-ÿ0-9]+", phrase):
        folded = _words(token)
        if folded and folded[0] not in _STOPWORDS and _plural_stem(folded[0]) in stems:
            matched.append(token)
    return matched


def _content_words(phrase: str) -> list[str]:
    return [word for word in _words(phrase) if word not in _STOPWORDS]


def _text_stems(text: str) -> set[str]:
    return {_plural_stem(word) for word in _words(text)}


def _plural_stem(word: str) -> str:
    if len(word) >= 6 and word.endswith("es"):
        return word[:-2]
    if len(word) >= 5 and word.endswith("s"):
        return word[:-1]
    return word


def _family_cites(phrase: str, text: str) -> bool:
    wanted = _content_words(phrase)
    if len(wanted) != 1 or len(wanted[0]) < _MIN_FAMILY_PREFIX:
        return False
    job = wanted[0]
    return any(_common_prefix_len(job, word) >= _MIN_FAMILY_PREFIX
               for word in _words(text))


def _common_prefix_len(left: str, right: str) -> int:
    length = 0
    for first, second in zip(left, right):
        if first != second:
            break
        length += 1
    return length


def _words(text: str) -> list[str]:
    decomposed = unicodedata.normalize("NFD", str(text).casefold())
    folded = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]+", folded)
