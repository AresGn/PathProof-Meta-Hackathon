# Plan de production de la vidéo (story E7.2, issue #39)

Vidéo **sans visage** : un écran de navigateur filmé, une voix off, des sous-titres anglais. 3:00 au plus, en deux formats (YouTube horizontal, X vertical) et deux langues de voix (anglais, français).
Textes de la voix : [`script-en.md`](script-en.md) et [`script-fr.md`](script-fr.md). Séquence de départ : `docs/prd.md` §13 et `docs/demo-script.md`.

## 1. Ce qu'on livre

| Priorité | Fichier | Format | Voix | Sous-titres anglais |
|---|---|---|---|---|
| **P1** | `pathproof_youtube_en.mp4` | 1920×1080, 16:9 | anglais | piste `.srt` (YouTube) + `pathproof_en.srt` |
| **P2** | `pathproof_x_en_vertical.mp4` | 1080×1920, 9:16 | anglais | incrustés |
| P3 | `pathproof_youtube_fr.mp4` | 1920×1080 | français | piste `.srt` (cues anglais calés sur la voix française) |
| P3 | `pathproof_x_fr_vertical.mp4` | 1080×1920 | français | incrustés |

Le jury est surtout anglophone : **P1 est ce qui est soumis**. P2 sert au post X (E7.3). P3 se fait s'il reste du temps ; la soumission ne doit pas en dépendre.
Toutes les versions durent **2:58 au plus** (limite 3:00), même découpage en blocs, mêmes numéros de plans.

> **À vérifier avant de publier sur X :** un compte X non Premium plafonne la durée d'une vidéo (je crois 2:20, non vérifié). Si le compte est concerné, il faudra une version raccourcie, donc un second jeu de textes : à décider avant de monter P2.

## 2. Qui fait quoi

| Qui | Tâche |
|---|---|
| **Vous** | Filmer l'écran (§4), enregistrer la voix (§5), choisir le titre, la miniature et le compte X, publier. |
| **Agent de code (montage)** | Assembler, couper les attentes, zoomer, incruster cartes et sous-titres, régler le son, exporter et contrôler les durées (§6). Il travaille avec `ffmpeg` en ligne de commande, sur des fichiers que vous déposez dans `video/raw/`. |
| **Ni l'un ni l'autre** | Inventer un plan. Tout ce qui est à l'écran vient d'une exécution réelle ou d'une carte clairement marquée (§7). |

Les médias ne vont pas dans le dépôt (lourds, et les rushs peuvent contenir du bruit) : `video/` reste hors de git. Le dépôt ne garde que ces trois documents, et le `.srt` final si vous voulez le versionner.

## 3. Découpage : 16 plans, 6 blocs de voix

Fenêtres imposées par le PRD §13 et par l'issue #39. Débit contrôlé : l'anglais reste sous 2,3 mots/s, le français sous 2,6 mots/s, ce qui laisse des silences pour l'interface.

| Bloc | Fenêtre | Plans | Mots EN (mots/s) | Mots FR (mots/s) |
|---|---|---|---|---|
| V1 moment fort | 0:00–0:20 | S01, S02 | 40 (2,0) | 42 (2,1) |
| V2 problème et chiffre | 0:20–0:45 | S03, S04 | 47 (1,9) | 50 (2,0) |
| V3a cas complet : entrées | 0:45–1:05 | S05, S06 | 42 (2,1) | 41 (2,1) |
| V3b cas complet : trace | 1:05–1:30 | S07, S08 | 41 (1,6) | 41 (1,6) |
| V3c cas complet : preuves | 1:30–2:00 | S09, S10, S11 | 57 (1,9) | 64 (2,1) |
| V4 cas difficile | 2:00–2:30 | S12, S13 | 54 (1,8) | 55 (1,8) |
| V5 évaluations et ligne écartée | 2:30–2:50 | S14, S15 | 45 (2,3) | 51 (2,6) |
| V6 nouveau, limites, équipe | 2:50–2:58 | S16 | 16 (2,0) | 17 (2,1) |
| **Total** | **2:58** | | **342** | **361** |

### Plan par plan

« Exécution » = capture d'une vraie exécution de PathProof. « Carte » = image faite au montage, sans exécution, marquée comme telle.

| Plan | Fenêtre | À l'écran | Source |
|---|---|---|---|
| S01 | 0:00–0:10 | Le relevé fictif (`releve_serie_d.jpg`, moyenne **11,20**) et la transcription de la note vocale « … j'ai eu 14 de moyenne » côte à côte. Option : l'extrait audio de la note, à −22 dB sous la voix | Exécution (clic sur **Contradictory voice note**, étape `transcribe_voice`) + le fichier d'entrée |
| S02 | 0:10–0:20 | L'agent s'arrête : « Vous avez déclaré 14/20, mais votre relevé affiche 11.2/20… », statut « Agent is waiting for your answer » | Exécution (même prise, 2e question) |
| S03 | 0:20–0:32 | **Carte** : « 77 101 candidats au Bac 2026 », source « données de l'Office du Baccalauréat relayées par Bénin Web TV, 14 juin 2026 ». Un seul chiffre dans toute la vidéo | Carte (`docs/impact.md`) |
| S04 | 0:32–0:45 | Dans un rapport réel, la section « Ranking average » : formule `M = Σ(mi·ci)/Σci (guide, page 8)` et les trois matières avec leurs coefficients | Exécution (rapport de S09) |
| S05 | 0:45–0:55 | `demo.html`, clic sur **Clear serie D sheet + matching voice note** ; mention « fictional, synthetic voice » | Exécution |
| S06 | 0:55–1:05 | Le lancement : la carte de l'agent s'allume outil par outil (accéléré ×3, pastille « ×3 » visible) | Exécution |
| S07 | 1:05–1:17 | Gros plan sur la trace : pastilles « Decided by Muse Spark 1.3 Contributor », « Run by Muse Voice Transcribe 1.0 », « Run by Muse Spark 1.3 » | Exécution |
| S08 | 1:17–1:30 | La question, la réponse « D », puis `lookup_filieres` « Run by deterministic code · no model » et l'étape Muse Wonder 1.0 (« effort high ») ; attente accélérée ×4 | Exécution |
| S09 | 1:30–1:42 | Le bandeau « Verified report — every claim checked by code », défilement jusqu'à Médecine **13,15** | Exécution |
| S10 | 1:42–1:52 | Clic sur les puces de preuve : « Grade · SVT 15/20 », « Quote · "peut-être médecin" » (fenêtre de preuve avec la citation surlignée) | Exécution |
| S11 | 1:52–2:00 | Clic sur « Guide · PUB-062 (page 36) » puis « Result · 13.15 » ; fin sur l'étape « All claims proven » | Exécution |
| S12 | 2:00–2:12 | Clic sur **Blurry sheet** : le relevé flou, l'agent le lit | Exécution |
| S13 | 2:12–2:30 | La question « la note de Mathématiques est illisible… » et l'agent en attente ; puis une carte : « SAM 3.1 : tableau trouvé, cellule jamais trouvée (0/3) → abandonné », source `docs/spikes/sam` | Exécution + carte |
| S14 | 2:30–2:42 | Dans le dépôt public, le tableau de `evals/results/summary.md` : **11 cas sur 11 conformes** (défilement lent) | Page GitHub du dépôt |
| S15 | 2:42–2:50 | Cas Pharmacie : relevé série D + texte `intention_pharmacien.txt`, étape `lookup_filieres`, déplier « Input / output » : la ligne « Pharmacie » est dans les lignes écartées (`Statut_qualité` « Réparé - fusion OCR ») et n'apparaît pas dans les recommandations | Exécution ; **repli** : le fichier `evals/results/2026-11-03/unverified_trap.json`, légendé comme tel |
| S16 | 2:50–2:58 | **Carte** de fin : PathProof, `pathproof-six.vercel.app`, `github.com/AresGn/PathProof-Meta-Hackathon`, compte X `{{X_HANDLE}}`, « Solo · fictional data » | Carte |

## 4. Prise de vues (écran)

### Préparation (une fois)
1. Serveur : `.venv/bin/uvicorn src.api.server:app --port 8000`, puis ouvrir `http://127.0.0.1:8000/demo.html` (la page servie par uvicorn, pas un aperçu statique).
2. **Enregistrer le navigateur seulement** (source « fenêtre » d'OBS, pas l'écran entier) : aucune fenêtre d'éditeur ni de terminal dans le champ. **`.env` ne doit jamais apparaître**, ni la barre d'adresse d'un autre onglet, ni un chemin personnel.
3. Navigateur en fenêtre privée, sans extension, barre de favoris masquée, un seul onglet, notifications coupées (mode « ne pas déranger »).
4. Réglages : 1920×1080, 30 i/s, MKV (remux en MP4 ensuite), curseur visible avec un halo discret.
5. Langue de l'interface : **choisir EN ou FR avant de lancer** (le rapport et les questions suivent la langue choisie au démarrage). Version anglaise : interface EN. Version française : interface FR, rushs séparés.
6. Les rushs d'une exécution complète durent 100 à 165 s (mesuré, `docs/deploy.md`, `evals/results/summary.md`) : tourner sans couper, le montage accélère les attentes.

### Où filmer
- **Serveur local** pour les prises : même code que le déploiement, sans limite par IP (5 requêtes/min sur Vercel) et sans le 404 de session `ask_student` connu sur Vercel (`docs/deploy.md`).
- **URL publique** pour **une** prise de S05/S06 : preuve que la démo déployée tourne. Si le 404 apparaît, on garde la prise locale.

### Liste des prises

| Prise | Quoi | Plans | Coût indicatif (boucle seule, `evals/results/summary.md`) |
|---|---|---|---|
| T1 | **Contradictory voice note** : répondre « D » à la 1re question, laisser la 2e (14 contre 11,2) affichée 10 s | S01, S02 | ≈ 0,32 $ |
| T2 | **Clear serie D sheet + matching voice note**, répondre « D », puis parcourir le rapport et les preuves | S04–S11 | ≈ 0,38 $ |
| T3 | **Blurry sheet** | S12, S13 | ≈ 0 $ |
| T4 | Pharmacie : relevé `releve_serie_d.jpg` + texte de `intention_pharmacien.txt` | S15 | ≈ 0,35 $ |
| T5 | GitHub : `summary.md`, défilement lent | S14 | 0 |

Prévoir 2 à 3 essais par prise : environ 5 $ par langue, très en dessous du solde de crédits (66 $ le 3 nov, selon le porteur).

**Prises à refaire si :** le bandeau « exécution enregistrée » apparaît (ce n'est pas une prise en direct ; si vous la gardez, la voix doit le dire) ; la 2e question de T1 n'est pas celle du 14 contre 11,2 (le comportement varie d'une exécution à l'autre) ; la limite de 12 pas est atteinte sans rapport (`docs/deploy.md`) ; une clé, un nom réel ou un chemin personnel est visible.

### Nommage des rushs
`video/raw/<plan>_<langue>_<format>_take<n>.mkv`, par exemple `S08_en_desktop_take2.mkv`, `S13_fr_vertical_take1.mkv`. Une ligne de `video/raw/NOTES.txt` par prise gardée : « bonne », « reprise », et pourquoi.

### Format vertical (X)
- **Prise native** : fenêtre étroite, `chromium --app=http://127.0.0.1:8000/demo.html --window-size=540,960 --force-device-scale-factor=2`, enregistrée en 1080×1920. L'interface est responsive (captures à 375 px dans `docs/`), donc la même prise se refait en vertical.
- **Repli** : recadrer le rush horizontal autour du panneau actif (zoom au montage). Moins net, mais sans refaire les prises.
- Zones de sécurité : texte et sous-titres entre 12 % et 82 % de la hauteur, rien dans les 10 % du haut ni les 15 % du bas (interface du lecteur).

## 5. Voix off

- **Vous enregistrez la voix** (français et anglais). Il n'y a pas de synthèse vocale dans PathProof ; une voix de synthèse pour la narration est possible mais doit être annoncée dans la description de la vidéo.
- Micro proche (15 cm), pièce calme, filtre anti-pop ou, à défaut, un tissu devant le micro. WAV 48 kHz mono, un fichier par bloc : `video/raw/VO_en_V1.wav` … `VO_en_V6.wav`, idem `VO_fr_*`.
- Lire à voix posée, 2 prises par bloc, couper les respirations bruyantes. Les nombres sont dits en toutes lettres (c'est écrit ainsi dans les scripts).
- Le texte est contraint par les fenêtres ci-dessus : si une phrase est trop longue à dire, la raccourcir **dans le script** (et pas en accélérant la voix), puis prévenir le montage.
- La voix des notes vocales d'exemple est synthétique (`data/samples/README.md`). Une mention à l'écran « fictional student · synthetic voice » en S05 le dit.

## 6. Montage (agent de code, `ffmpeg`)

Prérequis : `ffmpeg` et `ffprobe` installés (absents de cette machine le 3 nov : `sudo apt install ffmpeg`).

Un fichier `video/timeline.csv` décrit le montage, une ligne par plan : `plan, source, in, out, vitesse, zoom, carte, bloc_voix`. Le montage se rejoue depuis ce fichier si une prise change.

Étapes, dans l'ordre :
1. **Contrôle des rushs** : `ffprobe` (résolution, i/s, durée). Écarter ce qui ne respecte pas le §4.
2. **Voix** : réduction de bruit légère, normalisation à **−16 LUFS** intégrés, crête vraie −1 dBTP ; les blocs sont posés à leur fenêtre.
3. **Plans** : coupe (`in`/`out`), accélération des attentes avec une pastille « ×3 » ou « ×4 » toujours visible, zoom ciblé (`crop` + `scale`) sur les pastilles de modèles, sur la question, sur la preuve ouverte.
4. **Cartes** : S03, S13 (mention SAM) et S16, sobres, polices système, couleurs de l'interface (thème sombre, vert PathProof).
5. **Sous-titres** : `pathproof_en.srt`, cues de `script-en.md` (2 lignes maximum, 42 caractères en horizontal, 28 en vertical), calés sur la voix enregistrée. Pour la version à voix française : les **mêmes cues anglais**, recalés sur l'audio français.
6. **Son** : pas de musique avec paroles ; un fond discret (−30 dB) est permis, sinon rien. L'extrait de note vocale de S01 passe à −22 dB sous la voix.
7. **Export** :
   - YouTube : H.264 High, 1920×1080, 30 i/s, CRF 18, AAC 192 kbit/s ; sous-titres en **piste `.srt`** à téléverser avec la vidéo.
   - X vertical : H.264, 1080×1920, 30 i/s, CRF 20, AAC 192 kbit/s ; sous-titres **incrustés** (`subtitles=` avec `force_style`, police plus grande).
8. **Contrôle** : `ffprobe` donne une durée ≤ 180,0 s pour chaque fichier ; relecture complète ; `ffmpeg -i … -af ebur128` pour vérifier le niveau ; première image propre pour la miniature.

Le montage ne doit rien rendre plus beau que la réalité : pas de fausse trace, pas de rapport retouché, pas de valeur recalculée à la main.

## 7. Règles d'honnêteté (critères de l'issue #39)

| Critère | Comment il est tenu |
|---|---|
| 3:00 au plus, sous-titres anglais | 2:58 ; `.srt` ou incrustés, même sur la voix française |
| Séquence du PRD §13 | blocs V1 à V6, fenêtres du §3 |
| Chaque plan = une exécution réelle, mode enregistré dit | seules les cartes S03, S13 (mention SAM) et S16 ne sont pas des exécutions et se lisent comme des cartes ; une prise « enregistrée » se dit dans la voix |
| Aucune clé, donnée réelle, chiffre sans source | données fictives uniquement ; 77 101 sourcé à l'écran ; le PDF du guide n'est pas montré (seules ses lignes citées par les preuves le sont) |
| Lien ouvrable sans connexion | vidéo publique ou non répertoriée ; ouverte en fenêtre privée avant d'être mise dans le README |
| Seul le travail de l'événement | ni la V1 WhatsApp, ni de vieilles captures ; le dépôt est celui du hackathon |

Points de vocabulaire : jamais « chatbot » ; « vérifié » seulement pour le rapport dont chaque affirmation a passé `verify_report` ; « onze cas conformes, un passage chacun » (pas « fiable »).

**Écart avec le PRD, dit dans la voix :** le PRD (§3.1, ligne 97, et le tableau des cas du §10) annonce que Pharmacie, écartée par le contrôle qualité, est **listée** sous « Ce que je n'ai pas pu vérifier ». Dans la sortie réelle (`evals/results/2026-11-03/unverified_trap.json`), le rapport ne cite pas Pharmacie et écrit « Toutes les affirmations ci-dessus sont vérifiées » ; la ligne n'est visible que comme ligne **écartée** dans le résultat de `lookup_filieres`. La voix du bloc V5 dit donc « excluded », pas « listed as unverified ». Voir `docs/decisions.md`.

## 8. Calendrier (mardi 3 novembre, gel le soir ; limite de soumission : 4 novembre 21 h ET = 5 novembre 03 h à Porto-Novo)

| Étape | Durée estimée | Sortie |
|---|---|---|
| 1. Installer `ffmpeg` ; régler OBS et la fenêtre ; test de 1 minute | 30 min | rushs de test propres |
| 2. Prises T1 à T5, interface anglaise, écran horizontal | 60 min | `video/raw/S*_en_desktop_*` |
| 3. Voix anglaise, blocs V1 à V6 | 30 min | `VO_en_*.wav` |
| 4. Montage P1 (YouTube anglais) + `.srt` | 60 à 90 min | `pathproof_youtube_en.mp4` |
| 5. Contrôle : durée, niveau, lecture complète, ouverture en fenêtre privée | 20 min | liste cochée sur l'issue |
| 6. Prises verticales + montage P2 (X) | 60 min | `pathproof_x_en_vertical.mp4` |
| 7. Version française P3 (prises FR, voix FR, montage) | 90 min | optionnel |
| 8. Téléversement, lien dans le README, post X (E7.3), soumission (E7.5) | 30 min | liens |

La marge de la nuit du 4 au 5 novembre sert aux reprises, pas aux nouveautés.

## 9. À fournir par vous

- `{{X_HANDLE}}` : le compte X affiché sur la carte S16 (je n'ai pas de compte à citer).
- Titre et description de la vidéo (la description cite : démo, dépôt, « données fictives », voix de synthèse des notes d'exemple).
- Le lien final de la vidéo : à ajouter ensuite dans le README (la ligne a été retirée tant que la vidéo n'existe pas).
- Le choix de la voix : la vôtre ou une voix de synthèse annoncée.
