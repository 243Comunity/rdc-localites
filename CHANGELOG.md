# Journal des changements

## Non publié

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
