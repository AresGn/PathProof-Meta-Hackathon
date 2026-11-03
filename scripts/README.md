# scripts

## Tranche verticale sans vision ni voix (E2.5)

Commande (depuis la racine du dépôt, sans clé ni API) :

```bash
python scripts/run_vertical_slice.py data/samples/vertical_slice_serie_d.json
```

Lit la fixture JSON (notes série D + profil fictifs), calcule les moyennes de
classement par `compute_ranking_average`, filtre les offres par la recherche
provisoire (`Statut_qualité = OK` + `Bac_recommandé`, remplacée par E3.5),
construit un brouillon avec preuves et l'imprime seulement si `verify_report`
renvoie une liste vide. Code de sortie 1, sans rapport imprimé, si le
vérificateur refuse le brouillon.

Test d'intégration associé : `python -m pytest -q tests/test_vertical_slice.py`.

## Tirage de l'audit de données (E3.3)

```bash
python scripts/sample_audit.py --seed 2026
```

Affiche 20 `Offre_ID` de lignes `Statut_qualité = OK`, un par ligne, dans
l'ordre du tirage. Relancer avec la même graine donne les mêmes 20 lignes
(test : `tests/test_sample_audit.py`). L'audit comparant ces lignes au PDF
est publié dans `docs/data-audit.md`.

## Colonne faculte_classique (E3.4)

```bash
python scripts/make_faculte_classique.py --output data/faculte_classique.csv
```

Produit `data/faculte_classique.csv` (`Offre_ID`, `faculte_classique`
`oui`/`non`) depuis les offres recommandables du guide (`OK` à page
établie) : `oui` quand l'établissement commence par « Faculté ».
Sans `--output`, le CSV part sur la sortie standard (le test
`tests/test_faculte_classique.py` le compare au fichier commité, et
exige stderr vide). E3.5 a réparé les libellés et rétabli les pages :
plus aucune exception relue à la main ne subsiste.

## Réparation des données du guide (E3.5)

```bash
python scripts/repair_guide_data_e35.py
```

Applique aux CSV du guide les réparations vérifiées au PDF et tracées
dans `docs/data-audit.md` (libellés en quarantaine, pages rétablies,
espaces de `PUB-032`, séries `DEAT`/`EA` de `PUB-211`, filière de
`PUB-189`, marqueur « non publié » sur les cellules « – »). Idempotent ;
à ne relancer que sur une nouvelle extraction.

## Fichiers d'exemple fictifs (E0.3, E6.1)

```bash
pip install pillow                                       # outil de dev, hors requirements.txt
python scripts/make_grade_sheets.py                      # relevés JPEG (Arial ou Liberation Sans)
python scripts/make_voice_notes.py note_vocale_bruitee.mp3   # ElevenLabs, ELEVENLABS_API_KEY dans .env
```

Pillow reste hors de `requirements.txt` pour ne pas alourdir la fonction
Vercel. `make_voice_notes.py` utilise le ffmpeg de `imageio-ffmpeg`.
