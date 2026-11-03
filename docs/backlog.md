# PathProof backlog

Breakdown of `docs/prd.md` (27 Oct version) into epics and stories. The PRD schedule (section 11) serves as the sprint plan: there is no other. Tick a box only when the acceptance criterion is verified.

**Sizes:** S ≤ 2 h, M ≈ half a day, L ≈ a day. **Days:** J1 = Tue 27 Oct, J2 = Wed 28, J3 = Thu 29, J4 = Fri 30, J5 = Sat 31, J6 = Sun 1 Nov, J7 = Mon 2, J8 = Tue 3 (freeze in the evening), J9 = Wed 4 (margin; limit 21:00 ET = 03:00 in Porto-Novo). (J = "jour", day; the issues use this notation.)

**Tracking:** one GitHub issue per story (`#N` links below), grouped into 8 milestones J1 to J8; labels `epic:*`, `type:*`, `size:*`, `critical-path`, `needs-human`, `conditional`, `cut-line`. The issue criteria are the strict version of the acceptance criteria of this file. **Code rules:** see `AGENTS.md` (naming, structure, tests, definition of "done"). **Rules:** out of scope = no RIASEC, TTS, WhatsApp, grant computation (see PRD section 8); any new idea goes into `docs/decisions.md`. No impact figure without an official source.

## Dependency graph

```
E0 spikes (vision / voice / SAM / multi-tool round trip) ──► decisions (zoom_cell go/no-go, endpoints)
data/ ─► E1.1 subject normalization ─► E1.2 compute_ranking_average ──────┐
                          └► E3.1 Matières parser ─► E3.5 lookup_filieres ┤
E0.4 vision ─► E1.3 read_grade_sheet ──────────────────────────────────────┤
E0.5 voice ─► E2.1 transcribe_voice ─► E2.2 extract_profile ──────────────┤
E1.4 proof format ─► E2.4 verify_report ──────────────────────────────────┤
                                                                          ▼
                  E4 12-step loop + ask_student ─► build_report ─► end-to-end CLI (O1)
                                                                          ▼
                  E5 streaming /run + UI + degraded mode + deployment ─► E6 evals ─► E7 submission
```

**Critical path:** proof format → `verify_report` → loop → CLI → web → evals. `zoom_cell` is dropped (NO GO, E0.6).

**Vertical slice (E2.5, end of J3):** a run without vision or voice (grades and profile entered as JSON) goes through calculation → search → draft → verifier. J5 then adds vision and voice, it does not discover the loop. Gap with the PRD: `verify_report` moves from J5 to J3.

---

## E0 — Foundations and spikes (J1, Tue 27 Oct)

- [x] **E0.1 (S)** Secrets and brand: rename the file `env` to `.env` (team action); replace OrientBot with PathProof in `web/index.html`, `src/api/server.py`, `LICENSE`; `MAX_STEPS = 12` in `src/agent/loop.py`. *Done on 27 Oct.*
  *Acceptance:* `grep -ri orientbot --exclude-dir=.git --exclude-dir=.agents --exclude-dir=.claude .` only returns the README (V1 section), `docs/v1-reuse.md`, `docs/prd.md` (section 14) and this backlog; `git check-ignore .env` answers; `git ls-files env` is empty. *Verified, and a call to `muse-spark-1.3` with the key from `.env` succeeds.*
- [ ] **E0.2 (S)** [#4](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/4) Each member claims their $150 of credits and enables the spending alert (team action).
  *Acceptance:* the Billing page shows the credits and the alert.
- [x] **E0.3 (M)** [#5](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/5) Fictional example set: clear serie D sheet (overall average 11.2; SVT 15, Maths 12, PCT 12), clear serie C sheet, blurry sheet, two voice notes (one consistent with the D sheet, "peut-être médecin"; one contradictory, "14 de moyenne").
  *Acceptance:* 5 files in `data/samples/`, `data/samples/README.md` up to date, no real data.
- [x] **E0.4 (S)** [#6](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/6) Vision spike: D sheet → JSON, three runs.
  *Acceptance:* the 3 JSON files are identical (`diff`); result noted in `docs/decisions.md`. *Dep.:* E0.3.
- [x] **E0.5 (S)** [#7](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/7) Voice spike: model identifier and audio format taken from the official documentation; French transcription of the voice note.
  *Acceptance:* doc URL cited; transcribed text; presence or absence of a confidence score noted. *Dep.:* E0.3.
- [x] **E0.6 (S)** [#8](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/8) SAM 3.1 spike: locate a table cell with a text prompt.
  *Acceptance:* **go / no go** decision for `zoom_cell` written in `docs/decisions.md`. *Dep.:* E0.3. *Result:* **NO GO** (0 out of 3, sharp and blurry).
- [x] **E0.7 (M)** [#9](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/9) Round-trip spike: two tools, the model chooses, the result is sent back to it, its final answer uses it (extension of `scripts/test_muse_tool_call.py`).
  *Acceptance:* 5 runs out of 5 whose final answer contains the value returned by the tool; report committed in `docs/`.
- [x] **E0.8 (S)** [#46](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/46) Image experiment: test Meta's image generation on a report for parents. *Experiment off the critical path, to be cut first if delay sets in.* Throwaway script that sends to the image generation API (official doc `dev.meta.ai/docs/image-generation`) the content of the D sheet (average 11.2; Medicine ranking average 13.15; 3 programs; grants) and asks for a summary card for parents, 3 runs. Manual check of each image: figures, program names, accents, spelling. Comparison with a code rendering (HTML to PNG) from the same data.
  *Acceptance:* model, format and size taken from the official doc (URL cited); 3 raw images in `docs/spikes/image/`; table of errors per run (wrong figure, distorted name, unreadable text) and cost in credits in `docs/decisions.md`. The generated image is never presented as a verified report (it does not go through `verify_report`). The README and the video only describe the measured result, even if it is bad. *Dep.:* E0.3. *Blocks nothing.*

## E1 — Deterministic core and sheet reading (J2, Wed 28 Oct)

- [x] **E1.1 (S)** [#10](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/10) Coefficient loader and subject normalization (case, accents, "PCT" and "SPCT", "Maths") for C and D, from `data/coefficients_bac_benin.json`.
  *Acceptance:* tests: each retained alias resolves; an unknown subject raises an explicit error.
- [x] **E1.2 (M)** [#11](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/11) `compute_ranking_average`: `M = Σ(mi·ci) / Σci`, with detail and provenance of each coefficient. *Dep.:* E1.1.
  *Acceptance:* **the two page 8 examples hard-coded in the tests** (Medicine D: SVT 5, Maths 4, PCT 4; Medicine C: SVT 2, Maths 6, PCT 5; out of 13); SVT 15, Maths 12, PCT 12 in serie D → 13.15 (2 decimals, half up); missing coefficient → "non calculé" (not computed) with the reason.
- [x] **E1.3 (M)** [#12](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/12) `read_grade_sheet`: strict JSON `[{matiere, note, lisible}]`, `null` if unreadable. *Dep.:* E0.3, E0.4, E1.1.
  *Acceptance:* output validated by schema on 2 fictional sheets; grade outside 0–20 or subject invalid for the series flagged (FR-3), never a default value.
- [x] **E1.4 (S)** [#13](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/13) Frozen proof format (`grade`, `transcript`, `filiere`, `calc`), documented in `docs/architecture.md`.
  *Acceptance:* versioned schema; 4 valid and 4 invalid examples in tests.

- [x] **E1.5 (S)** [#14](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/14) Minimal CI: GitHub Actions workflow `.github/workflows/tests.yml` + badge in the README. *Dep.:* E1.2 (so that a meaningful test runs).
  *Acceptance:* the workflow is green on `main`; the README badge displays; the workflow uses no secret and does not call the API (the 10 evaluations never run in CI).

> **Checkpoint A (end of J2):** `python -m pytest` green, including the two page 8 examples, **and the workflow green on GitHub**; `read_grade_sheet` works on 2 sheets; `zoom_cell` decision made.

## E2 — Voice, profile, questions, verifier (J3, Thu 29 Oct)

- [x] **E2.1 (M)** [#15](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/15) `transcribe_voice`. *Dep.:* E0.5. *Done on 28 Oct: 2 real calls on the contradictory note, raw outputs in `docs/spikes/voice/transcribe_voice/` ("série D" in `text`, "14" in `text_normalized`, confidence None).*
  *Acceptance:* text obtained for the French sample; network failure → typed error, never an invented text.
- [x] **E2.2 (M)** [#16](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/16) `extract_profile`: series, declared average, interests, target job, constraints, each with its exact quote. *Dep.:* E2.1. *Done on 28 Oct: real call on the coherent voice note → serie D, declared average 11.2, médecin, Cotonou as a constraint (result in issue #16).*
  *Acceptance:* test: each quote is an exact substring of the transcript; absent field → `null`.
- [x] **E2.3 (S)** [#17](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/17) `ask_student`: suspends the loop and resumes with the answer. *Done on 28 Oct: the loop returns `{status: needs_input, question, messages, tool_call_id, pending_tool_call_ids, steps_used}`, `resume` answers each pending call (answer or `not executed` error) and counts the steps over the whole run; tests in `tests/test_ask_student.py` (tool) and `tests/test_loop.py` (loop, strict fake client).*
  *Acceptance:* test: the loop returns a question then resumes at the answer; without an answer, no following tool call.
- [x] **E2.4 (M)** [#18](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/18) `verify_report`: checks that each proof exists and matches. *Dep.:* E1.4.
  *Acceptance:* 4 falsification tests (a modified grade, an invented quote, a missing `Offre_ID`, a wrong calculation) all fail; a correct report returns an empty list; fails closed (a `None` report, without `claims`, or an exception blocks the report); the refusal message gives `type` and `claim_id`, never the expected value.
- [x] **E2.5 (M)** [#19](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/19) **Vertical slice** without vision or voice: JSON input → `compute_ranking_average` → provisional search → draft with proofs → `verify_report`. *Dep.:* E1.2, E2.4.
  *Acceptance:* a scripted run prints a verified report for serie D. *Done: command and tests in `tests/test_vertical_slice.py` (see `scripts/README.md`).*
- [x] **E2.6 (S)** Pooling of what `read_grade_sheet` and `extract_profile` duplicate (postponed by the review of #61): Muse Spark 1.3 call and decoding of its JSON answer in a single module of `src/clients/`, 0–20 bounds in `src/domain/`, tests' fake client in a single file. *Dep.:* E1.3, E2.2. *Done on 28 Oct: `src/clients/muse_spark.py` (`request_answer`, `decode_json_answer`), `src/domain/grade_scale.py`, `tests/fake_client.py`.*
  *Acceptance:* model name, `max_tokens` and 0–20 bounds defined only once; tool behaviour unchanged (existing tests green, only the expected token limit points to the shared constant).

> **Checkpoint B (end of J3):** the vertical slice runs. Otherwise, we do not start E3.

## E3 — Data and search (J4, Fri 30 Oct)

- [x] **E3.1 (M)** [#20](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/20) Splitting of the `Matières` column by series. *Dep.:* E1.1.
  *Acceptance:* 222 offers out of 224; `PUB-062` → Maths, PCT, SVT; `PUB-077` fixed; `PUB-220` and `PUB-223` = "matières non publiées" (subjects not published); coverage of `OK` offers in Classement mode reproduced: C 146 out of 149, D 147 out of 150. *Done on 29 Oct: `src/domain/offer_subjects.py`, tests in `tests/test_offer_subjects.py`. Gap noted in `docs/decisions.md`: after fixing `PUB-077`, the recomputed coverage is C 147 out of 149, D 148 out of 150, and 8 cells carry "—" (6 "Toutes séries" rows in addition to `PUB-220`, `PUB-223`).*
- [x] **E3.2 (M)** [#21](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/21) Finish `data/pages_offres.csv` (19 `a_verifier` rows, 2 `introuvable`).
  *Acceptance:* no `a_verifier` left; `PUB-064` → page 36; `PUB-122` and `PUB-210` resolved or marked "page non établie" (page not established). *Done on 29 Oct: the 19 rows checked one by one in the local PDF (12 `verifie_main`, 7 quarantined `page_non_etablie` because the PDF contradicts their institution, PR #67 review), `PUB-122` → page 48 and `PUB-210` → page 86, 5 `sigle` rows re-checked (seed 21 draw: `PUB-047`, `PUB-068`, `PUB-090`, `PUB-174`, `PUB-185`), schema locked by `tests/test_pages_offres.py`. Detail and pages to restore after E3.3 in `docs/decisions.md`.*
- [x] **E3.3 (M)** [#22](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/22) Audit of 20 randomly drawn `OK` rows (fixed seed) against the local PDF. *Dep.:* E3.2. *Done on 29 Oct: `scripts/sample_audit.py --seed 2026` (test `tests/test_sample_audit.py`), 5 gaps out of 20 after a strict recount in the PR #68 review (`PUB-032`, `PUB-211`, `PUB-215`, `PUB-217`, `PUB-219`), threshold crossed → decision in `docs/decisions.md` (fix + restrict, in E3.5), `data/` unchanged.*
  *Acceptance:* `docs/data-audit.md` with the table of the 20 rows and the gaps. Without this audit, the word "verified" does not appear in the README.
- [x] **E3.4 (S)** [#23](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/23) `faculte_classique` column. *Done on 30 Oct: `scripts/make_faculte_classique.py` + `src/domain/faculte_classique.py` + `data/faculte_classique.csv` (54 `oui`, 145 `non`, `OK` offers with an established page), 60 `OK` rows reviewed through a census of 14 labels, 5 suspect ones checked against the PDF, the others resting on the CSV label (review in `docs/data-audit.md`), 3 INSTI exceptions (`PUB-186`/`187`/`188`, pages 57/59/58), tests `tests/test_faculte_classique.py`. PR #69 review handled in two rounds.*
  *Acceptance:* rule "the name starts with Faculté" applied, then reviewed by hand.
- [x] **E3.5 (L)** [#24](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/24) `lookup_filieres` rewritten: strict access (`OK` row, series in `Bac_recommandé`, entry mode displayed), whole-word ranking, excluded rows returned with their status, plus the data repairs from the E3.3 audit. *Dep.:* E3.1, E3.2, E3.3.
  *Acceptance:* "pilote" does not return Foresterie Tropicale; `PUB-064` appears among the unverified rows; a Concours offer carries "les notes du Bac ne suffisent pas" (BAC grades are not enough); the old `tests/test_lookup_filieres.py` and `data/filieres.csv` are replaced/deleted; E3.3 repairs via a script traced in `docs/data-audit.md` (7 quarantined institutions fixed + pages restored, 5 E3.4 labels (`PUB-053`/`054`/`055` → FSA, `PUB-130` → FDSP, `PUB-141` → FLASH, review `docs/data-audit.md`), regeneration of `data/faculte_classique.csv` + removal of the `REVIEWED_EXCEPTIONS` that became redundant (the test requires an empty stderr) and update of the tests `test_quarantined_faculte_offers_are_excluded` and `test_reviewed_insti_offers_are_excluded`, which assume the pages are still absent, `PUB-032` spaces, `PUB-211` `DEAT`/`EA`, `PUB-189` program, "non publié" marker distinct from 0 on the 15 `OK` rows with `0`/`0` settled against the PDF); "non publié" values are never asserted as facts (`filiere` proofs refused on these fields, report says "le guide ne publie pas…" (the guide does not publish…)).
- [ ] ~~**E3.6 (M)** [#25](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/25) `zoom_cell` — **only if E0.6 = go**. *Dep.:* E0.6.~~ **Dropped: E0.6 = NO GO** (`docs/decisions.md`). Issue closed "won't do".
  ~~*Acceptance:* a blurry cell is re-read, or returned `null`.~~

> **Checkpoint C (end of J4):** audit published; `lookup_filieres` tested on the `false_friend`, `unverified_trap` and `concours_entry` cases.

## E4 — Complete loop on the command line (J5, Sat 31 Oct)

- [x] **E4.1 (L)** [#26](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/26) Tool schemas and rewritten loop (12 steps, step journal reusable by the web). *Dep.:* E2.3, E3.5. *Done on 31 Oct: schemas in `src/agent/tool_schemas.py` (single place), loop on the 8 real tools, journal `{step, tool, args, result, decision}`, `unverified` stop at the 3rd consecutive `verify_report` refusal with `refused_claims` passed on for `build_report` (#27); tests without network in `tests/test_loop.py` and `tests/test_tool_schemas.py`.*
  *Acceptance:* test with a fake model: exact stop at step 12; `ask_student` suspends the loop; a tool error becomes an observation, without a crash; after 3 consecutive `verify_report` refusals, stop with the `unverified` status (at the 3rd refusal, not at the 12th step).
- [x] **E4.2 (M)** [#27](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/27) `build_report`: accessibility, match, guide quotas, ranking average, 3 choices for apresmonbac.bj, "Ce que je n'ai pas pu vérifier". *Dep.:* E2.4. *Done on 31 Oct: sections PRD §3.3/§3.4, 3 choices with a Classical Faculty + allowance/official site reminders, `ValueError` if `verify_report` refuses, `unverified` path (verified ones presented, refused ones by `claim_id` without value), admission/city guard, `Offre_ID`+page required, FR-9 without recommendation, 5 offers at most; tests `tests/test_build_report.py`.*
  *Acceptance:* refuses to produce a report if `verify_report` returns a problem; no admission or city sentence (test on the produced text); in `unverified` status, refused claims go under "Ce que je n'ai pas pu vérifier", never presented as facts.
- [x] **E4.3 (S)** [#28](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/28) System prompt: decide, ask, do not compute, do not invent. *Dep.:* E4.1. *Done on 31 Oct: `SYSTEM_PROMPT` rewritten in `src/agent/prompts.py` (decide the next tool step by step; ask if unreadable, missing or contradictory; never compute or invent; end with `verify_report` then `build_report`), reviewed against PRD §0 and §3.5, coverage locked by `tests/test_prompts.py`; manual replays on the real API, raw outputs in `evals/results/e4.3_blurry_photo.txt` and `evals/results/e4.3_voice_contradicts_sheet.txt`: `blurry_photo` asks for a new photo (Mathematics grade unreadable, nothing invented), `voice_contradicts_sheet` flags the gap of 14 declared against 11.2 on the sheet and keeps the sheet (after series confirmation, confidence absent).*
  *Acceptance:* reviewed against section 0 of the PRD.
- [x] **E4.4 (L)** [#29](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/29) Command-line run of `clear_sheet_d_medecin` (sheet + audio → report). *Dep.:* E4.1, E4.2, E4.3, E1.3, E2.2. *Done on 1 Nov: `python -m src.main --image … --audio …` chains the real loop, JSON journal in `evals/results/`, `ask_student` questions read from stdin; manual replays `e4.4_clear_sheet_d_medecin` and `e4.4_voice_contradicts_sheet`.*
  *Acceptance (O1):* without intervention, verified report containing `PUB-062` and `PUB-133`, with at least 4 tool calls.

> **Checkpoint D (end of J5):** O1 reached. If E4.4 fails, J6 is used to repair it, not to build the web.

## E5 — Web demo (J6, Sun 1 Nov)

- [x] **E5.1 (M)** [#30](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/30) `POST /run` as an event stream (tool, input, output, decision) in place of the 501 of `src/api/server.py`. *Dep.:* E4.1. *Done on 1 Nov: SSE `{step, tool, args, result, decision}` in order, `needs_input` + `POST /answer` with `PendingRunStore` sessions, 413/415 on the server side, error as an `error` event (never a raw 500), key redacted, 501 stub removed; tests `tests/test_api_run.py` (`TestClient`, no network).*
  *Acceptance:* test: the events arrive in order; a question produces the `needs_input` state.
- [x] **E5.2 (L)** [#31](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/31) Interface: photo + audio upload, live trace, agent questions, clickable proofs, fictional examples offered to the judges. *Dep.:* E5.1. *Done on 1 Nov: `web/index.html`, `web/styles.css` and `web/js/` modules (`i18n.js`, `api.js`, `steps.js`, `proofs.js`, `report.js`, `app.js`, `format.js`): photo + voice + fallback text upload, step-by-step SSE trace, questions with an answer field, verified report followed by the claims, each proof of which — grade, quote, `Offre_ID` guide page, calculation — opens its source in a dialog; one-click fictional examples served read-only by `GET /samples/{name}` (allow-list of the 5 files of `data/samples/`), readable at 375 px, displayed content escaped or written as `textContent`; tests `tests/test_web_ui.py` (no network); real full run in Chrome at 375 px (coherent example, 1 series question, verified report `PUB-062` page 36), captures `docs/e5.2-demo-report-375px.png` and `docs/e5.2-demo-375px.png`.*
  *Acceptance:* a judge launches a case without preparing anything; each proof opens its source.
- [x] **E5.3 (M)** [#32](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/32) Degraded mode: the last successful run is replayed with the notice "exécution enregistrée" (recorded run) (FR-11). *Dep.:* E5.1. *Done on 3 Nov:* `web/recorded-run.json` is a static file taken from a real journal of the two fixed fictional samples; `scripts/record_demo.py` regenerates it only from a real run on these files and refuses other inputs, an unexpected sequence of questions or a non-compliant report. The browser preloads the file then replays trace + report in case of interruption, network/infrastructure failure or HTTP 5xx response; HTTP 4xx/429 errors and business/capacity SSE errors do not trigger the replay. The "exécution enregistrée" banner specifies that it is the fictional example, not the current inputs; its report does not claim to have been verified in the current session. Tests: `tests/test_recorded_run.py`, `tests/test_web_ui.py` and browser check after an API error simulation.
  *Acceptance:* network cut, the page displays the recording and the notice.
- [x] **E5.4 (M)** [#33](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/33) Public deployment, usage limit, key on the server side. *Dep.:* E5.2.
- [x] **E5.5 (M)** Visual redesign of the interface (dark theme, animated hero, live agent map, enriched trace, responsive 375 px → desktop). *Dep.:* E5.2. *Done on 3 Nov:* `web/index.html`, `web/styles.css`, new modules `web/js/agent-map.js` (the 8 tools around the agent, a tool lights up when it answers, state "the agent chooses / waits for your answer") and `web/js/motion.js` (appearing on scroll, disabled with `prefers-reduced-motion`); the trace shows who is working (model, code, student) and summarizes each call from its real result. No change of behaviour or server; tests `tests/test_web_ui.py`.
- [x] **E5.6 (M)** Demo on a separate page (`web/demo.html`, presentation in `web/index.html`), Meta model displayed at each step, report in the interface language. *Dep.:* E5.5. *Done on 3 Nov:* `web/js/models.js` associates each tool with its model (Muse Spark 1.3 decides each step and reads sheet/profile, Muse Voice Transcribe 1.0 transcribes, the rest is code) with a test that compares the identifiers with `src/clients/`; `POST /run` accepts `language` (`fr`|`en`, 400 otherwise) which follows the loop up to `build_report(language=...)` (fixed phrases in `src/domain/report_text.py`) and to the system prompt (`system_prompt_for`); French remains byte-for-byte identical. Recorded run in English (`web/recorded-run.en.json`, real run, `scripts/record_demo.py --language en`) loaded according to the language. Tests `tests/test_report_language.py`, `tests/test_recorded_run.py`, `tests/test_web_ui.py`.
- [x] **E5.7 (M)** Combine Muse Spark 1.3 Contributor and Muse Wonder 1.0 (high effort) in the loop. *Dep.:* E5.6. *Done on 3 Nov:* `src/clients/muse_wonder.py` (Wonder turn through the Responses API, history converted then answer rendered in chat format), `loop.run/resume(drafting_model=...)`: the contributor decides up to `lookup_filieres`, Wonder afterwards; fallback to the contributor if Wonder fails; each step of the journal and of the `step` SSE event carries `model`; the demo displays this model, its effort, and a call counter per model; the two recordings (`web/recorded-run*.json`) are regenerated by real runs. Tests `tests/test_muse_wonder.py`, `tests/test_recorded_run.py`, `tests/test_web_ui.py`. *Still to do:* rerun the `evals/` evaluations with this combination before announcing it as better.
  *Acceptance:* public URL on Vercel, redeployed on every push to `main`; the key appears in no served file (`curl` then `grep`); the per-IP quota is tested. From J7, no push to `main` without green local tests.

## E6 — Evaluation (J7, Mon 2 Nov)

- [x] **E6.1 (M)** [#34](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/34) Example files for the 10 cases of `evals/cases.jsonl`. *Dep.:* E0.3. *Done on 3 Nov:* the 10 entries reference fictional images, audio or fallback texts; their assertions declare the mandatory tools, forbidden strings, expected `Offre_ID` and expected question. `tests/test_eval_cases.py` validates the JSONL, the files and the absence of ground-truth loading by `src/`.
  *Acceptance:* no more "sample file TODO" lines; the cases' assertions are never loaded into the agent's prompt, tools or context (no module of `src/` reads `evals/`).
- [x] **E6.2 (M)** [#35](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/35) Evaluation runner. *Dep.:* E4.4. *Done on 3 Nov:* `python -m evals.run`, 11 cases run for real twice (7 then 6 compliant), cost $2.06, `verify_report` replayable (`--replay`).
  *Acceptance:* `evals/results/` contains one raw output per case and a table (compliance, tool calls, questions asked, duration). *Optional:* `verify_report` replayable on a recorded result, without rerunning the agent.
- [x] **E6.3 (L)** [#36](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/36) Fixes until 9 cases out of 10 compliant and 0 claims without proof. *Dep.:* E6.2. *Done on 3 Nov:* 11/11 compliant, `verify_report` replayed empty, two `clear_sheet_d_medecin` with the same verdict, loop cost $2.07 on the committed table.
  *Acceptance (O2 to O5):* table committed, failures explained.
- [x] **E6.4 (S)** [#37](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/37) Demo tested from another device; team registered on the CV platform. *Dep.:* E5.4. *Done on 3 Nov:* complete serie D example with a verified report; owner registered solo, credits claimed ($66 left out of $150, according to their confirmation).
  *Acceptance (O6):* dated log in `docs/decisions.md`; device, network, registration and credits confirmed by the owner.

> **Checkpoint E (end of J7):** O1 to O6 measured. Otherwise, we reduce the scope, we add nothing.

## E7 — Submission (J8, Tue 3 Nov, freeze in the evening; J9 margin)

- [x] **E7.1 (M)** [#38](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/38) Final README: real status, V1 section, models actually used, limits, team; `docs/impact.md` with the sourced official figure. *Dep.:* E6.3.
  *Acceptance:* no `TODO` in the README; each claim matches a committed result. *Done on 3 Nov:* README and `docs/impact.md` without `TODO`; figure 77,101 (press relaying the Office, not an official page); 4 Meta models; evaluation 11/11; solo team. Video link added with E7.2. **Still open:** README opening in a private window (to check on GitHub).
- [x] **E7.2 (L)** [#39](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/39) 3-minute video, English subtitles, strong moment first (`docs/demo-script.md`). *Dep.:* E6.3. *Done on 3 Nov:* FR/EN voice-over texts and production plan in `docs/video/`; video published on YouTube (https://youtu.be/NGVMj1RnXyQ), 4 exports of 2:58 (YouTube and vertical, English and French). The video files are not in the repository (176 MB: the Vercel preview had failed with them).
  *Acceptance:* duration ≤ 3:00; each shot shows a real run.
- [ ] **E7.3 (S)** [#40](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/40) X post with the video. *Dep.:* E7.2.
  *Acceptance:* link noted for the submission.
- [ ] **E7.4 (S)** [#41](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/41) Pre-submission check: search for secrets in the tree and the history, repository open without login, no personal path. *Dep.:* E7.1.
  *Acceptance:* checklist of section 15 of the PRD fully ticked.
- [ ] **E7.5 (S)** [#42](https://github.com/AresGn/PathProof-Meta-Hackathon/issues/42) Submission on the CV platform. *Dep.:* everything.
  *Acceptance:* acknowledgement of receipt archived. **Target: the evening of 3 Nov**; limit: 4 Nov, 21:00 ET = 03:00 in Porto-Novo.

---

## Cuts if delay sets in (in order)
1. X post and Viral prize (E7.3).
2. Evaluation cases reduced to 7, keeping `voice_contradicts_sheet`, `unverified_trap` and `false_friend`.

**Not to be cut:** the 20-row audit (otherwise remove the word "verified"), `verify_report`, the degraded mode.

## Points of vigilance
- **J4 and J5 are heavy.** E3.5 and E4.1 are the two riskiest L stories; checkpoint B protects J5.
- **`muse-spark-1.3` reasons before answering, and these tokens count in `max_tokens`.** Measured on 27 Oct: a one-word answer ("ok") consumed 228 reasoning tokens; with `max_tokens=20`, the content comes back empty (`finish_reason = length`). Plan a large limit in the loop and the tools, and track the real spending ($150 budget).
- Environment: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (`.venv/` is ignored by git).
- `pytest` alone fails at collection (the `src` package is not on the path): use `python -m pytest`.
