# Journal des changements

## Non publié

## 0.1.1 — 2026-11-13

- Encodage : 14 noms abîmés corrigés (OÏCHA, BATETELA ARABISÉS-LOMAMI, EMMAÜS, ZAÏRE…).
  16 noms dont une lettre est perdue sont listés dans `docs/A_VERIFIER.md`.
- Dates créées par Excel remplacées par le vrai nom du quartier (30 JUIN, 4 JANVIER, 17 MAI).
- `_` remplacé par une espace, apostrophes typographiques uniformisées.
- Une fiche marquée « à supprimer » par les agents de collecte retirée.
- `validate.py` refuse désormais les noms abîmés par l'encodage ou par Excel.
- Page de démonstration : sélection en cascade province → village, carte des villages du groupement.
- Fermes : position arrondie à ~1 km et précision GPS retirée (vie privée des propriétaires).
- Licence des données : CC BY 4.0.
- Contributions : pull requests obligatoires vers `main`, relecture par le mainteneur
  (`CODEOWNERS`), modèle de pull request.
- API statique republiée automatiquement à chaque changement sur `main` (dépôt public).

## 0.1.0 — 2026-11-13

- Import initial depuis le fichier Excel source (voir `docs/rapport_import.md`).
- 26 provinces, 179 territoires/villes, 1 044 communes/secteurs/chefferies,
  8 053 groupements/quartiers, 74 395 villages codés, 33 480 localités.
- Scripts `validate.py` et `build.py` ; sorties JSON, GeoJSON, SQLite et API statique.
