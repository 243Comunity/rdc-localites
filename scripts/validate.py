#!/usr/bin/env python3
"""Vérifie la cohérence des CSV de data/. Lancé par la CI sur chaque pull request.

Code de sortie 1 s'il y a au moins une erreur. Les avertissements ne bloquent pas.
"""
from __future__ import annotations

import sys
from collections import Counter

from common import load_all

# Boîte englobante de la RDC (avec une petite marge)
LAT_MIN, LAT_MAX = -13.6, 5.5
LON_MIN, LON_MAX = 12.0, 31.5

ENUMS = {
    ("territoires_villes", "type"): {"territoire", "ville"},
    ("communes_secteurs_chefferies", "type"): {"commune", "secteur", "chefferie"},
    ("groupements_quartiers", "type"): {"groupement", "quartier", "non_determine"},
    ("localites", "categorie"): {"village", "hameau", "ferme", "quartier", "autre"},
}

COLUMNS = {
    "provinces": ["id", "nom"],
    "territoires_villes": ["id", "nom", "type", "province_id"],
    "communes_secteurs_chefferies": ["id", "nom", "type", "territoire_ville_id", "antenne_id", "antenne_nom"],
    "groupements_quartiers": ["id", "nom", "type", "commune_secteur_chefferie_id"],
    "villages": ["id", "nom", "groupement_quartier_id", "commune_secteur_chefferie_id",
                 "latitude", "longitude", "altitude", "precision_m", "nb_points_gps"],
    "localites": ["id", "nom", "categorie", "groupement_quartier_id", "commune_secteur_chefferie_id",
                  "village_rattachement_nom", "village_rattachement_id",
                  "latitude", "longitude", "altitude", "precision_m"],
}

# Clés étrangères : (table, colonne) -> table cible ; obligatoire ?
FKS = [
    ("territoires_villes", "province_id", "provinces", True),
    ("communes_secteurs_chefferies", "territoire_ville_id", "territoires_villes", True),
    ("groupements_quartiers", "commune_secteur_chefferie_id", "communes_secteurs_chefferies", True),
    ("villages", "groupement_quartier_id", "groupements_quartiers", True),
    ("villages", "commune_secteur_chefferie_id", "communes_secteurs_chefferies", True),
    ("localites", "groupement_quartier_id", "groupements_quartiers", False),
    ("localites", "commune_secteur_chefferie_id", "communes_secteurs_chefferies", True),
    ("localites", "village_rattachement_id", "villages", False),
]

FORBIDDEN = {"username", "agent", "enqueteur", "telephone", "email"}


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    db = load_all()
    ids = {t: {r["id"] for r in rows} for t, rows in db.items()}

    for t, rows in db.items():
        cols = list(rows[0].keys()) if rows else []
        if cols != COLUMNS[t]:
            errors.append(f"{t}: colonnes {cols} au lieu de {COLUMNS[t]}")
        if FORBIDDEN & {c.lower() for c in cols}:
            errors.append(f"{t}: colonne de données personnelles interdite")
        dup = [i for i, n in Counter(r["id"] for r in rows).items() if n > 1]
        if dup:
            errors.append(f"{t}: {len(dup)} identifiants en double (ex. {dup[:5]})")
        missing_name = [r["id"] for r in rows if not r.get("nom")]
        if missing_name:
            errors.append(f"{t}: {len(missing_name)} lignes sans nom (ex. {missing_name[:5]})")
        for (tt, col), allowed in ENUMS.items():
            if tt == t:
                bad = {r[col] for r in rows} - allowed
                if bad:
                    errors.append(f"{t}.{col}: valeurs inconnues {sorted(map(str, bad))}")
        if "latitude" in cols:
            out = [r["id"] for r in rows if r["latitude"] is not None and not (
                LAT_MIN <= r["latitude"] <= LAT_MAX and LON_MIN <= (r["longitude"] or 0) <= LON_MAX)]
            if out:
                errors.append(f"{t}: {len(out)} coordonnées hors de la RDC (ex. {out[:5]})")
            no_gps = sum(1 for r in rows if r["latitude"] is None)
            if no_gps:
                warnings.append(f"{t}: {no_gps} lignes sans coordonnées GPS")

    for t, col, target, required in FKS:
        rows = db[t]
        if required:
            empty = [r["id"] for r in rows if r[col] is None]
            if empty:
                errors.append(f"{t}.{col}: {len(empty)} valeurs vides (ex. {empty[:5]})")
        broken = [r["id"] for r in rows if r[col] is not None and r[col] not in ids[target]]
        if broken:
            errors.append(f"{t}.{col}: {len(broken)} références vers {target} inexistantes (ex. {broken[:5]})")

    # Cohérence : la commune/secteur d'un village = celle de son groupement
    gq_parent = {r["id"]: r["commune_secteur_chefferie_id"] for r in db["groupements_quartiers"]}
    for t in ("villages", "localites"):
        bad = [r["id"] for r in db[t] if r["groupement_quartier_id"] is not None
               and gq_parent.get(r["groupement_quartier_id"]) != r["commune_secteur_chefferie_id"]]
        if bad:
            errors.append(f"{t}: {len(bad)} lignes dont la commune/secteur ne correspond pas au groupement (ex. {bad[:5]})")

    # Avertissement : même nom de village deux fois dans un groupement
    c = Counter((r["groupement_quartier_id"], r["nom"].upper()) for r in db["villages"])
    dups = [k for k, n in c.items() if n > 1]
    if dups:
        warnings.append(f"villages: {len(dups)} noms en double dans un même groupement (ex. {dups[:3]})")

    for w in warnings:
        print(f"AVERTISSEMENT  {w}")
    for e in errors:
        print(f"ERREUR         {e}")
    total = sum(len(r) for r in db.values())
    total_txt = f"{total:,}".replace(",", " ")
    print(f"\n{total_txt} entités vérifiées, {len(errors)} erreur(s), {len(warnings)} avertissement(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
