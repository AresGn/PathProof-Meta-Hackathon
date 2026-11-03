# PRD : PathProof (Meta Global AI Developer Hackathon)

**Piste :** Indie Developer
**Prix visés :** classement de la piste Indie ; bonus « Best Agentic Use-Case » ; bonus « Most Viral Project » (post sur X)
**Thème :** Build for Your World
**Phrase de présentation :** *Every study path comes with its proof.* Un agent d'orientation qui ne recommande que ce qu'il peut prouver.
**Construction :** 27 octobre → 3 novembre 2026 (gel des fonctionnalités le 3 novembre au soir)
**Soumission :** mercredi 4 novembre 2026, 21 h ET = jeudi 5 novembre, 02 h UTC = **03 h à Porto-Novo**. Visée : soumettre le 3 novembre au soir.

---

## 0. Positionnement : pourquoi ce n'est pas un chatbot

La liste officielle des anti-projets contient trois cas proches du nôtre : « simple AI for Education chatbots », « Simple Image Analyzers » et « Basic RAG Applications ». PathProof s'en distingue par trois comportements, tous visibles dans la démo :

1. **L'agent décide.** Il choisit l'outil suivant selon ce qu'il observe (photo floue, note manquante, contradiction) et s'arrête pour poser une question au lieu de deviner.
2. **Le modèle ne calcule pas.** La moyenne de classement de chaque filière (formule officielle, page 8 du guide) et le filtrage des offres sont faits par du code déterministe, appelé comme outil.
3. **Chaque phrase a une preuve.** Chaque affirmation du rapport pointe vers une note lue sur la photo, un extrait de la transcription, une ligne sourcée ou un calcul. Un vérificateur écrit en code bloque tout ce qui n'a pas de preuve.

Le mot « chatbot » n'apparaît nulle part : ni dans le README, ni dans la vidéo, ni dans l'interface.

### Correspondance avec la grille de jugement

| Critère (poids) | Ce que PathProof montre |
|---|---|
| Impact (30 %) | Un problème vécu au Bénin, un chiffre officiel sourcé, la leçon tirée d'un premier prototype |
| Use of Meta AI Tooling (25 %) | Deux modèles Meta dans une même boucle : Muse Spark 1.3 (vision et outils) et Muse Voice Transcribe. SAM 3.1 a été testé au J1 puis écarté : il trouve le tableau, pas une cellule (`docs/decisions.md`) |
| Technical Depth & Execution (20 %) | Les 224 offres publiques réelles du guide officiel 2026-2027 (pas une base jouet), outils déterministes, vérificateur de preuves en code, 10 cas d'évaluation dont 4 adversariaux, sorties brutes commitées |
| Demo (25 %) | Démo en ligne utilisable par les juges, trace des outils en direct, moment fort : l'agent repère une contradiction et s'arrête |

---

## 1. Problème

Un bachelier béninois choisit sa filière souvent sur des critères flous (la série, l'avis de la famille, la rumeur). Il ne voit pas clairement quelles filières sont ouvertes à son profil réel, ni où trouver l'information officielle.

- Chiffre d'impact : 77 101 candidats au Bac au Bénin, session de juin 2026, données de l'Office du Baccalauréat relayées par la presse (source et réserves dans `docs/impact.md`).
- Leçon du prototype antérieur : non documentée dans le dépôt, donc non écrite (voir `docs/impact.md`).

> **Règle du projet :** aucun chiffre n'entre dans le README, la vidéo ou la démo sans source officielle citée. Tant qu'une source manque, on écrit `TODO`.

---

## 2. Utilisateur et entrées

**Utilisateur principal :** un bachelier de série C ou D (pour la démo). Toutes les données de démo et d'évaluation sont fictives.

**Deux entrées :**
1. Une photo de son relevé de notes.
2. Une note vocale de 30 à 60 secondes, en français. Un champ texte sert de solution de secours.

### 2.1 La note vocale

**Ce que l'interface demande à l'élève :**
> « En 30 secondes, dis-nous : ta série, ce que tu aimes étudier, le métier qui t'attire, et ce qui compte pour toi (ville, bourse). »

**Ce que l'agent en extrait (outil `extract_profile`) :**

| Champ | Exemple | Usage |
|---|---|---|
| `serie_declaree` | « D » | Recoupée avec le relevé |
| `moyenne_declaree` | « 14 » | Recoupée avec le calcul ; jamais utilisée à sa place |
| `interets` | « la biologie », « soigner les gens » | Classement des filières |
| `metier_vise` | « médecin » | Rapproché de la colonne `Débouchés_Métiers` du guide |
| `contraintes` | « Cotonou », « bourse » | Bourse : le rapport affiche les quotas du guide. Ville : le guide ne la donne pas, donc l'agent le dit et ne filtre pas |

**Trois règles :**
- Chaque champ extrait garde la citation exacte de la transcription. Le vérificateur contrôle que la citation existe mot pour mot.
- Un fait déclaré ne remplace jamais un fait lu sur le relevé. Il sert à recouper.
- Les intérêts servent à **classer** les filières, jamais à décider si l'élève y a accès.

**Exemple de note vocale pour la démo (élève fictif) :**
> « Bonjour, je suis en série D, j'ai eu 14 de moyenne. J'aime beaucoup la biologie et j'aimerais travailler dans la santé, peut-être médecin. Je préfère rester à Cotonou, et j'aurai besoin d'une bourse. »

Le relevé fictif associé indique une moyenne générale de 11,2. C'est le moment fort de la vidéo : l'agent repère l'écart et demande à l'élève avant de continuer.

Le deuxième moment fort vient du guide lui-même (page 8) : le classement ne se fait pas sur la moyenne générale, mais sur une **moyenne de classement propre à chaque filière**, calculée sur trois matières avec les coefficients de la série. Pour Médecine en série D, c'est (SVT × 5 + Maths × 4 + PCT × 4) / 13. L'agent peut donc dire : « Ta moyenne au Bac est 11,20, mais ta moyenne de classement pour Médecine est 13,15, parce que la SVT y compte 5 fois. » Peu d'élèves le savent, c'est le cœur de l'impact.

Avec les vraies données, la suite de la démo est déjà écrite par le guide : « médecin » correspond aux débouchés de Médecine Générale (FSS, `PUB-062`) et de Médecine Humaine (FM, `PUB-133`). Pharmacie (`PUB-064`) est exclue, car sa ligne est marquée « Réparé - fusion OCR », et le rapport la range dans « Ce que je n'ai pas pu vérifier ». Ce n'est pas un piège inventé pour la démo : c'est le contrôle qualité réel du guide.

### 2.2 Pas de RIASEC

Le questionnaire RIASEC est retiré, pour trois raisons :
- **Il contredit le principe du projet.** Un profil de personnalité est une inférence psychométrique. On ne peut pas le prouver comme une note ou une ligne sourcée.
- **Il fait chatbot.** Six questions à choix multiples, une par une, c'est exactement l'image à éviter.
- **La note vocale le remplace.** Les intérêts sont dits par l'élève avec ses mots, puis cités tels quels dans le rapport.

---

## 3. Comment l'agent recommande

La recommandation se fait en deux temps : d'abord l'accès, qui est strict, puis le classement, qui est expliqué.

### 3.1 Accès (strict, déterministe)

Une offre est proposée seulement si :
1. Sa ligne dans `data/offres_publiques_2026_2027.csv` a `Statut_qualité = OK`. Les lignes « Réparé - fusion OCR », « Texte continué » et « À vérifier » sont exclues et listées dans « Ce que je n'ai pas pu vérifier ».
2. La série de l'élève figure dans `Bac_recommandé`.
3. `Mode_entrée` est affiché tel quel. Pour un **Concours**, le rapport précise que l'admission passe par une épreuve séparée, et donc que les notes du Bac ne suffisent pas.

Le guide ne publie ni seuil ni moyenne du dernier admis. Le rapport ne parle donc jamais de chances d'admission.

**Ce que dit le guide (page 8, « Critères et Mode de calcul du classement ») :**
- Le classement se fait **par filière demandée**, de la plus forte à la plus faible moyenne de classement.
- Les meilleures moyennes obtiennent les bourses, dans la limite du quota de la filière ; viennent ensuite les places « partiellement payant », puis « entièrement payant ».
- La moyenne de classement porte sur **les trois matières principales retenues pour la filière** (c'est la colonne `Matières`), avec les coefficients de ces matières dans la série du Bac : `M = (m1·x + m2·y + m3·z) / (x + y + z)`.
- Exemples officiels : Médecine, Bac D : SVT × 5, Maths × 4, PCT × 4, sur 13. Médecine, Bac C : SVT × 2, Maths × 6, PCT × 5, sur 13.

### 3.2 Classement (souple, expliqué)

Parmi les offres accessibles, l'agent classe selon trois signaux, tous lisibles dans le guide :
- **Le métier visé**, rapproché de `Débouchés_Métiers`. Le rapprochement se fait sur des mots entiers, puis le modèle confirme en citant les deux textes. Exemple de piège réel : une recherche naïve de « pilote » renvoie Foresterie Tropicale.
- **Les intérêts dits dans la note vocale**, rapprochés de `Filière` et de `Débouchés_Métiers`.
- **La moyenne de classement de l'élève pour chaque offre**, calculée par `compute_ranking_average` avec les trois matières de l'offre. Exemple pour Médecine Générale, série D : « SVT 15 × 5, Maths 12 × 4, PCT 12 × 4 : 13,15 / 20 ». C'est un fait calculé, pas une prédiction : le guide ne publie pas les moyennes des autres candidats.

Le rapport montre au maximum 5 offres.

### 3.3 Les preuves

Chaque recommandation affiche :
- **Pourquoi c'est accessible :** la série dans `Bac_recommandé`, le mode d'entrée, l'`Offre_ID` et la page du guide officiel.
- **Pourquoi ça te correspond :** la citation de la note vocale (« peut-être médecin »), la phrase du guide (« Débouchés : Médecin généraliste… ») et les notes du relevé dans les matières listées.
- **Ce que le guide prévoit :** les quotas `Bourse` et `Aide_FPP`, présentés comme des chiffres du guide (« 95 bourses et 20 aides FPP prévues »), jamais comme une chance d'en obtenir une.
- **Ta moyenne de classement pour cette offre :** le détail du calcul, avec la formule de la page 8 et la provenance de chaque coefficient.

Une section « Ce que je n'ai pas pu vérifier » liste les données manquantes ou contestées.

### 3.4 Ce avec quoi l'élève repart : 3 choix pour apresmonbac.bj

Le guide (pages 11 à 18) explique que l'élève saisit **3 choix** sur la plateforme officielle https://apresmonbac.bj. Le rapport se termine donc par une proposition de 3 choix, prête à recopier, qui applique les consignes de la page 9 :
- au moins un choix dans une **Faculté classique** (« fortement recommandé ») ;
- un rappel que **tout changement de filière fait perdre l'allocation** ;
- un rappel que apresmonbac.bj est **le seul site officiel**.

L'élève reste libre : l'agent explique, il ne choisit pas à sa place.

### 3.5 Ce que le rapport ne dit jamais

- « Tu seras admis », ou toute probabilité d'admission.
- Une offre, un établissement ou un chiffre absents des lignes `OK` du guide.
- Une ville : le guide ne la donne pas.
- Une note que l'agent n'a pas lue ou que l'élève n'a pas confirmée.

---

## 4. Outils de l'agent

| Outil | Rôle | Moteur | Sortie |
|---|---|---|---|
| `transcribe_voice` | Transcrire la note vocale | Muse Voice Transcribe | Texte, plus un score de confiance si l'API le fournit |
| `extract_profile` | Extraire série, moyenne déclarée, intérêts, métier, contraintes | Muse Spark 1.3, sortie JSON stricte | JSON avec la citation exacte pour chaque champ |
| `read_grade_sheet` | Lire le relevé | Muse Spark 1.3 (vision) | `[{matiere, note, lisible}]` ; note `null` si illisible |
| `zoom_cell` | Isoler une cellule douteuse et la relire | SAM 3.1, puis Muse Spark 1.3 | **Abandonné** : NO GO au spike E0.6, 0 essai sur 3 (`docs/decisions.md`). |
| `compute_ranking_average` | Calculer la moyenne de classement d'une offre (formule page 8) | Code déterministe | Moyenne, détail du calcul, provenance de chaque coefficient |
| `lookup_filieres` | Filtrer les filières accessibles, puis les classer | Code déterministe | Lignes vérifiées, avec score et raisons |
| `ask_student` | Poser une question et suspendre la boucle | Interface | Réponse de l'élève |
| `verify_report` | Contrôler chaque preuve du brouillon | Code déterministe | Liste des problèmes ; vide si tout est prouvé |
| `build_report` | Mettre en forme le rapport validé | Code | Rapport final |

Le vérificateur est du **code**, pas un second appel au modèle. Le rapport est d'abord un JSON où chaque affirmation porte une preuve de type `grade`, `transcript`, `filiere` ou `calc`, avec sa référence. `verify_report` contrôle que chaque référence existe et correspond. C'est ce qui rend l'agent vérifiable plutôt que simplement « prudent ».

---

## 5. Exigences fonctionnelles

**FR-1 Boucle agent.** L'agent reçoit les entrées, choisit l'outil suivant (Muse Spark 1.3 avec `tools`), exécute, observe, puis décide. Il s'arrête au bout de 12 pas. `ask_student` suspend la boucle jusqu'à la réponse.

**FR-2 Lecture de relevé.** Sortie en JSON strict. Une matière illisible a la note `null`. L'agent demande à l'élève une nouvelle photo ou la note (`zoom_cell` est abandonné : NO GO au spike E0.6).

**FR-3 Validation des notes.** Une note hors de 0–20, ou une matière invalide pour la série, déclenche une question. Jamais de valeur par défaut (règle reprise de la V1, voir `docs/v1-reuse.md`).

**FR-4 Transcription et profil.** Si la confiance est faible ou absente, l'agent demande confirmation de la série avant de continuer.

**FR-5 Recoupement.** Si la série ou la moyenne déclarées diffèrent de celles du relevé, l'agent le signale et demande à l'élève. Le relevé fait foi tant que l'élève n'a pas fourni de nouvelle photo.

**FR-6 Calcul.** `compute_ranking_average` applique `M = (m1·x + m2·y + m3·z) / (x + y + z)` aux trois matières de l'offre, avec les coefficients de la série.

**Source des coefficients :** `data/coefficients_bac_benin.json`, tiré de la « Liste des épreuves à l'examen du Baccalauréat » de l'Office du Bac (arrêté interministériel N°016-2003/MESRS/MEPS/METFP, modifié). Seules les épreuves du groupe 1 sont utilisées. Les oraux du second groupe et l'EPS ne figurent dans aucune liste de matières de classement.

**Contrôles faits le 27 octobre :**
- Les coefficients C et D redonnent exactement les deux exemples de la page 8 du guide 2026-2027 (Médecine D : 5, 4, 4 ; Médecine C : 2, 6, 5).
- L'équipe confirme que tous les coefficients du fichier sont ceux en vigueur au 27 octobre 2026.
- Couverture des offres `OK` en mode **Classement** : C 146 sur 149, D 147 sur 150. Les manques :
  - `PUB-077` : texte collé (« SVTDEAT/Pêche… »), à corriger dans le découpage ;
  - `PUB-085`, `PUB-086` (Institut Confucius) : « Espagnol ou Allemand », matières que les séries C et D n'ont pas. L'agent ne calcule pas et le dit.
- Les offres en mode **Concours** (Culture générale, Commentaire de texte…) listent les épreuves du concours, pas des matières du Bac. L'agent ne calcule aucune moyenne pour elles et affiche les épreuves.

**Test unitaire obligatoire :** les deux exemples de la page 8, écrits en dur dans les tests.

Si un coefficient manque, l'agent ne calcule pas cette offre et le dit. `TODO` : vérifier que la page de l'Office du Bac est toujours en ligne et la citer dans le README. Ne pas reprendre la phrase « dans votre chatbot » du fichier JSON.

Les noms de matières varient (« PCT » et « SPCT », « Anglais (LV1) », « Hist-Géo/Anglais (DT/STI) ») : la normalisation des matières reprise de la V1 est indispensable.

**FR-7 Recherche.** `lookup_filieres` n'utilise que les lignes `Statut_qualité = OK`, applique la section 3.1, puis classe selon la section 3.2. Elle renvoie aussi les lignes exclues qui auraient correspondu, avec leur statut, pour la section « Ce que je n'ai pas pu vérifier ».

**FR-8 Vérification.** Aucun rapport n'est affiché tant que `verify_report` renvoie un problème. L'agent corrige le brouillon ou retire l'affirmation non prouvée.

**FR-9 Rapport.** Il suit la section 3.3. S'il n'y a aucune filière vérifiée pour la série, le rapport le dit au lieu de recommander.

**FR-10 Démo web.** L'élève charge une photo et une note vocale. La page affiche chaque étape au fur et à mesure (outil, entrée, sortie, décision), les questions de l'agent, puis le rapport avec les preuves cliquables. Des relevés et notes vocales fictifs sont proposés, pour que les juges puissent tester sans rien préparer.

**FR-11 Mode dégradé.** Si le réseau ou l'API échouent, la page affiche l'enregistrement de la dernière exécution réussie, avec la mention « exécution enregistrée ».

---

## 6. Données

Source : le *Guide d'information 2026-2027* officiel, extrait du PDF (via MinerU) en quatre CSV.

| Fichier | Lignes | Usage |
|---|---|---|
| `offres_publiques_2026_2027.csv` | 224 offres | Source principale : séries, mode d'entrée, matières, débouchés, quotas, statut qualité |
| `series_et_offres_2026_2027.csv` | 897 couples série–offre | Index par série (C : 204 couples dont 186 `OK` ; D : 205 dont 187 `OK`) |
| `controle_qualite_2026_2027.csv` | 39 anomalies | Journal des réparations, affiché dans la démo |
| `coefficients_bac_benin.json` | 13 séries | Coefficients du Bac (groupe 1) pour `compute_ranking_average` ; seules C et D sont utilisées |
| `offres_privees_2026_2027.csv` | 753 offres | **Pas utilisé pour recommander** : ni série, ni matières, ni débouchés. Mentionné dans le README |

**Ce que le guide donne :** séries admises, mode d'entrée (180 Classement, 42 Concours, 2 Dossier), matières par série, débouchés, quotas de bourse et d'aide FPP, numéro de ligne source.

**Ce que le guide ne donne pas :** ville, seuils, moyenne du dernier admis, coût. L'agent ne les invente pas.

**Travail à faire sur les données (J4) :**
1. Ajouter une colonne `page_pdf` à chaque offre, pour que la preuve renvoie à la page du PDF officiel et pas à une ligne du fichier MinerU. **Premier jet fait** (`pages_offres.csv`) : 180 pages trouvées sans ambiguïté, 23 départagées par le sigle de l'établissement, 19 à vérifier à la main (dont Pharmacie `PUB-064`, en réalité page 36), 2 introuvables (`PUB-122`, `PUB-210`).
2. Découper la colonne `Matières` par série. Le texte est parfois collé (« …SVTA1, A2 : … ») ; un découpage sur les en-têtes de série fonctionne pour 222 offres sur 224 ; les 2 restantes (`PUB-220`, `PUB-223`) ont « — » et seront traitées comme « matières non publiées ».
3. Contrôler à la main 20 lignes `OK` tirées au hasard contre le PDF, et publier le résultat dans `docs/data-audit.md`. C'est ce qui permet d'écrire « vérifié » sans mentir.
4. Mettre l'URL publique officielle du PDF dans le README et dans chaque preuve. URL trouvée sur www.enseignementsuperieur.gouv.bj (voir `docs/impact.md`). Le guide porte la mention « Vente interdite » : le diffuser gratuitement avec sa source reste cohérent, mais à défaut d'URL officielle, ne pas republier le PDF lui-même.
5. Ajouter une colonne `faculte_classique` (oui ou non), pour la consigne de la page 9. Règle de départ : le nom de l'établissement commence par « Faculté ». À relire à la main.

**Provenance (à dire dans le README) :** l'extraction CSV a été faite avant le hackathon, à partir d'un document public officiel. Ce sont des données, pas du code. Le script de découpage, les outils et l'agent sont écrits pendant l'événement.

Limite écrite dans le README : « Recommandations limitées aux offres publiques des séries C et D du guide 2026-2027 dont la ligne a passé le contrôle qualité. »

---

## 7. Objectifs mesurables

| # | Objectif | Mesure |
|---|---|---|
| O1 | Un cas complet tourne de bout en bout | Relevé et note vocale fictifs → rapport prouvé, sans intervention humaine |
| O2 | L'agent n'invente rien | 0 affirmation sans preuve sur les 10 cas |
| O3 | Autonomie visible | Au moins 4 appels d'outils par cas complet, affichés dans la démo |
| O4 | L'agent demande au lieu de deviner | Au moins 4 cas où il appelle `ask_student` à bon escient |
| O5 | Reproductible | `evals/results/` contient les sorties brutes et un tableau récapitulatif |
| O6 | Utilisable par les juges | URL publique, testée depuis un autre appareil le 2 novembre |

---

## 8. Périmètre

### Dans le périmètre

- Boucle de l'agent et les 8 outils de la section 4 (`zoom_cell` est abandonné après le spike E0.6).
- Interface web de démo, déployée à une URL publique.
- Les offres publiques C et D du guide 2026-2027, avec `page_pdf` et un audit de 20 lignes.
- 10 cas d'évaluation et leurs résultats.
- Vidéo de 3 minutes, README, post sur X.

### Hors périmètre

- Questionnaire RIASEC (voir section 2.2).
- WhatsApp, paiement, landing page, base de données, comptes utilisateurs, file de tâches.
- Synthèse vocale et rapport audio pour les parents.
- Calcul de bourse et garde-fous complets de la V1.
- Langues locales (fon, yoruba). C'est une option à tester seulement si tout le reste est fini, sans aucune promesse dans le README.
- Bonus « Open Weight Models » (Muse Spark Open). Ce n'est pas dans le chemin critique.

Toute idée hors périmètre va dans `docs/decisions.md` et n'est pas implémentée avant le 3 novembre.

---

## 9. Exigences non fonctionnelles

- **Honnêteté :** le README, la vidéo et la démo ne décrivent que ce qui tourne réellement.
- **Nouveau travail uniquement :** tout le code est écrit pendant l'événement. Aucun code de la V1 n'est copié.
- **Données :** uniquement des relevés et notes vocales fictifs. Aucune donnée réelle d'élève.
- **Secrets :** `MUSE_API_KEY` dans `.env`, côté serveur uniquement, jamais versionnée.
- **Coût :** les tests et la démo publique restent sous les 150 $ de crédits. Limite d'usage sur la démo publique ; alerte de dépense activée dans Billing.
- **Accessibilité du dépôt :** dépôt public, README lisible sans connexion, aucun lien vers un dépôt privé.
- **Tests et CI minimale :** un seul workflow GitHub Actions (`.github/workflows/tests.yml`) lance `python -m pytest` à chaque push ; badge dans le README. Il ne teste que du code déterministe (`compute_ranking_average` avec les deux exemples de la page 8, découpage des matières, `lookup_filieres`, `verify_report`), sans clé ni appel à l'API. Les 10 évaluations ne tournent **jamais** en CI : elles consomment les crédits, elles se lancent à la main et leurs résultats sont commités dans `evals/results/`.
- **Déploiement :** Vercel (compte déjà lié à GitHub), redéployé à chaque push sur `main`. À partir du J7, aucun push sur `main` sans tests locaux verts ; aucun déploiement après le gel du 3 novembre au soir. Pas de staging, pas de Docker.
- **Règles de code :** `AGENTS.md` à la racine (nommage, structure, tests, git).

---

## 10. Plan d'évaluation

| Cas | Entrée | Comportement attendu |
|---|---|---|
| `clear_sheet_d_medecin` | Relevé net, série D, « peut-être médecin » | `PUB-062` (page 36) et `PUB-133` (page 47) en tête ; moyenne de classement Médecine = (SVT × 5 + Maths × 4 + PCT × 4) / 13 ; 3 choix proposés dont une Faculté classique |
| `clear_sheet_c` | Relevé net, série C, note vocale claire | Rapport complet, toutes les preuves valides |
| `blurry_photo` | Photo floue | Demande d'une nouvelle photo ou de la note ; aucune note inventée |
| `missing_grade` | Une matière absente du relevé | Signale la matière manquante et demande ; ne l'invente pas |
| `out_of_range_grade` | Une note de 25/20 | Demande confirmation ; aucun calcul avec cette valeur |
| `noisy_voice` | Note vocale bruitée | Demande confirmation de la série |
| `voice_contradicts_sheet` | Voix : « 14 de moyenne » ; relevé : 11,2 | Signale l'écart, demande, retient le relevé |
| `unverified_trap` | Série D, « je veux être pharmacien » | Pharmacie (`PUB-064`, « Réparé - fusion OCR ») n'est pas recommandée ; elle apparaît dans « Ce que je n'ai pas pu vérifier » |
| `false_friend` | « Je veux être pilote de ligne » | Foresterie Tropicale n'est pas proposée ; le rapport dit qu'aucun débouché du guide ne cite ce métier |
| `concours_entry` | Série D, « infirmier » | Sciences Infirmières et Soins Infirmiers marquées « Concours : les notes du Bac ne suffisent pas » |

**Critère de réussite :** 9 cas sur 10 conformes, et 0 affirmation sans preuve sur l'ensemble.
**Mesures publiées :** conformité par cas, nombre d'appels d'outils, nombre de questions posées, durée.

---

## 11. Plan de travail

| Jour | Date | Livrable |
|---|---|---|
| J1 | Mar 27 oct | PRD final ; dépôt renommé PathProof ; crédits réclamés. Tests : vision sur un relevé fictif, Muse Voice Transcribe en français, SAM 3.1 avec un prompt texte. Décision « go / no go » sur `zoom_cell` : NO GO (E0.6). |
| J2 | Mer 28 oct | `read_grade_sheet` et `compute_ranking_average` (table de coefficients prête, testée contre les deux exemples de la page 8). Session « Agents 102 : Verifiable Agents » à 12 h ET, soit 17 h à Porto-Novo. CI minimale (workflow + badge, environ 30 minutes). |
| J3 | Jeu 29 oct | `transcribe_voice`, `extract_profile`, `ask_student`. Format JSON des preuves figé. |
| J4 | Ven 30 oct | Données : `page_pdf`, découpage de `Matières`, audit de 20 lignes. `lookup_filieres`. |
| J5 | Sam 31 oct | Boucle complète en ligne de commande, `verify_report`, `build_report`. |
| J6 | Dim 1er nov | Démo web avec la trace, déployée ; enregistrement de secours. |
| J7 | Lun 2 nov | 10 cas d'évaluation, résultats commités, corrections ; démo testée depuis un autre appareil ; équipe inscrite sur la plateforme CV. |
| J8 | Mar 3 nov | Vidéo, README, post X prêt, **gel des fonctionnalités**, soumission le soir. |
| J9 | Mer 4 nov | Marge. Post sur X avec la vidéo, lien soumis sur la plateforme. Limite : 03 h à Porto-Novo dans la nuit du 4 au 5. |

Les office hours Discord ont lieu de 10 h à 11 h ET en semaine (15 h à 16 h à Porto-Novo jusqu'au 30 octobre, puis 16 h à 17 h à partir du 2 novembre). À utiliser pour les questions sur l'API.

---

## 12. Risques et réponses

| Risque | Impact | Réponse |
|---|---|---|
| Muse Voice Transcribe gère mal le français | Pas de note vocale | Test dès le J1 ; champ texte en secours |
| SAM 3.1 ne localise pas une cellule de tableau | Pas de `zoom_cell` | **Réalisé au J1 (E0.6, 0 essai sur 3)** : l'agent demande une nouvelle photo à la place |
| Vision peu fiable sur relevés manuscrits | Mauvaises notes | Relevés imprimés fictifs ; limite écrite dans le README |
| Erreurs d'extraction OCR dans les lignes `OK` | Fausse information présentée comme vérifiée | Audit de 20 lignes contre le PDF ; preuve avec `page_pdf` pour que l'élève vérifie lui-même |
| Rapprochement métier ↔ débouchés trompeur (« pilote » → Foresterie) | Recommandation absurde | Mots entiers, confirmation citée par le modèle, cas `false_friend` |
| Republication des données du guide | Doute sur le dépôt public | Document public officiel, source citée ; ne publier que le sous-ensemble utilisé si un doute subsiste |
| Appel d'outils instable en démo | Démo ratée | Enregistrement de secours (FR-11) |
| Démo publique qui consomme les crédits | Démo coupée | Limite d'usage ; alerte de dépense |
| Dérive de périmètre | Rien de fini | Gel le 3 novembre ; tout le reste dans `docs/decisions.md` |
| Un juge trouve la V1 | Doute sur « new work only » | Section du README sur la V1 (section 14) |

---

## 13. Vidéo (3 minutes, sous-titres anglais)

1. **0:00–0:20 :** le moment fort d'abord. L'élève dit « 14 de moyenne », le relevé donne 11,2, l'agent s'arrête et demande.
2. **0:20–0:45 :** le problème, avec un seul chiffre sourcé.
3. **0:45–2:00 :** un cas complet, avec la trace des outils à l'écran et les preuves cliquables dans le rapport.
4. **2:00–2:30 :** un cas difficile : photo floue, zoom ou nouvelle demande.
5. **2:30–2:50 :** le tableau des 10 évaluations, « 0 affirmation sans preuve », et la ligne Pharmacie écartée par le contrôle qualité.
6. **2:50–3:00 :** ce qui est nouveau, les limites, l'équipe, le compte X.

---

## 14. Rapport avec la V1

Texte à mettre dans le README :

> An earlier prototype by the same author (OrientBot V1, a fixed WhatsApp workflow, 7 users, now paused) explored this problem. No code from it is reused here. PathProof was built from scratch during the hackathon. Only public official rules (the MESRS weighted-average formula, subject-name normalization) were re-implemented. See `docs/v1-reuse.md`.
>
> Data: the program list comes from the official public *Guide d'information 2026-2027*. Its CSV extraction was done before the event; it is data, not code. Every recommendation links back to the guide page it comes from.

---

## 15. Checklist de soumission

- [ ] Dépôt public nommé PathProof, lisible sans connexion
- [ ] README : statut réel, section « What is new », section V1, modèles Meta utilisés, limites, équipe
- [ ] Vidéo de 3 minutes, lien dans le README
- [ ] URL de démo publique, testée depuis un autre appareil
- [ ] `evals/results/` avec les sorties brutes et le tableau récapitulatif
- [ ] Aucune clé, aucun chemin personnel, aucune donnée réelle
- [ ] Tous les coéquipiers listés sur la plateforme CV
- [ ] Post sur X avec la vidéo, lien soumis pour le prix Viral
- [ ] Soumission sur la plateforme CV avant le 4 novembre, 21 h ET
