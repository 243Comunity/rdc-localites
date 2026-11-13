# Dictionnaire de données

Tous les fichiers sont en UTF-8, séparateur virgule, une ligne d'en-tête. Une cellule vide signifie « inconnu ».

Les identifiants numériques sont **ceux de la source** : ils ne changent pas d'une version à l'autre. Ils ne sont pas hiérarchiques, sauf pour les communes/secteurs/chefferies (`503201` = territoire `5032` + rang `01`). Pour retrouver un parent, utilisez toujours la colonne `*_id` correspondante.

Les noms sont gardés tels que dans la source (en majuscules pour les entités administratives). Seule correction systématique : un guillemet `"` utilisé à la place d'une apostrophe est remplacé par `'` (ex. `N'JILI`).

## provinces.csv

| Colonne | Type | Description |
|---|---|---|
| id | entier | Identifiant (1 à 26) |
| nom | texte | Nom de la province |

## territoires_villes.csv

| Colonne | Type | Description |
|---|---|---|
| id | entier | Identifiant |
| nom | texte | Nom |
| type | `territoire` \| `ville` | |
| province_id | entier | → provinces.id |

## communes_secteurs_chefferies.csv

| Colonne | Type | Description |
|---|---|---|
| id | entier | Identifiant |
| nom | texte | Nom |
| type | `commune` \| `secteur` \| `chefferie` | |
| territoire_ville_id | entier | → territoires_villes.id |
| antenne_id | entier | Regroupement opérationnel de la source (ex. Kinshasa I Gombe). **Ce n'est pas un niveau administratif légal.** Dans un territoire, il est égal au territoire. |
| antenne_nom | texte | Nom de l'antenne |

## groupements_quartiers.csv

| Colonne | Type | Description |
|---|---|---|
| id | entier | Identifiant |
| nom | texte | Nom |
| type | `groupement` \| `quartier` \| `non_determine` | `non_determine` = « quartier inconnu » dans la source, à compléter |
| commune_secteur_chefferie_id | entier | → communes_secteurs_chefferies.id |

## villages.csv

| Colonne | Type | Description |
|---|---|---|
| id | entier | Code village de la source |
| nom | texte | Nom |
| groupement_quartier_id | entier | → groupements_quartiers.id |
| commune_secteur_chefferie_id | entier | → communes_secteurs_chefferies.id (redondant, pour filtrer sans jointure) |
| latitude, longitude | décimal | WGS 84 |
| altitude | décimal | mètres ; vidée si aberrante (< 0 ou > 5 200 m) |
| precision_m | décimal | précision annoncée par le GPS, en mètres |
| nb_points_gps | entier | nombre de relevés pour ce village dans la source ; le plus précis est retenu |

## localites.csv

Lieux habités sans code village dans la source.

| Colonne | Type | Description |
|---|---|---|
| id | texte | Identifiant **provisoire** `L<groupement_id>-<rang>` (ou `LS<secteur_id>-<rang>` sans groupement). Peut changer tant que la localité n'a pas de code officiel. |
| nom | texte | Nom tel que relevé (casse d'origine) |
| categorie | `village` \| `hameau` \| `ferme` \| `quartier` \| `autre` | `village` = village relevé sans code |
| groupement_quartier_id | entier | → groupements_quartiers.id (peut être vide) |
| commune_secteur_chefferie_id | entier | → communes_secteurs_chefferies.id |
| village_rattachement_nom | texte | Village de rattachement indiqué dans la source |
| village_rattachement_id | entier | → villages.id, quand le nom correspond à un seul village du même groupement |
| latitude, longitude, altitude, precision_m | décimal | comme pour les villages |
