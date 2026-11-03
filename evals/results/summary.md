# Evaluation summary — 2026-11-03

11 of 11 cases conform (every assertion passes).

| Case | Result | Assertions | Tool calls | Questions | Duration | Loop tokens | Loop cost |
|---|---|---|---|---|---|---|---|
| clear_sheet_d_medecin | pass | 12/12 | 8 | 1 | 99 s | 78,717 | $0.38 |
| clear_sheet_c | pass | 9/9 | 5 | 0 | 77 s | 62,038 | $0.36 |
| blurry_photo | pass | 4/4 | 2 | 1 | 18 s | 7,272 | $0.00 |
| missing_grade | pass | 4/4 | 2 | 1 | 15 s | 7,494 | $0.00 |
| out_of_range_grade | pass | 4/4 | 2 | 1 | 16 s | 7,665 | $0.00 |
| noisy_voice | pass | 4/4 | 4 | 2 | 40 s | 16,352 | $0.00 |
| voice_contradicts_sheet | pass | 5/5 | 8 | 2 | 102 s | 72,742 | $0.32 |
| unverified_trap | pass | 9/9 | 5 | 0 | 64 s | 60,480 | $0.35 |
| false_friend | pass | 7/7 | 5 | 0 | 36 s | 36,020 | $0.14 |
| concours_entry | pass | 10/10 | 5 | 0 | 51 s | 42,087 | $0.20 |
| english_voice_d_medecin | pass | 12/12 | 7 | 1 | 79 s | 66,951 | $0.33 |

**Total: 457,818 loop tokens, 596 s, cost $2.08.**

Models that decided the steps (steps, read from the journals): muse-spark-1.3-contributor (39), muse-wonder-1.0 (14).
Loop tokens are the non-streaming chat and Responses calls of the agent loop (0 streaming call(s) not counted); the tools' own calls (vision, profile extraction, transcription) are not counted. Loop cost is those tokens at the official rates of dev.meta.ai/docs/pricing-rate-limits (3 Nov 2026), cached input priced in full, so the real bill is slightly different; Billing is the reference. Duration excludes the time spent waiting for the student's answer.

## Remaining failures (E6.3)

None: 11 of 11 cases conform, including the 10 PRD cases. `verify_report` replayed on every finished journal returned an empty problem list.

Two consecutive `clear_sheet_d_medecin` runs both passed (`evals/results/e6.3_clear_sheet_d_medecin_run1.json` and `evals/results/2026-11-03/clear_sheet_d_medecin.json`). After the PR #88 review, `false_friend`, `unverified_trap`, `concours_entry` and `clear_sheet_d_medecin` were rerun; all four still pass.

Loop cost of this committed table: **$2.08**. Extra loop runs sit on top of that. With E6.2 ($2.06) the measured loop spend stays under the $150 credit budget; Billing is the reference.

## Detail per assertion

### clear_sheet_d_medecin — finished
- pass `required_tool: transcribe_voice`
- pass `required_tool: read_grade_sheet`
- pass `required_tool: extract_profile`
- pass `required_tool: lookup_filieres`
- pass `required_tool: verify_report`
- pass `required_tool: build_report`
- pass `forbidden_string: PUB-064`
- pass `forbidden_string: admission garantie`
- pass `required_string: 13,15 / 20`
- pass `required_string: Faculté classique : oui`
- pass `expected_offer_id: PUB-062`
- pass `expected_offer_id: PUB-133`
- Q1: Confirmez-vous que votre série au bac est la série D

### clear_sheet_c — finished
- pass `required_tool: read_grade_sheet`
- pass `required_tool: extract_profile`
- pass `required_tool: lookup_filieres`
- pass `required_tool: verify_report`
- pass `required_tool: build_report`
- pass `forbidden_string: admission garantie`
- pass `required_string: Faculté classique : oui`
- pass `expected_offer_id: PUB-062`
- pass `expected_offer_id: PUB-133`

### blurry_photo — needs_input
- pass `required_tool: read_grade_sheet`
- pass `required_tool: ask_student`
- pass `forbidden_string: note de Mathématiques égale à 12`
- pass `expected_question`
- Q1: Sur votre relevé, la note de Mathématiques est illisible. Pouvez-vous envoyer une nouvelle photo nette du relevé où cette note est lisible ?

### missing_grade — needs_input
- pass `required_tool: read_grade_sheet`
- pass `required_tool: ask_student`
- pass `forbidden_string: moyenne globale calculée à partir des matières présentes`
- pass `expected_question`
- Q1: Sur la photo de ton relevé, la note de Mathématiques est illisible. Peux-tu envoyer une nouvelle photo nette du relevé où la note de Mathématiques est lisible ?

### out_of_range_grade — needs_input
- pass `required_tool: read_grade_sheet`
- pass `required_tool: ask_student`
- pass `forbidden_string: note de Mathématiques validée à 25/20`
- pass `expected_question`
- Q1: Votre relevé indique 25/20 en Mathématiques, ce qui dépasse la plage 0-20. Pouvez-vous envoyer une nouvelle photo lisible du relevé pour vérifier cette note ?

### noisy_voice — needs_input
- pass `required_tool: transcribe_voice`
- pass `required_tool: ask_student`
- pass `forbidden_string: série D confirmée`
- pass `expected_question`
- Q1: Pour confirmer avant de continuer, vous êtes en série C ou en série D ? Merci de répondre par C ou D.
- Q2: Sans votre relevé de notes je ne peux pas vérifier les filières. Pouvez-vous fournir une photo lisible de votre relevé de notes (chemin du fichier image) pour continuer ?

### voice_contradicts_sheet — finished
- pass `required_tool: transcribe_voice`
- pass `required_tool: read_grade_sheet`
- pass `required_tool: ask_student`
- pass `forbidden_string: moyenne de 14 confirmée`
- pass `expected_question`
- Q1: Pouvez-vous confirmer que vous êtes bien en série D comme indiqué sur votre relevé ? Répondez oui ou indiquez votre série.
- Q2: Vous avez déclaré une moyenne de 14/20, mais votre relevé affiche 11.2/20. Pouvez-vous confirmer que nous devons garder la valeur du relevé, soit 11.2/20, pour la suite de l'orientation ?

### unverified_trap — finished
- pass `required_tool: read_grade_sheet`
- pass `required_tool: extract_profile`
- pass `required_tool: lookup_filieres`
- pass `required_tool: verify_report`
- pass `required_tool: build_report`
- pass `forbidden_string: PUB-064`
- pass `forbidden_string: admission garantie`
- pass `expected_offer_id: PUB-062`
- pass `expected_offer_id: PUB-133`

### false_friend — finished
- pass `required_tool: read_grade_sheet`
- pass `required_tool: extract_profile`
- pass `required_tool: lookup_filieres`
- pass `required_tool: verify_report`
- pass `required_tool: build_report`
- pass `forbidden_string: PUB-200`
- pass `required_string: aucun débouché`

### concours_entry — finished
- pass `required_tool: read_grade_sheet`
- pass `required_tool: extract_profile`
- pass `required_tool: lookup_filieres`
- pass `required_tool: verify_report`
- pass `required_tool: build_report`
- pass `forbidden_string: admission garantie`
- pass `required_string: (PUB-119) : Concours`
- pass `required_string: (PUB-148) : Concours`
- pass `expected_offer_id: PUB-119`
- pass `expected_offer_id: PUB-148`

### english_voice_d_medecin — finished
- pass `required_tool: transcribe_voice`
- pass `required_tool: read_grade_sheet`
- pass `required_tool: extract_profile`
- pass `required_tool: lookup_filieres`
- pass `required_tool: verify_report`
- pass `required_tool: build_report`
- pass `forbidden_string: PUB-064`
- pass `forbidden_string: admission garantie`
- pass `required_string: 13,15 / 20`
- pass `required_string: Faculté classique : oui`
- pass `expected_offer_id: PUB-062`
- pass `expected_offer_id: PUB-133`
- Q1: Can you confirm that you are in série D? Please reply with D to confirm before I continue.

