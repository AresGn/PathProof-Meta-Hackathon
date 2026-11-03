# Evaluation summary — 2026-11-03

6 of 11 cases conform (every assertion passes).

| Case | Result | Assertions | Tool calls | Questions | Duration | Loop tokens | Loop cost |
|---|---|---|---|---|---|---|---|
| clear_sheet_d_medecin | pass | 12/12 | 7 | 1 | 97 s | 71,525 | $0.36 |
| clear_sheet_c | pass | 9/9 | 5 | 0 | 88 s | 60,821 | $0.35 |
| blurry_photo | pass | 4/4 | 2 | 1 | 19 s | 7,533 | $0.00 |
| missing_grade | pass | 4/4 | 2 | 1 | 19 s | 7,354 | $0.00 |
| out_of_range_grade | FAIL | 3/4 | 2 | 1 | 22 s | 7,603 | $0.00 |
| noisy_voice | pass | 4/4 | 4 | 2 | 52 s | 15,942 | $0.00 |
| voice_contradicts_sheet | FAIL | 4/5 | 8 | 2 | 102 s | 73,316 | $0.34 |
| unverified_trap | FAIL | 8/9 | 5 | 0 | 93 s | 59,656 | $0.35 |
| false_friend | FAIL | 6/7 | 5 | 0 | 42 s | 35,422 | $0.14 |
| concours_entry | FAIL | 8/10 | 5 | 0 | 64 s | 39,144 | $0.17 |
| english_voice_d_medecin | pass | 12/12 | 7 | 1 | 111 s | 68,905 | $0.35 |

**Total: 447,221 loop tokens, 708 s, cost $2.06.**

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
- Q1: Sur la photo de votre relevé, la note de Mathématiques est illisible. Pouvez-vous envoyer une nouvelle photo plus nette de votre relevé ?

### missing_grade — needs_input
- pass `required_tool: read_grade_sheet`
- pass `required_tool: ask_student`
- pass `forbidden_string: moyenne globale calculée à partir des matières présentes`
- pass `expected_question`
- Q1: Sur votre relevé, la note de Mathématiques est illisible. Pouvez-vous envoyer une nouvelle photo bien nette du relevé pour que je puisse la lire ?

### out_of_range_grade — needs_input
- pass `required_tool: read_grade_sheet`
- pass `required_tool: ask_student`
- pass `forbidden_string: note de Mathématiques validée à 25/20`
- FAIL `expected_question` (none of ['25/20', '25 sur 20', '25 / 20'] in the questions asked)
- Q1: Sur la photo de votre relevé, la note lue en Mathématiques est 25, ce qui est hors de l'échelle 0-20. Pouvez-vous renvoyer une nouvelle photo lisible du relevé pour vérifier cette note ?

### noisy_voice — needs_input
- pass `required_tool: transcribe_voice`
- pass `required_tool: ask_student`
- pass `forbidden_string: série D confirmée`
- pass `expected_question`
- Q1: Je n'ai pas bien entendu ta série dans ta note vocale (le marché faisait beaucoup de bruit). Peux-tu me confirmer : es-tu en série C ou en série D ?
- Q2: Merci pour ta confirmation en série D. Pour continuer, peux-tu me fournir la photo de ton relevé de notes (le chemin du fichier image) afin que je puisse lire tes notes ?

### voice_contradicts_sheet — finished
- pass `required_tool: transcribe_voice`
- pass `required_tool: read_grade_sheet`
- pass `required_tool: ask_student`
- pass `forbidden_string: moyenne de 14 confirmée`
- FAIL `expected_question` (none of ['14 de moyenne', 'moyenne de 14', '14/20', '14 sur 20'] in the questions asked)
- Q1: Vous avez dit « je suis en série D » dans votre message vocal, et votre relevé de notes indique aussi la série D. Pouvez-vous confirmer que vous êtes bien en série D ?
- Q2: Vous avez dit « j'ai eu quatorze quatorze de moyenne », mais votre relevé de notes affiche une moyenne de 11.2. Pouvez-vous confirmer que la moyenne à retenir est bien celle du relevé (11.2) ? Sinon, merci de fournir un nouveau relevé.

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
- Q1: Vous avez dit être en série D : pouvez-vous confirmer que votre série est bien D ?

