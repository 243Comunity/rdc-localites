# RDC Localités

**Le découpage administratif complet de la République Démocratique du Congo, ouvert et gratuit, prêt à intégrer dans vos applications.**

Un projet de la communauté [243Comunity](https://243comunity.dev).

**Essayer en ligne : https://243comunity.github.io/rdc-localites/**

| Niveau | Nombre |
|---|---:|
| Provinces | 26 |
| Territoires et villes | 179 (145 territoires, 34 villes) |
| Communes, secteurs et chefferies | 1 044 |
| Groupements et quartiers | 8 053 |
| Villages codés (avec GPS) | 74 395 |
| Autres localités (hameaux, fermes, villages non codés…) | 33 480 |

## Pourquoi

En RDC, chaque application qui demande une adresse (mobile money, santé, agriculture, ONG, e-commerce, administration) refait à la main ses listes de provinces et de territoires, souvent incomplètes et différentes d'une application à l'autre. Ce dépôt fournit **une seule référence**, avec des identifiants stables, que tout le monde peut utiliser et améliorer.

## Utilisation rapide

### 1. API statique (aucune clé, aucun compte)

```
GET /api/v1/provinces.json
GET /api/v1/provinces/{id}.json                     → la province + ses territoires et villes
GET /api/v1/territoires-villes/{id}.json            → + ses communes, secteurs et chefferies
GET /api/v1/communes-secteurs-chefferies/{id}.json  → + ses groupements et quartiers
GET /api/v1/groupements-quartiers/{id}.json         → + ses villages et localités (avec GPS)
```

Chaque réponse contient un `chemin` (province → territoire → secteur) pour afficher une adresse complète. Exemple pour faire une liste déroulante en cascade :

```js
const BASE = "https://243comunity.github.io/rdc-localites/api/v1";
const provinces = await fetch(`${BASE}/provinces.json`).then(r => r.json());
const nordKivu  = await fetch(`${BASE}/provinces/15.json`).then(r => r.json());
console.log(nordKivu.territoires_villes); // GOMA VILLE, WALIKALE, LUBERO, BENI, RUTSHURU, ...
```

### 2. Fichiers à télécharger (usage hors ligne)

Chaque version publie dans ses *Releases* :

- `json/*.json` : une liste par niveau
- `rdc-localites.sqlite` : base SQLite indexée (~10 Mo), à embarquer dans une application mobile
- `geojson/villages.geojson`, `geojson/localites.geojson` : pour QGIS, Leaflet, Mapbox…
- `data/*.csv` : les fichiers de référence eux-mêmes

### 3. Générer soi-même

```bash
python scripts/validate.py   # vérifie les données
python scripts/build.py      # produit dist/ (JSON, GeoJSON, SQLite, API statique)
```

Python 3.10+ uniquement, sans aucune dépendance.

## Organisation du dépôt

```
data/        Les CSV de référence (la source de vérité, modifiable par pull request)
scripts/     import_excel.py (import initial), validate.py, build.py
docs/        Dictionnaire de données, rapport d'import
site/        Page de démonstration publiée avec l'API
dist/        Généré par build.py (non versionné)
```

## Hiérarchie

Conforme à l'organisation territoriale de la RDC :

```
Province
└── Ville ─────────── Commune ─── Quartier
└── Territoire ───┬── Secteur ──┬─ Groupement ─── Village
                  └── Chefferie ┘
```

Les **localités** sont les lieux habités qui n'ont pas de code village officiel dans la source : hameaux, fermes, campements, blocs de quartier, villages non codés. Elles ont un identifiant **provisoire** (`L<groupement>-<rang>`).

Détail de toutes les colonnes : [docs/DICTIONNAIRE.md](docs/DICTIONNAIRE.md).

## Contribuer

Un village manque, un nom est mal écrit, un point GPS est faux ? Voir [CONTRIBUTING.md](CONTRIBUTING.md). Pas besoin d'être développeur : un ticket suffit.

## Feuille de route

- [x] **v0.1** Données nettoyées, validation automatique, JSON / SQLite / GeoJSON, API statique
- [ ] **v0.2** Paquets prêts à l'emploi : npm, pub.dev (Flutter), PyPI, Composer
- [ ] **v0.3** Recherche tolérante aux fautes et normalisation d'adresses (« Kin/Gombe » → Gombe, Kinshasa)
- [ ] **v0.4** Composant de sélection en cascade (web + Flutter)
- [ ] **v0.5** Noms alternatifs et anciennes orthographes, correspondance anciennes provinces (avant 2015) → actuelles
- [ ] **v1.0** Limites (polygones) des territoires et secteurs, formulaire de contribution pour le terrain

## Licences

- Code : [MIT](LICENSE)
- Données : voir [DATA_LICENSE.md](DATA_LICENSE.md)

## Source

Voir [DATA_LICENSE.md](DATA_LICENSE.md). Les noms des agents de collecte présents dans le fichier d'origine ne sont **jamais** publiés.
