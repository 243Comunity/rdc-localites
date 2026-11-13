"""Outils partagés : lecture des CSV de data/ (bibliothèque standard uniquement)."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# Ordre hiérarchique officiel (loi organique n° 08/016) + localités non codées
TABLES = [
    "provinces",
    "territoires_villes",
    "communes_secteurs_chefferies",
    "groupements_quartiers",
    "villages",
    "localites",
]

INT_FIELDS = {
    "id", "province_id", "territoire_ville_id", "antenne_id",
    "commune_secteur_chefferie_id", "groupement_quartier_id",
    "village_rattachement_id", "nb_points_gps",
}
FLOAT_FIELDS = {"latitude", "longitude", "altitude", "precision_m"}


def _convert(table: str, key: str, value: str):
    if value == "":
        return None
    if key == "id" and table == "localites":
        return value  # identifiant provisoire texte (L<parent>-<rang>)
    if key in INT_FIELDS:
        return int(value)
    if key in FLOAT_FIELDS:
        return float(value)
    return value


def load(table: str) -> list[dict]:
    with open(DATA / f"{table}.csv", encoding="utf-8", newline="") as f:
        return [{k: _convert(table, k, v) for k, v in row.items()} for row in csv.DictReader(f)]


def load_all() -> dict[str, list[dict]]:
    return {t: load(t) for t in TABLES}
