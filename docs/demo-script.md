# Script de la vidéo (3 minutes, sous-titres anglais)

À écrire définitivement une fois l'agent fonctionnel (vidéo prévue le 3 novembre). Plan, aligné sur `docs/prd.md` section 13 :

1. **0:00-0:20 : le moment fort d'abord.** L'élève fictif dit « 14 de moyenne », le relevé donne 11,2 : l'agent s'arrête et demande.
2. **0:20-0:45 : le problème**, avec un seul chiffre sourcé : 77 101 candidats au Bac 2026 (Office du Baccalauréat relayé par la presse, voir `docs/impact.md`).
3. **0:45-2:00 : un cas complet.** La trace des outils à l'écran, les preuves cliquables dans le rapport. Message clé : la moyenne de classement de Médecine (13,15) diffère de la moyenne au Bac (11,20), parce que la SVT y compte 5 fois (guide, page 8). Ces chiffres sont ceux de l'exemple fictif du PRD, à remplacer par les sorties réelles.
4. **2:00-2:30 : un cas difficile.** Photo floue : l'agent demande une nouvelle photo ou la note (pas de `zoom_cell`, NO GO au spike E0.6).
5. **2:30-2:50 : le tableau des 10 évaluations**, « 0 affirmation sans preuve », et la ligne Pharmacie écartée par le contrôle qualité.
6. **2:50-3:00 : ce qui est nouveau, les limites, l'équipe, le compte X.**

Règles :
- Ne montrer que ce qui fonctionne réellement. Si l'API échoue, la démo affiche une exécution enregistrée, en le disant.
- Le mot « chatbot » n'apparaît ni dans la vidéo, ni dans l'interface.
- Ne montrer que le travail fait pendant l'événement.
