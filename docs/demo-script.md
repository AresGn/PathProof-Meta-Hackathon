# Script de la vidéo (3 minutes, sous-titres anglais)

Les textes de la voix off et le plan de production sont dans `docs/video/` : [`script-en.md`](video/script-en.md), [`script-fr.md`](video/script-fr.md), [`production-plan.md`](video/production-plan.md) (story E7.2, #39). Ce fichier garde le plan d'ensemble, aligné sur `docs/prd.md` section 13 :

1. **0:00-0:20 : le moment fort d'abord.** L'élève fictif dit « 14 de moyenne », le relevé donne 11,2 : l'agent s'arrête et demande.
2. **0:20-0:45 : le problème**, avec un seul chiffre sourcé : 77 101 candidats au Bac 2026 (Office du Baccalauréat relayé par la presse, voir `docs/impact.md`).
3. **0:45-2:00 : un cas complet.** La trace des outils à l'écran, les preuves cliquables dans le rapport. Message clé : la moyenne de classement de Médecine (13,15) diffère de la moyenne au Bac (11,20), parce que la formule ne retient que trois matières et que la SVT, sa meilleure, y compte 5 fois (guide, page 8). Ces chiffres ont été vérifiés sur le relevé fictif (171 / 13 = 13,15 ; moyenne affichée 11,20) et sur une exécution réelle du 3 novembre.
4. **2:00-2:30 : un cas difficile.** Photo floue : l'agent demande une nouvelle photo ou la note (pas de `zoom_cell`, NO GO au spike E0.6).
5. **2:30-2:50 : le tableau des 11 évaluations** (11 conformes, un passage chacun), « 0 affirmation sans preuve » (rejeu de `verify_report`), et la ligne Pharmacie écartée par le contrôle qualité (visible comme ligne exclue dans le résultat de `lookup_filieres`, pas dans le texte du rapport).
6. **2:50-3:00 : ce qui est nouveau, les limites, l'équipe, le compte X.**

Règles :
- Ne montrer que ce qui fonctionne réellement. Si l'API échoue, la démo affiche une exécution enregistrée, en le disant.
- Le mot « chatbot » n'apparaît ni dans la vidéo, ni dans l'interface.
- Ne montrer que le travail fait pendant l'événement.
