# PRD: PathProof (Meta Global AI Developer Hackathon)

**Track:** Indie Developer
**Targeted prizes:** Indie track ranking; "Best Agentic Use-Case" bonus; "Most Viral Project" bonus (post on X)
**Theme:** Build for Your World
**Tagline:** *Every study path comes with its proof.* An orientation agent that only recommends what it can prove.
**Build period:** 27 October → 3 November 2026 (feature freeze on the evening of 3 November)
**Submission:** Wednesday 4 November 2026, 21:00 ET = Thursday 5 November, 02:00 UTC = **03:00 in Porto-Novo**. Target: submit on the evening of 3 November.

---

## 0. Positioning: why this is not a chatbot

The official list of anti-projects contains three cases close to ours: "simple AI for Education chatbots", "Simple Image Analyzers" and "Basic RAG Applications". PathProof sets itself apart through three behaviours, all visible in the demo:

1. **The agent decides.** It picks the next tool from what it observes (blurry photo, missing grade, contradiction) and stops to ask a question instead of guessing.
2. **The model does not calculate.** The ranking average of each program (official formula, page 8 of the guide) and the filtering of offers are done by deterministic code, called as a tool.
3. **Every sentence has proof.** Every claim of the report points to a grade read on the photo, an excerpt of the transcript, a sourced row or a calculation. A verifier written in code blocks anything without proof.

The word "chatbot" appears nowhere: neither in the README, nor in the video, nor in the interface.

### Mapping to the judging grid

| Criterion (weight) | What PathProof shows |
|---|---|
| Impact (30%) | A problem lived in Benin, a sourced official figure, the lesson drawn from a first prototype |
| Use of Meta AI Tooling (25%) | Two Meta models in one loop: Muse Spark 1.3 (vision and tools) and Muse Voice Transcribe. SAM 3.1 was tested on D1 then dropped: it finds the table, not a cell (`docs/decisions.md`) |
| Technical Depth & Execution (20%) | The 224 real public offers of the official 2026-2027 guide (not a toy database), deterministic tools, a proof verifier in code, 10 evaluation cases of which 4 adversarial, raw outputs committed |
| Demo (25%) | Online demo usable by the judges, live tool trace, strong moment: the agent spots a contradiction and stops |

---

## 1. Problem

A student in Benin often picks a program on vague grounds (the BAC series, family opinion, rumor). They cannot clearly see which programs are open to their real profile, or where to find the official information.

- Impact figure: 77,101 BAC candidates in Benin, June 2026 session, Office du Baccalauréat data relayed by the press (source and caveats in `docs/impact.md`).
- Lesson from the earlier prototype: not documented in the repository, therefore not written (see `docs/impact.md`).

> **Project rule:** no figure enters the README, the video or the demo without a cited official source. As long as a source is missing, we write `TODO`.

---

## 2. User and inputs

**Main user:** a BAC graduate of series C or D (for the demo). All demo and evaluation data are fictional.

**Two inputs:**
1. A photo of their grade sheet.
2. A voice note of 30 to 60 seconds, in French. A text field serves as a fallback.

### 2.1 The voice note

**What the interface asks the student** (shown in French):
> « En 30 secondes, dis-nous : ta série, ce que tu aimes étudier, le métier qui t'attire, et ce qui compte pour toi (ville, bourse). » (In 30 seconds, tell us: your series, what you like to study, the job that attracts you, and what matters to you (city, grant).)

**What the agent extracts from it (`extract_profile` tool):**

| Field | Example | Use |
|---|---|---|
| `serie_declaree` | "D" | Cross-checked with the sheet |
| `moyenne_declaree` | "14" | Cross-checked with the calculation; never used in its place |
| `interets` | "la biologie", "soigner les gens" | Ranking of programs |
| `metier_vise` | "médecin" | Matched against the guide's `Débouchés_Métiers` column |
| `contraintes` | "Cotonou", "bourse" | Grant: the report shows the guide's quotas. City: the guide does not give it, so the agent says so and does not filter |

**Three rules:**
- Each extracted field keeps the exact quote from the transcript. The verifier checks that the quote exists word for word.
- A declared fact never replaces a fact read on the sheet. It is used for cross-checking.
- Interests are used to **rank** programs, never to decide whether the student has access to them.

**Example voice note for the demo (fictional student)** (in French, as spoken):
> « Bonjour, je suis en série D, j'ai eu 14 de moyenne. J'aime beaucoup la biologie et j'aimerais travailler dans la santé, peut-être médecin. Je préfère rester à Cotonou, et j'aurai besoin d'une bourse. » (Hello, I am in serie D, I got a 14 average. I really like biology and would like to work in health, maybe as a doctor. I prefer to stay in Cotonou, and I will need a grant.)

The associated fictional sheet shows an overall average of 11.2. This is the strong moment of the video: the agent spots the gap and asks the student before continuing.

The second strong moment comes from the guide itself (page 8): ranking is not done on the overall average but on a **ranking average specific to each program**, computed on three subjects with the series' coefficients. For Medicine in serie D, it is (SVT × 5 + Maths × 4 + PCT × 4) / 13. The agent can therefore say: "Your BAC average is 11.20, but your ranking average for Medicine is 13.15, because SVT counts 5 times in it." Few students know this; it is the heart of the impact.

With the real data, the rest of the demo is already written by the guide: "médecin" matches the careers of Médecine Générale (FSS, `PUB-062`) and Médecine Humaine (FM, `PUB-133`). Pharmacie (`PUB-064`) is excluded, because its row is marked "Réparé - fusion OCR", and the report files it under "Ce que je n'ai pas pu vérifier" ("what I could not verify"). This is not a trap invented for the demo: it is the guide's real quality control.

### 2.2 No RIASEC

The RIASEC questionnaire is removed, for three reasons:
- **It contradicts the project's principle.** A personality profile is a psychometric inference. It cannot be proven like a grade or a sourced row.
- **It feels like a chatbot.** Six multiple-choice questions, one by one, is exactly the image to avoid.
- **The voice note replaces it.** Interests are spoken by the student in their own words, then quoted as is in the report.

---

## 3. How the agent recommends

Recommendation happens in two steps: first access, which is strict, then ranking, which is explained.

### 3.1 Access (strict, deterministic)

An offer is proposed only if:
1. Its row in `data/offres_publiques_2026_2027.csv` has `Statut_qualité = OK`. Rows "Réparé - fusion OCR", "Texte continué" and "À vérifier" are excluded and listed under "Ce que je n'ai pas pu vérifier".
2. The student's series appears in `Bac_recommandé`.
3. `Mode_entrée` is displayed as is. For a **Concours** (competitive exam), the report states that admission goes through a separate test, and therefore that the BAC grades are not enough.

The guide publishes neither a threshold nor the average of the last admitted student. The report therefore never talks about admission chances.

**What the guide says (page 8, "Critères et Mode de calcul du classement"):**
- Ranking is done **per requested program**, from the highest to the lowest ranking average.
- The best averages get the grants, within the program's quota; then come the "partially paid" places, then the "fully paid" ones.
- The ranking average is computed on **the three main subjects retained for the program** (this is the `Matières` column), with the coefficients of these subjects in the BAC series: `M = (m1·x + m2·y + m3·z) / (x + y + z)`.
- Official examples: Medicine, BAC D: SVT × 5, Maths × 4, PCT × 4, out of 13. Medicine, BAC C: SVT × 2, Maths × 6, PCT × 5, out of 13.

### 3.2 Ranking (soft, explained)

Among the accessible offers, the agent ranks on three signals, all readable in the guide:
- **The target job**, matched against `Débouchés_Métiers`. Matching is done on whole words, then the model confirms by quoting the two texts. Example of a real trap: a naive search for "pilote" (pilot) returns Foresterie Tropicale.
- **The interests stated in the voice note**, matched against `Filière` and `Débouchés_Métiers`.
- **The student's ranking average for each offer**, computed by `compute_ranking_average` with the offer's three subjects. Example for Médecine Générale, serie D: "SVT 15 × 5, Maths 12 × 4, PCT 12 × 4: 13.15 / 20". This is a computed fact, not a prediction: the guide does not publish the other candidates' averages.

The report shows at most 5 offers.

### 3.3 The proofs

Each recommendation displays:
- **Why it is accessible:** the series in `Bac_recommandé`, the entry mode, the `Offre_ID` and the page of the official guide.
- **Why it suits you:** the quote from the voice note ("peut-être médecin"), the guide's sentence ("Débouchés : Médecin généraliste…") and the grades of the sheet in the listed subjects.
- **What the guide provides:** the `Bourse` and `Aide_FPP` quotas, presented as figures from the guide ("95 grants and 20 FPP aids planned"), never as a chance of getting one.
- **Your ranking average for this offer:** the detail of the calculation, with the page 8 formula and the provenance of each coefficient.

A section "Ce que je n'ai pas pu vérifier" lists missing or disputed data.

### 3.4 What the student leaves with: 3 choices for apresmonbac.bj

The guide (pages 11 to 18) explains that the student enters **3 choices** on the official platform https://apresmonbac.bj. The report therefore ends with a proposal of 3 choices, ready to copy, applying the page 9 instructions:
- at least one choice in a **Classical Faculty** ("strongly recommended");
- a reminder that **any change of program loses the allowance**;
- a reminder that apresmonbac.bj is **the only official site**.

The student remains free: the agent explains, it does not choose for them.

### 3.5 What the report never says

- "You will be admitted", or any probability of admission.
- An offer, an institution or a figure absent from the guide's `OK` rows.
- A city: the guide does not give it.
- A grade that the agent did not read or that the student did not confirm.

---

## 4. Agent tools

| Tool | Role | Engine | Output |
|---|---|---|---|
| `transcribe_voice` | Transcribe the voice note | Muse Voice Transcribe | Text, plus a confidence score if the API provides one |
| `extract_profile` | Extract series, declared average, interests, job, constraints | Muse Spark 1.3, strict JSON output | JSON with the exact quote for each field |
| `read_grade_sheet` | Read the sheet | Muse Spark 1.3 (vision) | `[{matiere, note, lisible}]`; `null` grade if unreadable |
| `zoom_cell` | Isolate a doubtful cell and re-read it | SAM 3.1, then Muse Spark 1.3 | **Dropped**: NO GO at spike E0.6, 0 successes out of 3 (`docs/decisions.md`). |
| `compute_ranking_average` | Compute the ranking average of an offer (page 8 formula) | Deterministic code | Average, detail of the calculation, provenance of each coefficient |
| `lookup_filieres` | Filter accessible programs, then rank them | Deterministic code | Verified rows, with score and reasons |
| `ask_student` | Ask a question and suspend the loop | Interface | The student's answer |
| `verify_report` | Check every proof of the draft | Deterministic code | List of problems; empty if everything is proven |
| `build_report` | Format the validated report | Code | Final report |

The verifier is **code**, not a second call to the model. The report is first a JSON where every claim carries a proof of type `grade`, `transcript`, `filiere` or `calc`, with its reference. `verify_report` checks that each reference exists and matches. This is what makes the agent verifiable rather than merely "cautious".

---

## 5. Functional requirements

**FR-1 Agent loop.** The agent receives the inputs, chooses the next tool (Muse Spark 1.3 with `tools`), executes, observes, then decides. It stops after 12 steps. `ask_student` suspends the loop until the answer.

**FR-2 Sheet reading.** Strict JSON output. An unreadable subject has the grade `null`. The agent asks the student for a new photo or the grade (`zoom_cell` is dropped: NO GO at spike E0.6).

**FR-3 Grade validation.** A grade outside 0–20, or a subject invalid for the series, triggers a question. Never a default value (rule taken from V1, see `docs/v1-reuse.md`).

**FR-4 Transcription and profile.** If confidence is low or absent, the agent asks for confirmation of the series before continuing.

**FR-5 Cross-checking.** If the declared series or average differ from those of the sheet, the agent flags it and asks the student. The sheet prevails until the student provides a new photo.

**FR-6 Calculation.** `compute_ranking_average` applies `M = (m1·x + m2·y + m3·z) / (x + y + z)` to the offer's three subjects, with the series' coefficients.

**Source of the coefficients:** `data/coefficients_bac_benin.json`, taken from the "Liste des épreuves à l'examen du Baccalauréat" (list of exams of the Baccalauréat) of the Office du Bac (interministerial order N°016-2003/MESRS/MEPS/METFP, as amended). Only group 1 exams are used. The second-group orals and PE appear in no ranking subject list.

**Checks made on 27 October:**
- The C and D coefficients reproduce exactly the two examples of page 8 of the 2026-2027 guide (Medicine D: 5, 4, 4; Medicine C: 2, 6, 5).
- The team confirms that all the coefficients in the file are those in force on 27 October 2026.
- Coverage of the `OK` offers in **Classement** mode: C 146 out of 149, D 147 out of 150. The gaps:
  - `PUB-077`: glued text ("SVTDEAT/Pêche…"), to fix in the splitting;
  - `PUB-085`, `PUB-086` (Confucius Institute): "Espagnol ou Allemand", subjects that series C and D do not have. The agent does not compute and says so.
- Offers in **Concours** mode (Culture générale, Commentaire de texte…) list the exams of the competition, not BAC subjects. The agent computes no average for them and displays the exams.

**Mandatory unit test:** the two examples of page 8, hard-coded in the tests.

If a coefficient is missing, the agent does not compute that offer and says so. `TODO`: check that the Office du Bac page is still online and cite it in the README. Do not reuse the phrase "dans votre chatbot" from the JSON file.

Subject names vary ("PCT" and "SPCT", "Anglais (LV1)", "Hist-Géo/Anglais (DT/STI)"): the subject normalization taken from V1 is indispensable.

**FR-7 Search.** `lookup_filieres` only uses rows with `Statut_qualité = OK`, applies section 3.1, then ranks per section 3.2. It also returns the excluded rows that would have matched, with their status, for the "Ce que je n'ai pas pu vérifier" section.

**FR-8 Verification.** No report is displayed as long as `verify_report` returns a problem. The agent fixes the draft or removes the unproven claim.

**FR-9 Report.** It follows section 3.3. If there is no verified program for the series, the report says so instead of recommending.

**FR-10 Web demo.** The student uploads a photo and a voice note. The page displays each step as it happens (tool, input, output, decision), the agent's questions, then the report with clickable proofs. Fictional sheets and voice notes are offered, so judges can test without preparing anything.

**FR-11 Degraded mode.** If the network or the API fail, the page displays the recording of the last successful run, with the notice "exécution enregistrée" (recorded run).

---

## 6. Data

Source: the official *Guide d'information 2026-2027*, extracted from the PDF (via MinerU) into four CSV files.

| File | Rows | Use |
|---|---|---|
| `offres_publiques_2026_2027.csv` | 224 offers | Main source: series, entry mode, subjects, careers, quotas, quality status |
| `series_et_offres_2026_2027.csv` | 897 series–offer pairs | Index by series (C: 204 pairs of which 186 `OK`; D: 205 of which 187 `OK`) |
| `controle_qualite_2026_2027.csv` | 39 anomalies | Repair log, displayed in the demo |
| `coefficients_bac_benin.json` | 13 series | BAC coefficients (group 1) for `compute_ranking_average`; only C and D are used |
| `offres_privees_2026_2027.csv` | 753 offers | **Not used to recommend**: no series, no subjects, no careers. Mentioned in the README |

**What the guide gives:** admitted series, entry mode (180 Classement, 42 Concours, 2 Dossier), subjects per series, careers, grant and FPP aid quotas, source line number.

**What the guide does not give:** city, thresholds, average of the last admitted student, cost. The agent does not invent them.

**Data work to do (D4):**
1. Add a `page_pdf` column to each offer, so that the proof points to the page of the official PDF and not to a line of the MinerU file. **First draft done** (`pages_offres.csv`): 180 pages found without ambiguity, 23 told apart by the institution's acronym, 19 to check by hand (including Pharmacie `PUB-064`, actually page 36), 2 not found (`PUB-122`, `PUB-210`).
2. Split the `Matières` column by series. The text is sometimes glued ("…SVTA1, A2 : … "); a split on the series headings works for 222 offers out of 224; the 2 remaining (`PUB-220`, `PUB-223`) have "—" and will be treated as "subjects not published".
3. Check 20 randomly drawn `OK` rows by hand against the PDF, and publish the result in `docs/data-audit.md`. This is what allows writing "verified" without lying.
4. Put the official public URL of the PDF in the README and in each proof. URL found on www.enseignementsuperieur.gouv.bj (see `docs/impact.md`). The guide carries the mention "Vente interdite" (sale forbidden): distributing it free of charge with its source remains consistent, but without an official URL, do not republish the PDF itself.
5. Add a `faculte_classique` column (yes or no), for the page 9 instruction. Starting rule: the institution's name starts with "Faculté". To be reviewed by hand.

**Provenance (to state in the README):** the CSV extraction was done before the hackathon, from an official public document. These are data, not code. The splitting script, the tools and the agent are written during the event.

Limit written in the README: "Recommendations limited to the public offers of series C and D of the 2026-2027 guide whose row passed the quality check."

---

## 7. Measurable objectives

| # | Objective | Measure |
|---|---|---|
| O1 | A full case runs end to end | Fictional sheet and voice note → proven report, without human intervention |
| O2 | The agent invents nothing | 0 claims without proof across the 10 cases |
| O3 | Visible autonomy | At least 4 tool calls per full case, displayed in the demo |
| O4 | The agent asks instead of guessing | At least 4 cases where it calls `ask_student` appropriately |
| O5 | Reproducible | `evals/results/` contains the raw outputs and a summary table |
| O6 | Usable by the judges | Public URL, tested from another device on 2 November |

---

## 8. Scope

### In scope

- Agent loop and the 8 tools of section 4 (`zoom_cell` is dropped after spike E0.6).
- Demo web interface, deployed at a public URL.
- The public C and D offers of the 2026-2027 guide, with `page_pdf` and a 20-row audit.
- 10 evaluation cases and their results.
- 3-minute video, README, post on X.

### Out of scope

- RIASEC questionnaire (see section 2.2).
- WhatsApp, payment, landing page, database, user accounts, task queue.
- Speech synthesis and audio report for parents.
- Grant computation and the full guardrails of V1.
- Local languages (Fon, Yoruba). This is an option to test only if everything else is finished, with no promise in the README.
- "Open Weight Models" bonus (Muse Spark Open). It is not on the critical path.

Any out-of-scope idea goes into `docs/decisions.md` and is not implemented before 3 November.

---

## 9. Non-functional requirements

- **Honesty:** the README, the video and the demo only describe what really runs.
- **New work only:** all the code is written during the event. No V1 code is copied.
- **Data:** only fictional sheets and voice notes. No real student data.
- **Secrets:** `MUSE_API_KEY` in `.env`, server side only, never versioned.
- **Cost:** tests and the public demo stay under the $150 of credits. Usage limit on the public demo; spending alert enabled in Billing.
- **Repository accessibility:** public repository, README readable without login, no link to a private repository.
- **Tests and minimal CI:** a single GitHub Actions workflow (`.github/workflows/tests.yml`) runs `python -m pytest` on every push; badge in the README. It only tests deterministic code (`compute_ranking_average` with the two page 8 examples, subject splitting, `lookup_filieres`, `verify_report`), with no key or API call. The 10 evaluations **never** run in CI: they consume credits, they are launched by hand and their results are committed in `evals/results/`.
- **Deployment:** Vercel (account already linked to GitHub), redeployed on every push to `main`. From D7, no push to `main` without green local tests; no deployment after the freeze on the evening of 3 November. No staging, no Docker.
- **Code rules:** `AGENTS.md` at the root (naming, structure, tests, git).

---

## 10. Evaluation plan

| Case | Input | Expected behaviour |
|---|---|---|
| `clear_sheet_d_medecin` | Clear sheet, serie D, "peut-être médecin" | `PUB-062` (page 36) and `PUB-133` (page 47) at the top; Medicine ranking average = (SVT × 5 + Maths × 4 + PCT × 4) / 13; 3 choices proposed including one Classical Faculty |
| `clear_sheet_c` | Clear sheet, serie C, clear voice note | Complete report, all proofs valid |
| `blurry_photo` | Blurry photo | Asks for a new photo or the grade; no invented grade |
| `missing_grade` | A subject missing from the sheet | Flags the missing subject and asks; does not invent it |
| `out_of_range_grade` | A grade of 25/20 | Asks for confirmation; no calculation with this value |
| `noisy_voice` | Noisy voice note | Asks for confirmation of the series |
| `voice_contradicts_sheet` | Voice: "14 average"; sheet: 11.2 | Flags the gap, asks, keeps the sheet |
| `unverified_trap` | Serie D, "je veux être pharmacien" (I want to be a pharmacist) | Pharmacie (`PUB-064`, "Réparé - fusion OCR") is not recommended; it appears in "Ce que je n'ai pas pu vérifier" |
| `false_friend` | "Je veux être pilote de ligne" (I want to be an airline pilot) | Foresterie Tropicale is not proposed; the report says that no career in the guide cites this job |
| `concours_entry` | Serie D, "infirmier" (nurse) | Sciences Infirmières et Soins Infirmiers marked "Concours : les notes du Bac ne suffisent pas" |

**Success criterion:** 9 cases out of 10 compliant, and 0 claims without proof overall.
**Published measures:** compliance per case, number of tool calls, number of questions asked, duration.

---

## 11. Work plan

(J = day; the French day abbreviation is kept because the issues use it.)

| Day | Date | Deliverable |
|---|---|---|
| J1 | Tue 27 Oct | Final PRD; repository renamed PathProof; credits claimed. Tests: vision on a fictional sheet, Muse Voice Transcribe in French, SAM 3.1 with a text prompt. "Go / no go" decision on `zoom_cell`: NO GO (E0.6). |
| J2 | Wed 28 Oct | `read_grade_sheet` and `compute_ranking_average` (coefficient table ready, tested against the two page 8 examples). Session "Agents 102: Verifiable Agents" at 12:00 ET, i.e. 17:00 in Porto-Novo. Minimal CI (workflow + badge, about 30 minutes). |
| J3 | Thu 29 Oct | `transcribe_voice`, `extract_profile`, `ask_student`. Proof JSON format frozen. |
| J4 | Fri 30 Oct | Data: `page_pdf`, splitting of `Matières`, 20-row audit. `lookup_filieres`. |
| J5 | Sat 31 Oct | Complete loop on the command line, `verify_report`, `build_report`. |
| J6 | Sun 1 Nov | Web demo with the trace, deployed; fallback recording. |
| J7 | Mon 2 Nov | 10 evaluation cases, results committed, fixes; demo tested from another device; team registered on the CV platform. |
| J8 | Tue 3 Nov | Video, README, X post ready, **feature freeze**, submission in the evening. |
| J9 | Wed 4 Nov | Margin. X post with the video, link submitted on the platform. Limit: 03:00 in Porto-Novo on the night of 4 to 5. |

Discord office hours take place from 10:00 to 11:00 ET on weekdays (15:00 to 16:00 in Porto-Novo until 30 October, then 16:00 to 17:00 from 2 November). To be used for API questions.

---

## 12. Risks and responses

| Risk | Impact | Response |
|---|---|---|
| Muse Voice Transcribe handles French poorly | No voice note | Test on D1; text field as a fallback |
| SAM 3.1 does not locate a table cell | No `zoom_cell` | **Realized on D1 (E0.6, 0 out of 3)**: the agent asks for a new photo instead |
| Vision unreliable on handwritten sheets | Wrong grades | Fictional printed sheets; limit written in the README |
| OCR extraction errors in `OK` rows | False information presented as verified | 20-row audit against the PDF; proof with `page_pdf` so the student can check themselves |
| Misleading job ↔ careers matching ("pilote" → Foresterie) | Absurd recommendation | Whole words, confirmation quoted by the model, `false_friend` case |
| Republication of the guide's data | Doubt about the public repository | Official public document, source cited; publish only the subset used if a doubt remains |
| Unstable tool calling in the demo | Failed demo | Fallback recording (FR-11) |
| Public demo that consumes the credits | Demo cut off | Usage limit; spending alert |
| Scope drift | Nothing finished | Freeze on 3 November; everything else in `docs/decisions.md` |
| A judge finds V1 | Doubt about "new work only" | README section on V1 (section 14) |

---

## 13. Video (3 minutes, English subtitles)

1. **0:00–0:20:** the strong moment first. The student says "14 average", the sheet says 11.2, the agent stops and asks.
2. **0:20–0:45:** the problem, with a single sourced figure.
3. **0:45–2:00:** a full case, with the tool trace on screen and the clickable proofs in the report.
4. **2:00–2:30:** a hard case: blurry photo, zoom or new request.
5. **2:30–2:50:** the table of the 10 evaluations, "0 claims without proof", and the Pharmacie row dropped by the quality check.
6. **2:50–3:00:** what is new, the limits, the team, the X account.

---

## 14. Relationship with V1

Text to put in the README:

> An earlier prototype by the same author (OrientBot V1, a fixed WhatsApp workflow, 7 users, now paused) explored this problem. No code from it is reused here. PathProof was built from scratch during the hackathon. Only public official rules (the MESRS weighted-average formula, subject-name normalization) were re-implemented. See `docs/v1-reuse.md`.
>
> Data: the program list comes from the official public *Guide d'information 2026-2027*. Its CSV extraction was done before the event; it is data, not code. Every recommendation links back to the guide page it comes from.

---

## 15. Submission checklist

- [ ] Public repository named PathProof, readable without login
- [ ] README: real status, "What is new" section, V1 section, Meta models used, limits, team
- [ ] 3-minute video, link in the README
- [ ] Public demo URL, tested from another device
- [ ] `evals/results/` with the raw outputs and the summary table
- [ ] No key, no personal path, no real data
- [ ] All teammates listed on the CV platform
- [ ] Post on X with the video, link submitted for the Viral prize
- [ ] Submission on the CV platform before 4 November, 21:00 ET
