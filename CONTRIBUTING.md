# Contribuer à RDC Localités

Merci ! Ce projet vit grâce aux personnes qui connaissent le terrain.

## Signaler une erreur (sans coder)

Ouvrez un ticket avec le modèle **« Correction de données »** et indiquez :

- l'entité concernée (nom + identifiant si vous l'avez) ;
- ce qui est faux et la bonne valeur ;
- **comment vous le savez** (vous êtes sur place, document officiel, carte…).

Les tickets sans source restent ouverts jusqu'à confirmation par une deuxième personne.

## Corriger directement (pull request)

1. Modifiez le CSV concerné dans `data/` (gardez l'ordre des colonnes).
2. Lancez `python scripts/validate.py` : il doit afficher `0 erreur(s)`.
3. Une PR = un sujet (ex. « Lubero : 12 villages du groupement Baswagha »).
4. Ajoutez une ligne dans `CHANGELOG.md` sous « Non publié ».

### Règles

- **Ne jamais modifier un identifiant existant.** Des applications l'ont peut-être déjà enregistré.
- Une entité qui n'existe plus n'est pas supprimée sans discussion : ouvrez d'abord un ticket.
- Nouveau village sans code officiel → ajoutez-le dans `localites.csv`, catégorie `village`.
- Aucune donnée personnelle (nom d'un agent, téléphone, propriétaire d'une parcelle…).

## Contribuer au code

Bienvenue sur : paquets npm / pub.dev / PyPI, recherche tolérante aux fautes, composant de sélection en cascade, documentation. Regardez les tickets étiquetés `good first issue`.

## Versions

Les données suivent le versionnage sémantique :

- **correctif** (0.1.**1**) : corrections de noms ou de GPS ;
- **mineure** (0.**2**.0) : ajout d'entités ou de colonnes ;
- **majeure** (**1**.0.0) : changement qui casse l'existant (colonne renommée, identifiant modifié).
