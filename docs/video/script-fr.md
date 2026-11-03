# Script de la voix off — français

Durée à l'écran : 2:58 au plus (limite 3:00). Voix off seule : pas de visage, pas de musique avec paroles.
Rythme : environ 2,5 mots par seconde en français, avec des silences laissés à l'interface. Chaque bloc donne sa fenêtre et ses plans (voir `production-plan.md`) ; le nombre de mots est contrôlé dans `production-plan.md`.

Ton : posé, comme on explique à un collègue. Les nombres sont dits en toutes lettres. Les sous-titres restent **en anglais** (voir `script-en.md`).

---

## V1 · 0:00–0:20 · Le moment fort (plans S01, S02)

Une élève dit avoir quatorze de moyenne. Son relevé de notes affiche onze virgule deux. La plupart des outils choisiraient l'une des deux et continueraient. Cet agent s'arrête, et lui pose la question. Voici PathProof : chaque filière vient avec sa preuve.

## V2 · 0:20–0:45 · Le problème, un seul chiffre sourcé (plans S03, S04)

En juin 2026, soixante-dix-sept mille candidats ont passé le baccalauréat au Bénin. Choisir une filière peut se résumer à une rumeur. Pourtant, le guide officiel classe filière par filière, sur trois matières, avec les coefficients de votre série. Pas sur votre moyenne générale. PathProof calcule cela, et montre sa preuve.

## V3a · 0:45–1:05 · Un cas complet, les entrées (plans S05, S06)

Voici un parcours complet, avec une élève fictive de série D. Une photo de relevé et une note vocale entrent. L'agent choisit lui-même ses outils, pas à pas, et chaque étape montre quel modèle Meta a décidé et lequel a exécuté.

## V3b · 1:05–1:30 · Un cas complet, la trace (plans S07, S08)

Muse Voice Transcribe écoute la note. Muse Spark lit le relevé. Le Contributor choisit l'outil suivant, et pose une question avant de continuer. Ensuite, du code ordinaire, pas le modèle, filtre les filières et calcule les moyennes. Wonder rédige le rapport.

## V3c · 1:30–2:00 · Un cas complet, les preuves (plans S09, S10, S11)

Médecine se classe à treize virgule un cinq, au-dessus de sa moyenne du bac de onze virgule deux. La formule retient trois matières, et la biologie, sa meilleure, compte cinq fois. Chaque phrase ouvre sa preuve : la note lue sur la photo, ses propres mots, la ligne du guide avec sa page, le calcul. Un vérificateur en code bloque toute affirmation sans preuve.

## V4 · 2:00–2:30 · Un cas difficile (plans S12, S13)

Maintenant, un cas difficile. Même élève, photo floue : la note de mathématiques est illisible. L'agent ne devine pas, et ne la déduit pas du total. Il demande une photo plus nette. Nous avons aussi testé SAM 3.1 pour zoomer sur une cellule : il trouve le tableau, jamais la cellule, nous l'avons donc abandonné.

## V5 · 2:30–2:50 · Les évaluations et une ligne écartée (plans S14, S15)

Nous avons fait passer onze cas fictifs à l'agent réel : les onze sont conformes, un seul passage chacun. Le vérificateur n'a trouvé aucune affirmation sans preuve. Un élève qui veut faire pharmacie ? Cette ligne du guide n'a pas passé le contrôle qualité : elle revient comme écartée, jamais recommandée.

## V6 · 2:50–2:58 · Ce qui est nouveau, les limites, l'équipe (plan S16)

Construit en solo pendant ce hackathon. Données fictives, séries C et D seulement. À essayer sur pathproof-six.vercel.app.

---

## Sous-titres

Les sous-titres sont **en anglais**, même sur la version à voix française (critère de l'issue #39) : on reprend les cues de `script-en.md`, calées sur l'audio français enregistré.
