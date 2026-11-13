#!/usr/bin/env python3
"""Importe le fichier Excel source et produit les CSV de référence dans data/.

Usage :
    python scripts/import_excel.py chemin/vers/Data_Localites.xlsx

Ce script n'est lancé que lorsqu'une nouvelle version du fichier source arrive.
Les CSV de data/ sont ensuite la source de vérité : les corrections de la
communauté se font directement dans ces CSV, par pull request.

Ce qui est volontairement exclu de la publication :
  - la colonne des agents de collecte (noms de personnes = données personnelles) ;
  - les lignes cassées (texte débordant d'une cellule sur plusieurs lignes) ;
  - les points GPS sans aucun nom ni code.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"

TYPE_TV = {"T": "territoire", "V": "ville"}
TYPE_CSC = {"C": "commune", "S": "secteur", "H": "chefferie"}
TYPE_GQ = {"G": "groupement", "Q": "quartier", "C": "non_determine"}

ALT_MIN, ALT_MAX = 0, 5200  # le point culminant de la RDC est ~5 109 m


def clean_name(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value)
    s = s.replace('"', "'")  # N"JILI -> N'JILI : l'apostrophe a été remplacée par un guillemet
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def slug(value: str | None) -> str | None:
    if not value:
        return None
    s = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or None


def to_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def main(xlsx: str) -> None:
    raw = pd.read_excel(xlsx, dtype=str)
    raw.columns = [c.split(",")[0].strip() for c in raw.columns]
    n_raw = len(raw)

    report: dict[str, int | str] = {"lignes_source": n_raw}

    # 1. Lignes cassées : pas de province => débris d'une cellule multi-lignes
    df = raw[raw["province_id"].notna()].copy()
    report["lignes_cassees_supprimees"] = n_raw - len(df)

    df = df.drop(columns=["username"])  # données personnelles, jamais publiées

    for col in ["province_id", "antenne_id", "territoire_ville_id",
                "secteur_chefferie_commune_id", "groupement_quartier_id", "village_id"]:
        df[col] = to_int(df[col])
    for col in ["latitude", "longitude", "altitude", "precision"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["province", "antenne", "territoire_ville", "secteur_chefferie_commune",
                "groupement_quartier", "nom_village", "lieu_habite", "village_ratachement"]:
        df[col] = df[col].map(clean_name)

    bad_alt = df["altitude"].notna() & ~df["altitude"].between(ALT_MIN, ALT_MAX)
    report["altitudes_aberrantes_mises_a_vide"] = int(bad_alt.sum())
    df.loc[bad_alt, "altitude"] = pd.NA

    # ---------- Niveaux administratifs ----------
    provinces = (df[["province_id", "province"]].drop_duplicates()
                 .rename(columns={"province_id": "id", "province": "nom"})
                 .sort_values("id"))

    tv = (df[["territoire_ville_id", "territoire_ville", "type_territoire_ville", "province_id"]]
          .drop_duplicates()
          .rename(columns={"territoire_ville_id": "id", "territoire_ville": "nom",
                           "type_territoire_ville": "type"})
          .sort_values("id"))
    tv["type"] = tv["type"].map(TYPE_TV)

    csc = (df[["secteur_chefferie_commune_id", "secteur_chefferie_commune",
               "type_secteur_chefferie_commune", "territoire_ville_id", "antenne_id", "antenne"]]
           .drop_duplicates()
           .rename(columns={"secteur_chefferie_commune_id": "id", "secteur_chefferie_commune": "nom",
                            "type_secteur_chefferie_commune": "type",
                            "antenne": "antenne_nom"})
           .sort_values("id"))
    csc["type"] = csc["type"].map(TYPE_CSC)

    gq_src = df[df["groupement_quartier_id"].notna()]
    gq = (gq_src[["groupement_quartier_id", "groupement_quartier", "type_groupement_quartier",
                  "secteur_chefferie_commune_id"]]
          .drop_duplicates()
          .rename(columns={"groupement_quartier_id": "id", "groupement_quartier": "nom",
                           "type_groupement_quartier": "type",
                           "secteur_chefferie_commune_id": "commune_secteur_chefferie_id"})
          .sort_values("id"))
    gq["type"] = gq["type"].map(TYPE_GQ)

    # ---------- Villages codés ----------
    report["villages_codes_sans_nom_exclus"] = int(
        df.loc[df["village_id"].notna() & df["nom_village"].isna(), "village_id"].nunique())
    vsrc = df[df["village_id"].notna() & df["nom_village"].notna()].copy()
    vsrc["_prec"] = vsrc["precision"].fillna(1e9)
    vsrc = vsrc.sort_values(["village_id", "_prec"])
    n_points = vsrc.groupby("village_id").size()
    villages = vsrc.drop_duplicates("village_id", keep="first")  # meilleur point GPS
    villages = pd.DataFrame({
        "id": villages["village_id"],
        "nom": villages["nom_village"],
        "groupement_quartier_id": villages["groupement_quartier_id"],
        "commune_secteur_chefferie_id": villages["secteur_chefferie_commune_id"],
        "latitude": villages["latitude"].round(7),
        "longitude": villages["longitude"].round(7),
        "altitude": villages["altitude"].round(1),
        "precision_m": villages["precision"].round(3),
        "nb_points_gps": villages["village_id"].map(n_points).astype("Int64"),
    }).sort_values("id")
    report["villages_avec_plusieurs_points_gps"] = int((n_points > 1).sum())

    # ---------- Localités (lieux habités sans code village) ----------
    lsrc = df[df["village_id"].isna() & df["lieu_habite"].notna()].copy()
    lsrc["categorie"] = lsrc["statut_entite"].fillna("autre")
    # Rattachement : nom de village -> id, si le nom est unique dans le même groupement/secteur
    key = villages.assign(_k=villages["nom"].str.upper())
    key["_g"] = key["groupement_quartier_id"].astype("string").fillna("s" + key["commune_secteur_chefferie_id"].astype("string"))
    uniq = key.groupby(["_g", "_k"])["id"].agg(["count", "first"]).reset_index()
    uniq = uniq[uniq["count"] == 1].set_index(["_g", "_k"])["first"]
    lsrc["_g"] = lsrc["groupement_quartier_id"].astype("string").fillna("s" + lsrc["secteur_chefferie_commune_id"].astype("string"))
    lsrc["_k"] = lsrc["village_ratachement"].str.upper()
    idx = pd.MultiIndex.from_arrays([lsrc["_g"], lsrc["_k"]])
    lsrc["village_rattachement_id"] = pd.array(uniq.reindex(idx).values, dtype="Int64")

    # Identifiants provisoires stables : L<parent>-<rang> dans un ordre déterministe
    lsrc = lsrc.sort_values(["_g", "categorie", "lieu_habite", "latitude", "longitude"], na_position="last")
    lsrc["_rang"] = lsrc.groupby("_g").cumcount() + 1
    lsrc["id"] = "L" + lsrc["_g"].str.replace("s", "S", regex=False) + "-" + lsrc["_rang"].astype(str).str.zfill(4)
    localites = pd.DataFrame({
        "id": lsrc["id"],
        "nom": lsrc["lieu_habite"],
        "categorie": lsrc["categorie"],
        "groupement_quartier_id": lsrc["groupement_quartier_id"],
        "commune_secteur_chefferie_id": lsrc["secteur_chefferie_commune_id"],
        "village_rattachement_nom": lsrc["village_ratachement"],
        "village_rattachement_id": lsrc["village_rattachement_id"],
        "latitude": lsrc["latitude"].round(7),
        "longitude": lsrc["longitude"].round(7),
        "altitude": lsrc["altitude"].round(1),
        "precision_m": lsrc["precision"].round(3),
    })
    # Fermes : souvent la propriété d'une famille, parfois nommées d'après le propriétaire.
    # On publie leur position arrondie à 0,01° (~1 km), sans précision GPS.
    ferme = localites["categorie"] == "ferme"
    localites.loc[ferme, ["latitude", "longitude"]] = localites.loc[ferme, ["latitude", "longitude"]].round(2)
    localites.loc[ferme, "precision_m"] = pd.NA
    report["fermes_position_arrondie_1km"] = int(ferme.sum())

    report["points_sans_nom_ni_code_ignores"] = int(
        (df["village_id"].isna() & df["lieu_habite"].isna()).sum())

    # ---------- Indicateurs qualité ----------
    dup = villages.assign(_k=villages["nom"].str.upper()).groupby(
        ["groupement_quartier_id", "_k"]).size()
    report["noms_de_village_en_double_dans_un_meme_groupement"] = int((dup > 1).sum())
    report["villages_sans_groupement"] = int(villages["groupement_quartier_id"].isna().sum())
    report["localites_rattachees_a_un_village_code"] = int(localites["village_rattachement_id"].notna().sum())

    DATA.mkdir(exist_ok=True)
    tables = {
        "provinces.csv": provinces[["id", "nom"]],
        "territoires_villes.csv": tv[["id", "nom", "type", "province_id"]],
        "communes_secteurs_chefferies.csv": csc[["id", "nom", "type", "territoire_ville_id", "antenne_id", "antenne_nom"]],
        "groupements_quartiers.csv": gq[["id", "nom", "type", "commune_secteur_chefferie_id"]],
        "villages.csv": villages,
        "localites.csv": localites,
    }
    for name, t in tables.items():
        t.to_csv(DATA / name, index=False, encoding="utf-8", lineterminator="\n")
        report[f"lignes_{name}"] = len(t)

    DOCS.mkdir(exist_ok=True)
    with open(DOCS / "rapport_import.md", "w", encoding="utf-8") as f:
        f.write("# Rapport d'import\n\nGénéré par `scripts/import_excel.py`.\n\n| Indicateur | Valeur |\n|---|---:|\n")
        for k, v in report.items():
            f.write(f"| {k.replace('_', ' ')} | {v:,} |\n".replace(",", " "))
    for k, v in report.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
