# Déploiement public sur Vercel (E5.4, #33)

Un seul projet Vercel, production = `main`, redéployé à chaque push. Ni staging, ni Docker.

## Configuration
| Élément | Valeur |
|---|---|
| Point d'entrée | `app.py` (racine) : réexporte `app` de `src/api/server.py` |
| Fichiers inclus | `vercel.json` : `web/**` et `data/**` (sans `data/source/**`, le PDF du guide n'est jamais déployé) |
| Durée maximale | 300 s (`maxDuration`, plafond du plan Hobby) ; le flux SSE reste ouvert pendant toute l'exécution |
| Disque | Seul `/tmp` est inscriptible : `new_run_tmpdir` l'utilise quand `VERCEL` est défini (les dépôts de l'élève y sont supprimés après le run ou après 30 min) |
| Projet | `.vercel/` est ignoré par git (identifiants locaux) |

## Variables d'environnement
- `MUSE_API_KEY` : **cible Production uniquement**, saisie dans Vercel (`vercel env add MUSE_API_KEY production`). Aucun fichier du dépôt ne la contient ; les déploiements de prévisualisation n'ont pas la variable et la protection Standard de Vercel reste active.
- `MUSE_BASE_URL` : seulement si différente de `https://api.meta.ai/v1`.

## Limite d'usage par IP
Règle Vercel Firewall sur `POST /run` et `POST /answer` : **5 requêtes par minute et par IP**, au-delà réponse **429** avant d'atteindre la fonction (donc sans coût d'API). Une exécution complète = 1 `/run` + au plus 2 `/answer`. Les compteurs sont par région : plusieurs régions peuvent cumuler jusqu'à N fois le seuil. Le serveur garde en plus ses plafonds internes (5 runs simultanés, 100 sessions suspendues).

Commande : voir la section « Vérification » ci-dessous pour la preuve du 429.

## Limite assumée : sessions `ask_student`
`PendingRunStore` est en mémoire. Sur Vercel, `/answer` peut tomber sur une autre instance que `/run` : réponse 404, la page restaure la trace et ferme la session (l'enregistrement E5.3 ne remplace pas ce cas, par choix : voir `docs/decisions.md`). Un stockage partagé n'est pas mis en place avant le gel du 3 nov.

## Vérification (à rejouer depuis un autre réseau)
```bash
URL=https://<projet>.vercel.app
curl -s $URL/health
curl -s $URL | grep -c MUSE           # 0
for f in $(curl -s $URL | grep -o 'js/[a-z-]*\.js'); do curl -s $URL/$f | grep -c MUSE; done   # 0
for i in $(seq 1 8); do curl -s -o /dev/null -w "%{http_code}\n" -X POST $URL/run -F text=bonjour; done   # 429 au-delà du seuil
```

## Gel
Aucun déploiement après le gel du 3 nov au soir. Retour arrière : `vercel rollback` ou promotion du déploiement précédent depuis le tableau de bord.
