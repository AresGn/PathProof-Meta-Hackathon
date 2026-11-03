# data/samples — fichiers d'exemple fictifs

Only FICTIONAL grade sheets belong here. No real student data, ever.

Tous les fichiers de ce dossier sont **fictifs** : noms manifestement inventés, numéro de table `000`, aucune photo, aucun cachet, aucune signature. Les valeurs ci-dessous sont la vérité terrain des tests de `read_grade_sheet` (E1.3) et des évaluations (E6.1).

Régénérer : `python scripts/make_grade_sheets.py` (relevés) et `python scripts/make_voice_notes.py` (voix, clé `ELEVENLABS_API_KEY` dans `.env`). Les coefficients sont ceux du groupe 1 de `data/coefficients_bac_benin.json`.

## `releve_serie_d.jpg` — relevé net, série D (fictif)

Élève : « Mlle EXEMPLE Ayaba Fictive ». Imprimé, net.

| Matière | Note /20 | Coeff | Points |
|---|---|---|---|
| ANGLAIS | 8 | 2 | 16 |
| FRANCAIS | 9,5 | 2 | 19 |
| HISTOIRE & GEOGRAPHIE | 7 | 2 | 14 |
| MATHEMATIQUES | 12 | 4 | 48 |
| PHILOSOPHIE | 8 | 2 | 16 |
| PHYSIQUE, CHIMIE ET TECHNOLOGIE | 12 | 4 | 48 |
| SCIENCES DE LA VIE ET DE LA TERRE | 15 | 5 | 75 |
| *Total des épreuves écrites* | *11,24* | *21* | *236* |
| EDUCATION PHYSIQUE ET SPORTIVE | 10,5 | 1 | 10,5 |
| **Total du 1er groupe** | **11,20** | **22** | **246,5** |

- Moyenne générale affichée : **11,20/20** (valeur exacte 246,5 / 22 = 11,2045).
- Décision : Admise, mention Passable.
- Moyenne de classement Médecine (SVT×5 + Maths×4 + PCT×4) / 13 = 171 / 13 = **13,15** (attendu, pas imprimé sur le relevé).

## `releve_serie_c.jpg` — relevé net, série C (fictif)

Élève : « M. SPECIMEN Koffi Imaginaire ». Imprimé, net.

| Matière | Note /20 | Coeff | Points |
|---|---|---|---|
| ANGLAIS | 12 | 2 | 24 |
| FRANCAIS | 11 | 2 | 22 |
| HISTOIRE & GEOGRAPHIE | 10 | 2 | 20 |
| MATHEMATIQUES | 14 | 6 | 84 |
| PHILOSOPHIE | 9 | 2 | 18 |
| PHYSIQUE, CHIMIE ET TECHNOLOGIE | 13 | 5 | 65 |
| SCIENCES DE LA VIE ET DE LA TERRE | 12 | 2 | 24 |
| *Total des épreuves écrites* | *12,24* | *21* | *257* |
| EDUCATION PHYSIQUE ET SPORTIVE | 15 | 1 | 15 |
| **Total du 1er groupe** | **12,36** | **22** | **272** |

- Moyenne générale affichée : **12,36/20** (valeur exacte 272 / 22 = 12,3636).
- Décision : Admis, mention Assez bien.

## `releve_serie_d_flou.jpg` — relevé flou (fictif)

Même contenu que `releve_serie_d.jpg`, photographié de travers (rotation 1,5°) avec un flou gaussien réel sur toute l'image.

- **Note illisible :** la ligne MATHEMATIQUES, cellules « Note /20 », « Coeff » et « Points obtenus » (flou fort). Seul « Sur 80 » reste lisible.
- Comportement attendu : `lisible = false` et `note = null` pour MATHEMATIQUES, puis `ask_student`. Ne pas déduire la note du total 236 : c'est un calcul que le modèle ne fait pas.
- Toutes les autres valeurs restent lisibles et identiques au relevé D.

## `note_vocale_coherente.mp3` — note vocale cohérente (fictif), 44 s

Voix de synthèse ElevenLabs (`eleven_multilingual_v2`, voix féminine jeune, accent d'Afrique de l'Ouest). Même élève que le relevé D. Texte dit :

> Bonjour... Alors, euh, je suis en terminale, série D, D comme Daniel. Au bac, j'ai eu onze virgule deux de moyenne. Ce que j'aime le plus, c'est la biologie, les SVT... vraiment, c'est ma matière préférée. Plus tard, j'aimerais travailler dans la santé... peut-être médecin. Depuis petite, je veux soigner les gens, aider ma famille, mon quartier. Pour la ville, euh... je préfère rester à Cotonou, près de mes parents. Et, honnêtement, j'aurai besoin d'une bourse, parce que les études, ça coûte cher chez nous. Voilà... merci de m'écouter.

Valeurs attendues : `serie_declaree` = D, `moyenne_declaree` = 11,2 (égale au relevé), `interets` = biologie / SVT, soigner les gens, `metier_vise` = médecin, ville = Cotonou, bourse = oui.

## `note_vocale_contradictoire.mp3` — note vocale contradictoire (fictif), 40 s

Même voix. Contient mot pour mot le texte du PRD §2.1, entouré d'hésitations :

> Euh... oui, bonjour. Bonjour, je suis en série D, j'ai eu 14 de moyenne. Voilà... J'aime beaucoup la biologie et j'aimerais travailler dans la santé, peut-être médecin. Au lycée, ce que je préférais, c'était les travaux pratiques en SVT, avec le microscope. Je préfère rester à Cotonou, et j'aurai besoin d'une bourse. Mes parents m'ont dit de bien chercher les filières où il y a des bourses... Donc, euh, je compte sur vous pour m'aider à choisir. Merci beaucoup, hein.

Valeurs attendues : `serie_declaree` = D, `moyenne_declaree` = 14, en contradiction avec 11,20 sur `releve_serie_d.jpg`. L'agent signale l'écart, demande à l'élève et retient le relevé.

Les deux transcriptions ont été vérifiées avec ElevenLabs Scribe : « série D », « 11,2 » et « 14 » sont bien reconnus.

## Fichiers supplémentaires d'évaluation E6.1 (tous fictifs)

| Fichier | Contenu fictif |
|---|---|
| `releve_serie_d_note_manquante.jpg` | Relevé fictif série D avec une note Mathématiques manquante ; ni points totaux ni moyenne affichés. Généré par `scripts/make_grade_sheets.py`. |
| `releve_serie_d_note_25.jpg` | Relevé fictif série D avec Mathématiques à 25/20 ; ni points totaux ni moyenne affichés, la confirmation est demandée. Généré par `scripts/make_grade_sheets.py`. |
| `profil_serie_c.txt` | Texte fictif de secours pour la voix d'un élève de série C. |
| `note_vocale_bruitee.mp3` | Note vocale fictive de 33 s (même voix), bruit de marché en fond et rafale de bruit sur la lettre de la série. Générée par `scripts/make_voice_notes.py`. |
| `note_vocale_anglais.mp3` | Note vocale fictive de 42 s en anglais (même voix), jumelle de `note_vocale_coherente.mp3` : série D, 11,2, « maybe as a doctor ». Générée par `scripts/make_voice_notes.py`. |
| `intention_pharmacien.txt` | Texte fictif de secours : souhait de devenir pharmacien. |
| `intention_pilote.txt` | Texte fictif de secours : souhait de devenir pilote de ligne. |
| `intention_infirmier.txt` | Texte fictif de secours : souhait de devenir infirmier. |

## Inventaire des autres fichiers d'exemple (tous fictifs)

- `releve_serie_d.jpg` — relevé fictif net de série D.
- `releve_serie_c.jpg` — relevé fictif net de série C.
- `releve_serie_d_flou.jpg` — relevé fictif flou de série D.
- `note_vocale_coherente.mp3` — voix fictive cohérente avec le relevé D.
- `note_vocale_contradictoire.mp3` — voix fictive qui annonce 14 de moyenne.
- `vertical_slice_serie_d.json` — fixture fictive pour la tranche verticale sans vision ni voix.

Les dix entrées du PRD, plus `english_voice_d_medecin` (jury surtout anglophone), leurs fichiers et leurs assertions machine-vérifiables sont
déclarés dans `evals/cases.jsonl`. Les textes `.txt` sont des solutions de
secours d'entrée, pas des transcriptions audio mesurées.
Comparaison des chaînes : sous-chaîne, sans tenir compte de la casse ni
des accents.

- `forbidden_strings` : absentes du rapport vérifié et des questions posées.
- `required_strings` : présentes dans le rapport vérifié (texte rendu par
  `build_report`, par exemple « 13,15 / 20 » ou « (PUB-119) : Concours »).
- `required_tools` : outils appelés au moins une fois. `compute_ranking_average`
  n'y figure pas : `lookup_filieres` renvoie déjà la moyenne qu'il calcule, et
  `verify_report` recalcule chaque preuve `calc`.
- `expected_question` : liste d'alternatives ; au moins une apparaît dans une
  question posée par `ask_student`. `null` : aucune question attendue.

Les `.txt` se passent au CLI avec `--voice-text` ; `noisy_voice` se lance
avec `--audio` seul. Transcription mesurée de `note_vocale_bruitee.mp3` par
`transcribe_voice` le 3 nov : « … Je suis en terminale, série euh ce que
j'aime c'est la biologie… », `confidence = null` (l'API n'en renvoie pas,
E0.5) : la série est inaudible, l'agent doit la demander (FR-4).
