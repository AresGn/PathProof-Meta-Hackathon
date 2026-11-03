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
- `MUSE_API_KEY` : saisie dans Vercel (tableau de bord), jamais dans le dépôt. Elle est définie pour Production **et** Preview : les prévisualisations sont donc protégées par la connexion Vercel (302 vérifié sur l'URL d'un déploiement et sur l'alias de branche), seul le domaine de production est public.
- `MUSE_BASE_URL` : seulement si différente de `https://api.meta.ai/v1`.

## Limite d'usage par IP
Règle Vercel Firewall sur `POST /run` et `POST /answer` : **5 requêtes par minute et par IP**, au-delà réponse **429** avant d'atteindre la fonction (donc sans coût d'API). Une exécution complète = 1 `/run` + au plus 2 `/answer`. Les compteurs sont par région : plusieurs régions peuvent cumuler jusqu'à N fois le seuil. Le serveur garde en plus ses plafonds internes (5 runs simultanés, 100 sessions suspendues).

Commande : voir la section « Vérification » ci-dessous pour la preuve du 429.

## Dépense
Le plan Vercel est Hobby, sans carte : Vercel ne facture rien (un quota dépassé bloque le service), donc aucune alerte de dépense Vercel n'est utile. Le coût réel est celui des crédits Meta consommés par chaque exécution ; il est borné par la limite par IP ci-dessus, par les 5 exécutions simultanées et par l'**alerte de dépense Meta** (Billing), activée dès le premier jour par le titulaire de la clé (E0.2, #4).

## Limite assumée : sessions `ask_student`
`PendingRunStore` est en mémoire. Sur Vercel, `/answer` peut tomber sur une autre instance que `/run` : réponse 404, la page restaure la trace et ferme la session (l'enregistrement E5.3 ne remplace pas ce cas, par choix : voir `docs/decisions.md`). Un stockage partagé n'est pas mis en place avant le gel du 3 nov.

## Voix : ffmpeg
Une fonction Vercel n'a pas `ffmpeg` : `transcribe_voice` échouait en production (« ffmpeg is not installed »). `src/clients/voice.py` prend `ffmpeg` du système s'il existe, sinon le binaire embarqué par `imageio-ffmpeg` (dans `requirements.txt`). Vérifié sur l'URL publique : 3 transcriptions sur 3 réussies.

## Mesures sur l'URL publique (3 nov 2026)
- Exécution complète (relevé série D + note vocale cohérente) : `done` / `ok` en 164 s au total, rapport vérifié de 4 050 caractères, flux SSE diffusé pas à pas ; `/run` seul 22 à 60 s, `/answer` jusqu'à 190 s, chacun sous les 300 s.
- `/answer` : 200 dans 5 essais sur 6 ; **un 404** (session perdue entre instances), conforme à la limite ci-dessus. Le taux observé n'est pas nul : si la démo vidéo s'y heurte, enregistrer sur la page locale ou passer à un stockage partagé.
- Un essai a atteint la limite de 12 pas sans rapport (le modèle répétait `verify_report`) : comportement de l'agent (E6.3), pas de l'hébergement.
- Limite par IP : 5 requêtes `POST` à 200 puis 3 à 429 sur 8 appels.

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
