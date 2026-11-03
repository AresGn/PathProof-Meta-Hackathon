# What we take from OrientBot V1 (and what we leave)

**Rule:** we take **business rules** (specifications) and rewrite them in this repository during the event. No code file, function or block of code from `orientbotv2` is copied. This is what the README says ("No code from it is reused here") and what the "new work only" framework requires. See also `docs/prd.md` (sections 0, 12 and 14).

This document only cites elements checked in the V1 code (read-only, private repository, not linked here). The paths mentioned serve as an internal reference for the team; none of the contents of those files is reproduced.

---

## 1. To take as a rule (rewrite from scratch)

### 1.1 Ranking average per program
- **Source in V1:** `packages/domain/src/mesrs/coefficients-bac-series.ts`, computation in `calculer-moyenne.ts`.
- **Rule:** average weighted by the coefficients of the BAC series. Only the **group 1 (written + practical)** exams count.
- **What changes compared with V1:** PathProof computes the **ranking average specific to each offer**: `M = (m1·x + m2·y + m3·z) / (x + y + z)`, on the three subjects of the offer's `Matières` column, with the series' coefficients (2026-2027 guide, page 8). Tool: `compute_ranking_average`.
- **Official source:** order N°016-2003/MESRS/MEPS/METFP (as amended) for the coefficients; *Guide d'information 2026-2027*, page 8, for the formula.
- **Data:** `data/coefficients_bac_benin.json`. A data file, not code. The C and D coefficients must reproduce the two examples of page 8 (Medicine D: 5, 4, 4; Medicine C: 2, 6, 5), a mandatory unit test. The team confirms that the coefficients are those in force on 27 October 2026.

### 1.2 Matching subject names
- **Source:** `packages/domain/src/mesrs/matcher-matieres.ts`.
- **Rule:** normalize both sides (case, accents, plurals, abbreviations: "math", "PCT" and "SPCT", "Anglais (LV1)", "Hist-Géo/Anglais (DT/STI)"), then resolve compound formulas with the subjects the student actually has.
- **Why:** grade sheets, the guide and the coefficient table do not write subjects the same way. Without this step, `read_grade_sheet` produces subjects that match nothing.

### 1.3 Recommend nothing without proof
- **Source:** a design principle of this repository (`docs/architecture.md`), not a V1 file.
- **Rule:** only rows with `Statut_qualité = OK` are recommended; the others are listed under "Ce que je n'ai pas pu vérifier" ("what I could not verify"). Every sentence of the report carries a proof (`grade`, `transcript`, `filiere` or `calc`) checked by `verify_report`.

### 1.4 Ask rather than guess
- **Source:** `profilage.processor.ts`, validation of grades between 0 and 20 and of valid subjects for the series.
- **Rule:** a grade outside 0–20 or a subject invalid for the series triggers a question (`ask_student`), never a default value (FR-3).

---

## 2. Not to take for this event

| V1 element | Why we leave it |
|---|---|
| WhatsApp bot (Baileys), BullMQ queue, Supabase | Heavy infrastructure, out of reach in the 9 days |
| KKiaPay payment, landing page, partner codes | Off topic for the demo |
| Session state machine (`ACCUEIL` → `RAPPORT_PARENTS`) | Fixed workflow, replaced by a loop where the agent chooses the tool |
| RIASEC questionnaire | **Removed on principle** (`docs/prd.md` section 2.2): a personality profile cannot be proven, and six multiple-choice questions feel like a "chatbot". The voice note replaces it |
| Recommendation guardrails (anti-saturation, public-first, strict match, grant, validator) | Full pipeline too heavy; we keep the "nothing without proof" idea, delivered by `verify_report` |
| Audio report for parents, speech synthesis | Meta has no TTS API |
| Grant computation (`estimer-bourse.ts`) | Out of scope; the report only shows the guide's quotas |
| LLM calls via OpenRouter / Groq / Claude | Replaced by the Meta models |

---

## 3. Data: what we can and cannot do

**What is in the repository (data, not code):** the CSVs extracted from the *Guide d'information 2026-2027*, an official public MESRS document. The extraction (MinerU) was done before the hackathon; these files were kept in the V1 folder (`GUIDE_2026-2027-CSV-EXCEL/`) and copied as is into `data/`. They are:

- `offres_publiques_2026_2027.csv`, `series_et_offres_2026_2027.csv`, `controle_qualite_2026_2027.csv`;
- `pages_offres.csv` (offer → PDF page), produced for PathProof;
- `coefficients_bac_benin.json` (list of the Office du Bac exams).

**What is not in the repository:**
- **The guide PDF.** It carries the mention "Vente interdite" (sale forbidden). A local copy exists in `data/source/` (ignored by git) to check pages. We do not republish it; a public official URL was found on 3 Nov and is cited in `docs/impact.md` (see also `docs/prd.md` section 6).
- **`offres_privees_2026_2027.csv` (753 offers).** They are useless for recommending (no series, subjects or careers); we therefore reduce what we republish. The README mentions them.
- The other V1 guides (2024-2025, 2025-2026) and any content from the PDFs or Markdown files of `orientbotv2`.

**Provenance to write in the README:** see `docs/prd.md` section 14. If any doubt about republication remains, we publish only the subset used (C and D).

---

## 4. Summary for the team

- **Take:** the official average formula (rewritten, with a test on the page 8 examples), subject normalization, the "nothing without proof" rule, the "ask rather than guess" rule.
- **Leave:** WhatsApp, payment, TTS, parents, grant, full guardrails, RIASEC.
- **Data:** the guide's CSV and JSON files in `data/`; PDF only locally.
- **Forbidden:** copying code or code files from `orientbotv2` into this repository.
