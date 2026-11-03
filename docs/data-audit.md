# Data audit: 20 OK rows against the official PDF (E3.3)

## Method

Reproducible sample of the rows with `Statut_qualité = OK`:

```bash
python scripts/sample_audit.py --seed 2026
```

Draw: `random.Random(2026).sample()` over the 206 `OK` rows sorted by
`Offre_ID` (test: `tests/test_sample_audit.py`). Each row is compared
with the local PDF (`data/source/guide_2026.pdf`, 116 pages, not committed) at the page
given in `data/pages_offres.csv`, on 8 fields: `Filière`, `Établissement`,
`Bourse`, `Aide_FPP`, `Mode_entrée`, `Bac_recommandé`, `Matières`,
`Débouchés_Métiers`.

Verdict rule: a field is compliant if its value equals the guide's, give or
take accents, case, punctuation and subject order (`PCT` = `SPCT`, E1.1). A
gap is a difference of substance: a wrong value, or an element omitted or
added. A value inferred from a "–" cell or from nothing (quota, mode, series)
is an added element: a gap. Threshold of issue #22: 3 rows or more with a gap
trigger a decision in `docs/decisions.md`.

## Table: 20 rows × 8 fields

`FIL` Filière, `ÉTA` Établissement, `BOU` Bourse, `AID` Aide_FPP, `MOD`
Mode_entrée, `BAC` Bac_recommandé, `MAT` Matières, `DÉB` Débouchés_Métiers.

| Offre | Pg | FIL | ÉTA | BOU | AID | MOD | BAC | MAT | DÉB |
|---|---|---|---|---|---|---|---|---|---|
| PUB-028 | 42 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-032 | 39 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| PUB-059 | 35 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-087 | 26 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-115 | 24 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-133 | 47 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-136 | 51 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-139 | 52 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-151 | 48 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-153 | 49 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-157 | 64 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-164 | 66 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-170 | 57 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-176 | 56 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-202 | 75 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-211 | 86 | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| PUB-215 | 87 | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| PUB-216 | 82 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PUB-217 | 89 | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| PUB-219 | 84 | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |

Reading notes (compliant rows): `PUB-059` (`DEAT/PV` of the guide in the
Matières segment), `PUB-087` (the guide's typo `géomantique` copied as is),
`PUB-133`/`PUB-157` (`SPCT`/`TF` normalized), `PUB-164`/`PUB-202` (`ou`
resolved per series, 3 subjects everywhere), `PUB-170`/`PUB-176` (extended
labels), `PUB-202` (typo `Fançais` corrected), merged cells attributed to
each row (`PUB-028`, `PUB-170`, `PUB-176`), `A` expanded into
`A1, A2` (`PUB-211`, `PUB-215`).

## Error rate

- **5 rows out of 20 (25 %)** carry at least one gap: `PUB-032`,
  `PUB-211`, `PUB-215`, `PUB-217`, `PUB-219`.
- **14 fields out of 160 (8.8 %)**.
- Threshold crossed (5 ≥ 3): decision in `docs/decisions.md`: fix the
  extraction and restrict, implemented in E3.5.

## Gaps

### 1. PUB-032: words glued together in `Débouchés_Métiers` (page 39)

CSV: « contrôle deséquipements de laboratoires médicaux etvétérinaires,
Maintenance des équipementsélectroniques ».
PDF: « contrôle des équipements de laboratoires médicaux et vétérinaires,
Maintenance des équipements électroniques ».

Three missing spaces. A whole-word match (E3.5) would miss `équipements`,
`vétérinaires`, `électroniques` on this row.

### 2. PUB-211: quotas, mode, series and DEAT segment (page 86)

- `Bourse`/`Aide_FPP`: "–"/"–" recorded as `0`/`0`.
- `Mode_entrée`: "–" recorded as `Classement`.
- `Bac_recommandé`: « A, B, C, D, G2, G3, DEAT, EA » recorded as « A1, A2, B, C,
  D, G2, G3 » (`DEAT`, `EA` omitted).
- `Matières`: the segment « Pour DEAT : toutes les trois (03) matières
  écrites » is missing (the A/B, C/D, G2/G3 segments are exact).

### 3. PUB-215: quotas and mode inferred (page 87)

`Bourse`/`Aide_FPP`: "–"/"–" recorded as `0`/`0`. `Mode_entrée`: "–"
recorded as `Classement`. Series, subjects (the `EA` subject of the shared
cell does belong to the other row) and careers exact. The page footer
states: « Mode d'entrée : A titre payant - les candidats sont invités à se
rapprocher de l'UADC » (a cost, not a mechanism).

### 4. PUB-217: 3-column page, 4 values inferred (page 89)

The page only gives No., institution and program. Quotas recorded as `0`/`0`,
mode recorded as `Dossier`, Bac recorded as `Toutes séries`. The word `Dossier`
appears nowhere in the guide as an entry mode (checked by full-text
search: `dossier` only appears on pages 9 and 16, off topic). Subjects and
careers `—`: a faithful transcription of the absence.

### 5. PUB-219: Bac inferred (page 84)

`Bac_recommandé`: "–" recorded as `Toutes séries`. Quotas (40/0), mode
(Concours), subjects and careers (`—`) transcribed faithfully.

### Scope beyond the sample

15 `OK` rows have `0`/`0` (`PUB-085`, `PUB-086`, `PUB-096`–`PUB-099`,
`PUB-145`, `PUB-180`, `PUB-211`–`PUB-215`, `PUB-217`, `PUB-218`): real zeros
must be told apart from "–". The UADC rows (`PUB-211` to
`PUB-215`) are `OK` and computable for serie C/D: without a fix, the agent
would write "0 grants planned, page 86", accepted by `verify_report` (it
compares against the CSV), while the page shows "–": the same case as the 7
offers quarantined in E3.2.

## E3.2 follow-up: quarantined rows (trace carried over)

7 `OK` rows remain `page_non_etablie`: the PDF contradicts their
institution (`docs/decisions.md`, 2026-10-29). Pages found, to be restored
after the labels are fixed: `PUB-025` → 42, `PUB-045` → 23,
`PUB-048` → 24, `PUB-142` → 53, `PUB-186` → 57, `PUB-187` → 59,
`PUB-188` → 58. `PUB-189` (page 58) has an empty program to fill in.
Unchecked suspicions: `PUB-026` (probable counterpart page 42), `PUB-049`
(probable counterpart page 24). Fix and restoration: E3.5.

## E3.4 follow-up: faculte_classique review (issue #23)

Column produced by `python scripts/make_faculte_classique.py --output
data/faculte_classique.csv` (rule: `Établissement` starts with
« Faculté » → `oui`, otherwise `non`; 3 exceptions reviewed below).
199 recommendable offers (`OK` with an established page): 54 `oui`,
145 `non`. Excluded from the file: the 5 non-`OK` rows marked
`oui` by the rule (`PUB-064`, `065`, `074`, `075`, `140`) and the
7 rows without a page (`PUB-025`, `045`, `048`, `142`, `186`, `187`,
`188`, E3.2 quarantine): a non-recommendable offer must never
be chosen as the "Faculté classique" choice, by construction
rather than by each caller's filter. Source instruction, guide
page 9: « Il est
fortement recommandé de choisir au moins une formation dans une
Faculté Classique parmi les trois choix à opérer sur la plateforme. »
(It is strongly recommended to choose at least one program in a Classical Faculty among the three choices to make on the platform.)

Review of the 60 `OK` rows marked `oui` (54 open to C/D according to
`series_et_offres_2026_2027.csv`, plus 6 outside the index: five A/B-only
offers — `PUB-048`, `050`, `141`, `143` in A1/A2/B, `PUB-146` in A1/A2 —
and `PUB-145` « Toutes séries » with no C/D pair in the index):
census into 14 labels, all genuine university faculties
(FA, FADESP, FASHS, FASEG ×2, FLLAC, FLASH, FLASH-Adjarra, FM, FSA,
FAST, FAST/Natitingou, FDSP, FSS); PDF check of the 5 suspect pairs and of the 3 exceptions,
detailed below. For the other rows, the `oui` rests on the CSV label. The file keeps 54 `oui`
(49 C/D + 5 outside the index): excluding the 3 quarantined rows to be restored in E3.5
(`PUB-045`, `048`, `142`) and the 3 INSTI rows (`PUB-186`, `187`, `188`).

Exceptions (`oui` → `non`, in `REVIEWED_EXCEPTIONS` of
`src/domain/faculte_classique.py`): `PUB-186`, `PUB-187`, `PUB-188` —
the PDF shows the Institut National Supérieur de Technologie Industrielle
(INSTI) on pages 57, 59 and 58 (Génie Civil 50/10; Génie Électrique et
Informatique 25/5, both options) while the CSV still carries the
FAST/Natitingou label quarantined in E3.2. Since the 3 rows are
also without a page, they are absent from the file until E3.5 (labels
fixed + pages restored), after which these exceptions join the
rule: regenerate the file, then remove the exceptions that became
redundant (the script reports them on stderr; a repaired label that
contradicted the review makes the script fail).

Quarantined rows (E3.2) are excluded from the file until E3.5
restores them; the true institution remains a faculty for `PUB-045`
(FLASH-Adjarra, page 23), `PUB-048` (FLLAC, page 24) and `PUB-142`
(FLASH-Parakou, page 53). `PUB-025` (ENSTIC, a true ENS) is excluded likewise.

Traps verified as `non`: `PUB-002` (CIFRED, « Facultaire » in the name
but a centre), `PUB-211` to `PUB-215` (UADC UFRs, not
faculties), `PUB-216` (shifted program label, « Métiers de
l'agriculture »). Outside the file because non-`OK`: `PUB-195`/`PUB-210`
(empty institution, `À vérifier`), like the 5 non-`OK` `oui` rows above.

Suspect rows checked against the PDF one by one,
program + quotas + series matching: `PUB-053` (Agroéconomie 25/2,
page 36), `PUB-054` (Forêts 23/5, page 35) and `PUB-055` (Entreprenariat
Agricole 25/5, page 36) are under « Faculté des Sciences Agronomiques
(FSA) »; `PUB-130` (Droit Privé 0/270, page 53) is under « Faculté de
Droit et Sciences Politiques (FDSP) »; `PUB-141` (Allemand 0/95, page
53) is under « Faculté des Lettres, Arts et Sciences Humaines (FLASH) ».
The 5 CSV labels are wrong but remain faculties: `oui`
confirmed, no new exception. These 5 label errors (outside the
7 E3.2 quarantines) are to be fixed in E3.5.

## E3.5 repairs (issue #24)

Applied by `python scripts/repair_guide_data_e35.py` (idempotent,
each value checked against the local PDF at the cited page; the script prints
the list of changes, 67 on the first application):

- **7 quarantined labels (E3.2) fixed, pages restored** as
  `verifie_main`: `PUB-025` → École Normale Supérieure /Porto-Novo
  (p. 42), `PUB-045` → FLASH-Adjarra (p. 23), `PUB-048` → FLLAC (p. 24),
  `PUB-142` → FLASH Parakou (p. 53), `PUB-186`/`187`/`188` → INSTI
  (p. 57/59/58). Regeneration of `data/faculte_classique.csv`
  (206 rows: 57 `oui`, 149 `non`) and removal of the INSTI exceptions from
  `REVIEWED_EXCEPTIONS`: the script reports their redundancy on stderr
  at the first regeneration, then stderr is empty.
- **5 E3.4 labels fixed**: `PUB-053`/`054`/`055` → Faculté des
  Sciences Agronomiques (FSA) (p. 35/36), `PUB-130` → Faculté de Droit
  et Sciences Politiques (FDSP) (p. 53), `PUB-141` → Faculté des
  Lettres, Arts et Sciences Humaines (FLASH) (p. 53). Still faculties:
  `oui` confirmed, no new exception.
- **`PUB-032`** (p. 39): three spaces restored in
  `Débouchés_Métiers` (« des équipements », « et vétérinaires »,
  « équipements électroniques »).
- **`PUB-211`** (p. 86): `DEAT` and `EA` restored in
  `Bac_recommandé`, segment `DEAT : Les trois (03) matières écrites`
  added to `Matières`.
- **`PUB-189`** (p. 58): program filled in, « Génie Énergétique
  (Énergies Renouvelables et Systèmes Énergétiques) ». The row remains
  `À vérifier`: it is not recommended.
- **"non publié" marker** (not published), distinct from 0, settled against the PDF on
  the 15 `OK` rows with `0`/`0`: real published zeros kept
  (`PUB-085`/`086`, `PUB-096`–`099`, `PUB-145`, `PUB-180`; their mode
  "–" on page 45 becomes "non publié" for `PUB-085`/`086` and
  `PUB-096`–`099`), dashes replaced by "non publié" on `Bourse`,
  `Aide_FPP`, `Total_allocations` and `Mode_entrée` for
  `PUB-211`–`215` (p. 86/87) and `PUB-217`/`218` (p. 89, no quotas, mode
  or series published), and on `Bac_recommandé` for `PUB-217`,
  `PUB-218` and `PUB-219` (p. 84). These values are never asserted
  as facts: `verify_report` refuses any `filiere` proof on a
  "non publié" field, and the search displays them as such.

## Conclusion

Seed 2026 sample: 15 rows out of 20 fully compliant,
5 documented gaps (§1 to §5). Threshold crossed: `docs/decisions.md`
decides (fix + restrict, in E3.5). The word "verified" only covers
the values transcribed from the guide; "–" cells are said to be
"not published by the guide" (« non publié »), never asserted. No change to
`data/` in this story.
