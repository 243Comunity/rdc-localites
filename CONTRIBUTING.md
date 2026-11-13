# Contribuer à RDC Localités

Merci ! Ce projet vit grâce aux personnes qui connaissent le terrain : un village manquant,
un nom mal écrit, un groupement mal rattaché, tout compte.

## Comment ça marche

```
Vous (fork ou branche) ──► Pull request ──► Vérification automatique ──► Relecture du mainteneur ──► main
```

- **Personne ne pousse directement sur `main`.** Toute modification passe par une pull request.
- La vérification automatique (`scripts/validate.py`) doit être verte.
- Seul le mainteneur du projet peut fusionner dans `main` (voir `.github/CODEOWNERS`).

## 1. Signaler sans coder

Ouvrez un ticket (**Issues → New issue → Correction de données**) et indiquez :

- l'entité concernée (nom, identifiant si vous l'avez, et le chemin province / territoire / secteur / groupement) ;
- ce qui est faux, ou ce qui manque ;
- **comment vous le savez** : vous êtes sur place, document officiel, carte…

## 2. Proposer une modification

1. **Forkez** le dépôt (bouton *Fork* en haut à droite), ou créez une branche si vous êtes membre de l'organisation.
   Nommez la branche selon le sujet : `ajout/lubero-baswagha`, `correction/noms-kwilu`…
2. Modifiez le CSV concerné dans `data/`, en gardant l'ordre des colonnes.
3. Vérifiez localement :
   ```bash
   python scripts/validate.py   # doit afficher « 0 erreur(s) »
   ```
4. Ajoutez une ligne dans `CHANGELOG.md`, section « Non publié ».
5. Ouvrez une **pull request vers `main`** et remplissez le modèle proposé.

**Une pull request = un sujet** (par exemple « Lubero : 12 villages du groupement Baswagha »). C'est plus facile à relire.

## Où ajouter quoi

| Je veux… | Fichier | Identifiant |
|---|---|---|
| Ajouter un village qui a un code officiel | `villages.csv` | le code officiel |
| Ajouter un village, hameau ou campement **sans** code officiel | `localites.csv` (catégorie `village`, `hameau`…) | `L<groupement_id>-<numéro suivant>` |
| Corriger un nom | le fichier de l'entité | ne pas toucher l'identifiant |
| Corriger un rattachement | colonne `*_id` du parent | ne pas toucher l'identifiant |

## Règles

- **Ne jamais modifier un identifiant existant** : des applications l'ont peut-être déjà enregistré.
- Ne supprimez pas une entité sans en discuter d'abord dans un ticket.
- Indiquez toujours votre source dans la pull request.
- **Aucune donnée personnelle** : pas de nom d'agent, de téléphone, ni de position exacte d'une propriété privée.

## Contribuer au code

Bienvenue aussi sur : paquets npm / pub.dev / PyPI, recherche tolérante aux fautes, composant de
sélection en cascade, documentation. Regardez les tickets étiquetés `good first issue`.

## Versions

Les données suivent le versionnage sémantique :

- **correctif** (0.1.**1**) : corrections de noms ou de GPS ;
- **mineure** (0.**2**.0) : ajout d'entités ou de colonnes ;
- **majeure** (**1**.0.0) : changement qui casse l'existant (colonne renommée, identifiant modifié).

Le mainteneur publie une nouvelle version en créant une *release* sur GitHub ; les fichiers
téléchargeables sont générés automatiquement.
