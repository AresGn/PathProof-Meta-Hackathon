"""Format the verified report for the student (E4.2, issue #27).

Deterministic: no model call, no network. The input is the draft report
JSON (proofs `grade`, `transcript`, `filiere`, `calc`) plus the verifier
context {"serie", "grades", "transcript"}. Every rendered line comes from a
verified claim or from the guide rows its filiere proofs point to.

Verified path (`refused_claims` is None): `verify_report` must return no
problem, otherwise ValueError is raised and nothing is rendered (FR-8).

Unverified path (loop stopped after 3 refusals, #26): `refused_claims`
are the claims of the last draft the verifier refused (loop contract:
matched by `claim_id`, None ignored). Only the verified claims are
presented; each refused claim is listed under "Ce que je n'ai pas pu
vérifier" by its `claim_id` and proof types, never with its values and
never as a fact. A problem on a claim not declared refused also raises.

Sections (docs/prd.md sections 3.3 and 3.4): accessibilité,
correspondance, quotas du guide, moyenne de classement (formula and
provenance), 3 choix pour apresmonbac.bj (at least one Faculte
classique, with the allocation and official-site reminders), and
"Ce que je n'ai pas pu vérifier". At most 5 offers; every offer shows
its Offre_ID and its guide page, with a verified `Bac_recommandé` proof
backing the serie line and a verified `Mode_entrée` proof backing the
entry-mode line; with no verified offer the report says so instead of
recommending (FR-9). A claim carrying a `calc` proof must reference
exactly one offer with exactly one calc (an ambiguous grouping is
refused instead of showing one average for two offers).

Admission promises are refused in the agent's own sentences (verified
claim texts and fixed templates, quotes stripped): a student citation
such as "je veux être admis" stays quotable inside « ... » because the
report repeats the student's words without promising anything, and
guide fields are cited as published (the offers CSV carries none of the
forbidden words). Places follow the same rule: the agent never adds a
place name; an Établissement cited as published may carry its town
(e.g. "Ecole Normale Supérieure /Porto-Novo") and a student quote
repeats the student's own words, so the no-city acceptance check
applies to the agent's sentences (tested on safe offers), never to a
quoted name the report did not invent.
"""

import re

from src.domain.guide import (
    NOT_PUBLISHED,
    OK_STATUS,
    load_faculte_classique_by_id,
    load_offer_rows,
    load_pages_by_id,
)
from src.domain.offer_subjects import ALL_SERIES_HEADER
from src.domain.report_text import DEFAULT_LANGUAGE, REPORT_TEXT, report_text
from src.tools.compute_ranking_average import COEFFICIENT_SOURCE, FORMULA
from src.tools.verify_report import verify_report

MAX_OFFERS = 5  # docs/prd.md section 3.2: the report shows at most 5 offers
# French reference wording (docs/prd.md sections 3.1 and 3.3); the English
# wording lives next to it in src/domain/report_text.py.
CONCOURS_NOTE = REPORT_TEXT["fr"]["concours_note"]
ALLOCATION_REMINDER = REPORT_TEXT["fr"]["allocation_reminder"]
OFFICIAL_SITE_REMINDER = REPORT_TEXT["fr"]["official_site_reminder"]
NO_OFFER_MESSAGE = REPORT_TEXT["fr"]["no_offer"]
FEWER_THAN_THREE_NOTE = REPORT_TEXT["fr"]["fewer_than_three"]
NO_FACULTE_NOTE = REPORT_TEXT["fr"]["no_faculte"]

# Admission promises never reach the student: "admis" also covers
# "admission". "chances" is plural on purpose so "changement" stays
# allowed. Checked on the agent's own sentences (claim texts and fixed
# templates with « ... » citations stripped), never on a student quote
# or a guide field cited as published.
_FORBIDDEN_SUBSTRINGS = (
    "seras admis",
    "serez admis",
    "seras admise",
    "serez admise",
    "admis",
    "admission",
    "chances",
    "probabilité",
    "probabilite",
    "admitted",
    "probability",
    "chance",
    "likely",
    "accepted",
    "guarantee",
)

# Places the agent never writes itself (acceptance check on safe offers).
# Guide Établissement values and student quotes are cited as published,
# so they are excluded from the check by stripping « ... » spans.
_CITY_MARKERS = (
    "cotonou",
    "porto-novo",
    "porto novo",
    "parakou",
    "abomey-calavi",
    "abomey",
    "bohicon",
    "natitingou",
    "djougou",
    "lokossa",
    "kandi",
    "ouidah",
    "calavi",
)

_QUOTED_SPAN = re.compile("«.*?»", re.DOTALL)


def build_report(report: dict, context: dict,
                 refused_claims: list | None = None,
                 language: str = DEFAULT_LANGUAGE) -> str:
    """Render the verified report text; raise when a proof is missing.

    `refused_claims` is the loop `unverified` contract (#26): the refused
    claims of the last draft, as dicts with `claim_id` (plain ids are
    accepted too). None means the fully verified path. `language` ("fr" or
    "en") only chooses the wording of the fixed sentences; an unsupported
    language raises instead of falling back.
    """
    text_of = report_text(language)
    problems = verify_report(report, context)
    if refused_claims is None:
        if problems:
            raise ValueError(_refusal_summary(problems))
        verified = _report_claims(report)
        refused_ids: set[str] = set()
    else:
        refused_ids = _refused_ids(refused_claims)
        _raise_on_undeclared(problems, refused_ids)
        verified = [claim for claim in _report_claims(report)
                    if claim.get("claim_id") not in refused_ids]
    for claim in verified:
        text_value = claim.get("text") if isinstance(claim, dict) else None
        if isinstance(text_value, str) and _contains_forbidden(text_value):
            raise ValueError(
                f"report promises admission: {claim.get('claim_id')!r}")
    by_type = _problems_by_claim(problems)
    text = _render(verified, context, refused_ids, by_type, text_of)
    _assert_no_forbidden_admission(_strip_quoted(text))
    return text


def _report_claims(report: object) -> list[dict]:
    if not isinstance(report, dict) or not isinstance(report.get("claims"), list):
        raise ValueError("report has no usable claims: asking, not guessing")
    return report["claims"]


def _refused_ids(refused_claims: list) -> set[str]:
    if not isinstance(refused_claims, list):
        raise ValueError("refused_claims must be a list of claims or ids")
    ids = set()
    for entry in refused_claims:
        if isinstance(entry, dict):
            claim_id = entry.get("claim_id")
        else:
            claim_id = entry
        if isinstance(claim_id, str) and claim_id.strip():
            ids.add(claim_id)
    return ids


def _raise_on_undeclared(problems: list, refused_ids: set[str]) -> None:
    for problem in problems:
        claim_id = problem.get("claim_id") if isinstance(problem, dict) else None
        if not isinstance(claim_id, str) or claim_id not in refused_ids:
            raise ValueError(_refusal_summary(problems))


def _refusal_summary(problems: list) -> str:
    parts = []
    for problem in problems:
        if not isinstance(problem, dict):
            continue
        parts.append(f"{problem.get('claim_id')}:{problem.get('type')}")
    detail = ", ".join(parts) if parts else "unverified report"
    return f"unverified report, {len(problems)} problem(s): {detail}"


def _problems_by_claim(problems: list) -> dict[str, list[str]]:
    by_claim: dict[str, list[str]] = {}
    for problem in problems:
        if not isinstance(problem, dict):
            continue
        claim_id = problem.get("claim_id")
        if isinstance(claim_id, str) and claim_id:
            by_claim.setdefault(claim_id, []).append(str(problem.get("type")))
    return by_claim


def _render(verified: list[dict], context: object,
            refused_ids: set[str], by_type: dict[str, list[str]],
            text_of: dict[str, str]) -> str:
    serie = _context_serie(context)
    rows = {row["Offre_ID"]: row for row in load_offer_rows()}
    pages = load_pages_by_id()
    faculte = load_faculte_classique_by_id()
    offre_ids = _verified_offre_ids(verified, rows, pages)
    proven = _proven_champs(verified)
    _require_access_proofs(offre_ids, proven, rows, serie)
    sections = [
        text_of["title"].format(serie=serie),
        _accessibility_section(offre_ids, rows, pages, serie, text_of),
        _correspondance_section(verified, offre_ids, rows, text_of),
        _quotas_section(offre_ids, rows, pages, text_of),
        _average_section(verified, offre_ids, rows, pages, serie, text_of),
        _choices_section(offre_ids, rows, pages, faculte, text_of),
        _unverified_section(refused_ids, by_type, offre_ids, rows, text_of),
    ]
    return "\n\n".join(sections)


def _context_serie(context: object) -> str:
    if isinstance(context, dict) and isinstance(context.get("serie"), str):
        serie = context["serie"].strip()
        if serie:
            return serie
    raise ValueError("context serie is missing: asking, not guessing")


def _verified_offre_ids(verified: list[dict], rows: dict, pages: dict) -> list[str]:
    offre_ids: list[str] = []
    for claim in verified:
        if not isinstance(claim, dict):
            continue
        for proof in claim.get("proofs", []):
            if not isinstance(proof, dict) or proof.get("type") != "filiere":
                continue
            offre_id = proof.get("offre_id")
            if not isinstance(offre_id, str) or not offre_id.strip():
                raise ValueError("offre sans Offre_ID: asking, not guessing")
            if offre_id not in offre_ids:
                offre_ids.append(offre_id)
    if len(offre_ids) > MAX_OFFERS:
        raise ValueError(f"au plus {MAX_OFFERS} offres, {len(offre_ids)} vérifiées")
    for offre_id in offre_ids:
        row = rows.get(offre_id)
        if row is None or row.get("Statut_qualité") != OK_STATUS:
            raise ValueError(f"offre {offre_id} sans ligne {OK_STATUS}: asking, not guessing")
        if offre_id not in pages:
            raise ValueError(f"offre {offre_id} sans page: asking, not guessing")
    return offre_ids


def _proven_champs(verified: list[dict]) -> dict[str, set[str]]:
    """Verified filiere champs per offer, backing the access lines."""
    proven: dict[str, set[str]] = {}
    for claim in verified:
        if not isinstance(claim, dict):
            continue
        for proof in claim.get("proofs", []):
            if not isinstance(proof, dict) or proof.get("type") != "filiere":
                continue
            offre_id = proof.get("offre_id")
            champ = proof.get("champ")
            if isinstance(offre_id, str) and isinstance(champ, str):
                proven.setdefault(offre_id, set()).add(champ)
    return proven


def _require_access_proofs(offre_ids: list[str], proven: dict[str, set[str]],
                           rows: dict, serie: str) -> None:
    """Refuse an access line the draft never proved (serie, entry mode).

    The serie line is backed by a verified `Bac_recommandé` proof and the
    serie must appear in it (same open-to-serie rule as `lookup_filieres`);
    the entry-mode line needs a verified `Mode_entrée` proof, unless the
    guide does not publish the mode (then no filiere proof can exist and
    the report says so instead).
    """
    for offre_id in offre_ids:
        champs = proven.get(offre_id, set())
        if "Bac_recommandé" not in champs:
            raise ValueError(
                f"offre {offre_id} sans preuve Bac_recommandé: asking, not guessing")
        row = rows[offre_id]
        if row.get("Mode_entrée", "").strip() != NOT_PUBLISHED \
                and "Mode_entrée" not in champs:
            raise ValueError(
                f"offre {offre_id} sans preuve Mode_entrée: asking, not guessing")
        values = [value.strip() for value in row.get("Bac_recommandé", "").split(",")]
        if serie not in values \
                and not any(value.startswith(ALL_SERIES_HEADER) for value in values):
            raise ValueError(
                f"offre {offre_id} non ouverte à la série {serie}: asking, not guessing")


def _accessibility_section(offre_ids: list[str], rows: dict, pages: dict,
                           serie: str, text_of: dict[str, str]) -> str:
    lines = [text_of["h_access"]]
    if not offre_ids:
        return "\n".join([*lines, text_of["no_offer"]])
    for offre_id in offre_ids:
        row = rows[offre_id]
        if row.get("Mode_entrée", "").strip() == NOT_PUBLISHED:
            entry_mode = text_of["entry_not_published"]
        else:
            entry_mode = text_of["entry_mode"].format(mode=row.get("Mode_entrée", ""))
        lines.append(text_of["access_line"].format(
            filiere=row.get("Filière", ""), etablissement=row.get("Établissement", ""),
            offre_id=offre_id, page=pages.get(offre_id), serie=serie,
            bac=row.get("Bac_recommandé", ""), entry=entry_mode))
    return "\n".join(lines)


def _correspondance_section(verified: list[dict], offre_ids: list[str], rows: dict,
                            text_of: dict[str, str]) -> str:
    lines = [text_of["h_match"]]
    quotes = []
    for claim in verified:
        if not isinstance(claim, dict):
            continue
        for proof in claim.get("proofs", []):
            if isinstance(proof, dict) and proof.get("type") == "transcript":
                quote = proof.get("quote")
                if isinstance(quote, str) and quote.strip() and quote not in quotes:
                    quotes.append(quote)
    for quote in quotes:
        lines.append(text_of["you_said"].format(quote=quote))
    for offre_id in offre_ids:
        row = rows[offre_id]
        lines.append(text_of["outlets_line"].format(
            filiere=row.get("Filière", ""), offre_id=offre_id,
            debouches=row.get("Débouchés_Métiers", "")))
    if len(lines) == 1:
        lines.append(text_of["no_match"])
    return "\n".join(lines)


def _quotas_section(offre_ids: list[str], rows: dict, pages: dict,
                    text_of: dict[str, str]) -> str:
    lines = [text_of["h_quotas"]]
    if not offre_ids:
        return "\n".join([*lines, text_of["no_offer_quotas"]])
    for offre_id in offre_ids:
        row = rows[offre_id]
        bourse = (row.get("Bourse") or "").strip()
        aide = (row.get("Aide_FPP") or "").strip()
        page = pages.get(offre_id)
        if bourse == NOT_PUBLISHED or aide == NOT_PUBLISHED:
            lines.append(text_of["quotas_unpublished"].format(
                filiere=row.get("Filière", ""), offre_id=offre_id, page=page))
        else:
            lines.append(text_of["quotas_line"].format(
                filiere=row.get("Filière", ""), offre_id=offre_id,
                bourse=bourse, aide=aide, page=page))
    return "\n".join(lines)


def _average_section(verified: list[dict], offre_ids: list[str],
                     rows: dict, pages: dict, serie: str,
                     text_of: dict[str, str]) -> str:
    lines = [text_of["h_average"],
             text_of["formula_line"].format(formula=FORMULA, source=COEFFICIENT_SOURCE,
                                            serie=serie)]
    if not offre_ids:
        return "\n".join([*lines, text_of["no_offer_average"]])
    calc_by_offre = _calc_by_offre(verified)
    separator = text_of["decimal_separator"]
    for offre_id in offre_ids:
        row = rows[offre_id]
        filiere = row.get("Filière", "")
        calc = calc_by_offre.get(offre_id)
        if calc is None:
            if row.get("Mode_entrée") == "Concours":
                lines.append(text_of["concours_line"].format(
                    filiere=filiere, offre_id=offre_id, note=text_of["concours_note"]))
            else:
                lines.append(text_of["average_not_computed"].format(
                    filiere=filiere, offre_id=offre_id))
            continue
        try:
            detail = ", ".join(f"{entry['matiere']} {_format_number(entry['note'], separator)} "
                                f"× {entry['coefficient']}"
                                for entry in calc["inputs"])
            result = _format_number(calc["result"], separator)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                f"calc proof of {offre_id} is unusable: asking, not guessing") from error
        lines.append(text_of["average_line"].format(
            filiere=filiere, offre_id=offre_id, detail=detail, result=result))
    return "\n".join(lines)


def _calc_by_offre(verified: list[dict]) -> dict[str, dict]:
    """Verified calc proof of each offer; ambiguous groupings are refused.

    A claim carrying a calc must reference exactly one offer with exactly
    one calc: with two offers and a single calc the same average would
    otherwise show for both.
    """
    calc_by_offre: dict[str, dict] = {}
    for claim in verified:
        if not isinstance(claim, dict):
            continue
        proofs = claim.get("proofs", [])
        if not isinstance(proofs, list):
            continue
        filiere_ids = [proof.get("offre_id") for proof in proofs
                       if isinstance(proof, dict) and proof.get("type") == "filiere"
                       and isinstance(proof.get("offre_id"), str)]
        calcs = [proof for proof in proofs
                 if isinstance(proof, dict) and proof.get("type") == "calc"]
        if not calcs:
            continue
        if len(set(filiere_ids)) != 1 or len(calcs) != 1:
            raise ValueError(
                f"claim {claim.get('claim_id')!r} links one calc to "
                f"{len(set(filiere_ids))} offer(s): asking, not guessing")
        offre_id = filiere_ids[0]
        if offre_id not in calc_by_offre:
            calc_by_offre[offre_id] = calcs[0]
    return calc_by_offre


def _choices_section(offre_ids: list[str], rows: dict, pages: dict, faculte: dict,
                     text_of: dict[str, str]) -> str:
    lines = [text_of["h_choices"]]
    if not offre_ids:
        lines.append(text_of["no_offer"])
    else:
        # Draft order first (the agent's ranking), Faculte classique first
        # within it so the page-9 consigne is met whenever possible.
        oui = [oid for oid in offre_ids if faculte.get(oid) == "oui"]
        non = [oid for oid in offre_ids if faculte.get(oid) != "oui"]
        ranked = oui + non
        for rank, offre_id in enumerate(ranked[:3], start=1):
            row = rows[offre_id]
            classique = text_of["faculte_yes" if faculte.get(offre_id) == "oui" else "faculte_no"]
            lines.append(text_of["choice_line"].format(
                rank=rank, filiere=row.get("Filière", ""),
                etablissement=row.get("Établissement", ""), offre_id=offre_id,
                page=pages.get(offre_id), classique=classique))
        if len(offre_ids) < 3:
            lines.append(text_of["fewer_than_three"].format(count=len(offre_ids)))
        if not oui:
            lines.append(text_of["no_faculte"])
    lines.append(text_of["reminder"].format(text=text_of["allocation_reminder"]))
    lines.append(text_of["reminder"].format(text=text_of["official_site_reminder"]))
    lines.append(text_of["stay_free"])
    return "\n".join(lines)


def _unverified_section(refused_ids: set[str], by_type: dict[str, list[str]],
                        offre_ids: list[str], rows: dict,
                        text_of: dict[str, str]) -> str:
    lines = [text_of["h_unverified"]]
    for claim_id in sorted(refused_ids):
        kinds = ", ".join(by_type.get(claim_id, [text_of["unverified_proof_kind"]]))
        lines.append(text_of["unverified_claim"].format(claim_id=claim_id, kinds=kinds))
    for offre_id in offre_ids:
        row = rows[offre_id]
        if (row.get("Bourse") or "").strip() == NOT_PUBLISHED \
                or (row.get("Aide_FPP") or "").strip() == NOT_PUBLISHED:
            lines.append(text_of["unverified_quotas"].format(offre_id=offre_id))
    if len(lines) == 1:
        lines.append(text_of["all_verified"])
    return "\n".join(lines)


def _format_number(value: object, separator: str = ",") -> str:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError("calc result is not a number: asking, not guessing")
    text = str(number).replace(".", separator)
    return text.rstrip("0").rstrip(separator) if separator in text else text


def _strip_quoted(text: str) -> str:
    """Remove « ... » citations: student words and guide fields as published."""
    return _QUOTED_SPAN.sub(" ", text)


def _assert_no_forbidden_admission(text: str) -> None:
    if _contains_forbidden(text):
        for marker in _FORBIDDEN_SUBSTRINGS:
            if marker in text.casefold():
                raise ValueError(f"report promises admission or places: {marker!r}")


def _contains_forbidden(text: str) -> bool:
    folded = text.casefold()
    return any(marker in folded for marker in _FORBIDDEN_SUBSTRINGS)
