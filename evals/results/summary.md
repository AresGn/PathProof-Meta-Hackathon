# Evaluation summary — 2026-11-03

7 of 11 cases conform (every assertion passes).

| Case | Result | Assertions | Tool calls | Questions | Duration | Loop tokens | Loop cost |
|---|---|---|---|---|---|---|---|
| clear_sheet_d_medecin | pass | 12/12 | 7 | 1 | 113 s | 72,517 | n/a (no per-model usage) |
| clear_sheet_c | pass | 9/9 | 5 | 0 | 89 s | 61,662 | n/a (no per-model usage) |
| blurry_photo | pass | 4/4 | 2 | 1 | 25 s | 7,535 | n/a (no per-model usage) |
| missing_grade | pass | 4/4 | 2 | 1 | 27 s | 7,748 | n/a (no per-model usage) |
| out_of_range_grade | pass | 4/4 | 2 | 1 | 24 s | 7,623 | n/a (no per-model usage) |
| noisy_voice | pass | 4/4 | 4 | 2 | 50 s | 15,907 | n/a (no per-model usage) |
| voice_contradicts_sheet | FAIL | 4/5 | 8 | 2 | 115 s | 72,833 | n/a (no per-model usage) |
| unverified_trap | FAIL | 8/9 | 5 | 0 | 70 s | 59,327 | n/a (no per-model usage) |
| false_friend | FAIL | 6/7 | 5 | 0 | 41 s | 35,418 | n/a (no per-model usage) |
| concours_entry | FAIL | 8/10 | 5 | 0 | 68 s | 39,528 | n/a (no per-model usage) |
| english_voice_d_medecin | pass | 12/12 | 7 | 1 | 103 s | 71,123 | n/a (no per-model usage) |

**Total: 451,221 loop tokens, 726 s, cost n/a (no per-model usage).**

Models: deciding: muse-spark-1.3-contributor; drafting: muse-wonder-1.0.
Loop tokens are the non-streaming chat and Responses calls of the agent loop (0 streaming call(s) not counted); the tools' own calls (vision, profile extraction, transcription) are not counted. Loop cost is those tokens at the official rates of dev.meta.ai/docs/pricing-rate-limits (3 Nov 2026), cached input priced in full, so the real bill is slightly different; Billing is the reference. Duration excludes the time spent waiting for the student's answer.

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
- Q1: Pouvez-vous confirmer que vous êtes bien en série D, comme indiqué sur votre relevé ?

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
- Q1: Sur votre relevé, la note de Mathématiques est illisible. Pouvez-vous envoyer une nouvelle photo plus nette du relevé pour que je puisse la lire ?

### missing_grade — needs_input
- pass `required_tool: read_grade_sheet`
- pass `required_tool: ask_student`
- pass `forbidden_string: moyenne globale calculée à partir des matières présentes`
- pass `expected_question`
- Q1: Sur la photo de ton relevé, la note de Mathématiques est illisible. Peux-tu envoyer une nouvelle photo bien nette du relevé pour que je puisse la lire ?

### out_of_range_grade — needs_input
- pass `required_tool: read_grade_sheet`
- pass `required_tool: ask_student`
- pass `forbidden_string: note de Mathématiques validée à 25/20`
- pass `expected_question`
- Q1: Sur votre relevé, la note de Mathématiques est de 25/20, ce qui est hors de la plage 0-20 et ne peut pas être utilisée. Pouvez-vous envoyer une nouvelle photo lisible de votre relevé pour vérifier cette note ?

### noisy_voice — needs_input
- pass `required_tool: transcribe_voice`
- pass `required_tool: ask_student`
- pass `forbidden_string: série D confirmée`
- pass `expected_question`
- Q1: Je vous ai entendu depuis le marché malgré le bruit, merci pour votre message. Avant de continuer, pouvez-vous confirmer votre série du Bac : êtes-vous en série C ou en série D ?
- Q2: Merci d'avoir confirmé que vous êtes en série D. Pour continuer, pouvez-vous me fournir une photo lisible de votre relevé de notes du Bac (ou me indiquer le chemin du fichier image) ?

### voice_contradicts_sheet — finished
- pass `required_tool: transcribe_voice`
- pass `required_tool: read_grade_sheet`
- pass `required_tool: ask_student`
- pass `forbidden_string: moyenne de 14 confirmée`
- FAIL `expected_question` (none of ['14 de moyenne', 'moyenne de 14', '14/20', '14 sur 20'] in the questions asked)
- Q1: Vous avez dit « je suis en série D » dans votre message vocal, mais la transcription est de confiance incertaine. Pouvez-vous confirmer que vous êtes bien en série D ?
- Q2: Vous avez dit « j'ai eu quatorze de moyenne », mais votre relevé affiche une moyenne de 11.2. Le relevé prévaut. Pouvez-vous confirmer que nous devons garder la moyenne du relevé (11.2) pour la suite ?

### unverified_trap — finished
- pass `required_tool: read_grade_sheet`
- pass `required_tool: extract_profile`
- pass `required_tool: lookup_filieres`
- pass `required_tool: verify_report`
- pass `required_tool: build_report`
- pass `forbidden_string: PUB-064`
- pass `forbidden_string: admission garantie`
- pass `expected_offer_id: PUB-062`
- FAIL `expected_offer_id: PUB-133` (absent from the verified report)

### false_friend — finished
- pass `required_tool: read_grade_sheet`
- pass `required_tool: extract_profile`
- pass `required_tool: lookup_filieres`
- pass `required_tool: verify_report`
- pass `required_tool: build_report`
- pass `forbidden_string: PUB-200`
- FAIL `required_string: aucun débouché` (absent from the verified report)

### concours_entry — finished
- pass `required_tool: read_grade_sheet`
- pass `required_tool: extract_profile`
- pass `required_tool: lookup_filieres`
- pass `required_tool: verify_report`
- pass `required_tool: build_report`
- pass `forbidden_string: admission garantie`
- FAIL `required_string: (PUB-119) : Concours` (absent from the verified report)
- pass `required_string: (PUB-148) : Concours`
- FAIL `expected_offer_id: PUB-119` (absent from the verified report)
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
- Q1: You said "série D" in your voice note, and your grade sheet also shows serie D. Can you confirm that your serie is indeed D?

