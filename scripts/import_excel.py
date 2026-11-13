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

MOIS = ["JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET",
        "AOÛT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE"]

# Noms abîmés dans la source par des erreurs d'encodage (« OÃ¿CHA »). Corrections relues
# une par une. « probable » = lettre déduite du contexte, à confirmer sur le terrain.
CORRECTIONS = {
    ("communes_secteurs_chefferies", 613411): "OÏCHA",
    ("communes_secteurs_chefferies", 803407): "BATETELA ARABISÉS-LOMAMI",
    ("villages", 2003067): "EMMAÜS",
    ("villages", 2019946): "KIKUPÎKA MAKABA I",
    ("villages", 2023218): "ÎLE LIMBILA",
    ("villages", 2025869): "PANDU COTON ZAÏRE",
    ("villages", 2025978): "MONO MAÏGO",            # probable
    ("villages", 2094797): "VILLAGE DE NGBOL'UWA",
    ("villages", 2060581): "TANGA / 6° ESCAL",
    ("villages", 2053285): "KYUBO KABANGO / KYUBO MAMBA",
    ("villages", 2079349): "YENGALA PLANTATION",
    ("villages", 2012766): "POSTE KIPWANGA",        # probable
    ("villages", 2026791): "MBWA PONT",             # probable
    ("villages", 2062191): "KALUNGU",
}

# Une lettre a été perdue dans la source et ne peut pas être devinée : on retire le
# caractère abîmé et on liste l'entité dans docs/A_VERIFIER.md.
A_VERIFIER = {
    ("groupements_quartiers", 1006901): "V KOJAMWENE",
    ("villages", 2008734): "KAZMBA",
    ("villages", 2035412): "TSHIAMNDU",
    ("villages", 2038764): "KABA",
    ("villages", 2046075): "BENA KAPTA KAFIKA",
    ("villages", 2046791): "KIALU SANT",
    ("villages", 2047668): "MB LUMBA",
    ("villages", 2047669): "KIAMBE MB",
    ("villages", 2075540): "NGANG",
    ("villages", 2075549): "DJA",
    ("villages", 2075565): "GO",
    ("villages", 2080735): "LAMBA",
    ("villages", 2080744): "MIBLA",
    ("villages", 2080831): "ELMBE II",
    ("villages", 2081421): "BUZIND",
    ("villages", 2094872): "BNA KASUAYA",
}

# Fiches que les agents ont eux-mêmes marquées comme erronées.
SUPPRIMER_SI_NOM_CONTIENT = ["FORMULAIRE A SUPPRIMER"]


def clean_name(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value)
    # Excel a transformé des noms comme « 30 JUIN » en dates (2024-06-30 00:00:00)
    m = re.fullmatch(r"\d{4}-(\d\d)-(\d\d)( 00:00:00)?", s.strip())
    if m:
        s = f"{int(m.group(2))} {MOIS[int(m.group(1)) - 1]}"
    s = s.replace('"', "'")  # N"JILI -> N'JILI : l'apostrophe a été remplacée par un guillemet
    s = s.replace("\u2019", "'").replace("\u2018", "'")  # apostrophes typographiques
    s = s.replace("_", " ")  # BOMA_VILLE -> BOMA VILLE
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

    # ---------- Corrections de noms ----------
    frames = {"communes_secteurs_chefferies": csc, "groupements_quartiers": gq,
              "villages": villages, "localites": localites}
    raw_names = {}
    for (table, ident), nom in {**CORRECTIONS, **A_VERIFIER}.items():
        t = frames[table]
        hit = t["id"] == ident
        if hit.sum() != 1:
            raise SystemExit(f"Correction introuvable : {table} {ident}")
        raw_names[(table, ident)] = t.loc[hit, "nom"].iloc[0]
        t.loc[hit, "nom"] = nom
    # Le nom du village de rattachement des localités suit la correction du village
    fix_village = {raw_names[k]: v for k, v in {**CORRECTIONS, **A_VERIFIER}.items() if k[0] == "villages"}
    localites["village_rattachement_nom"] = localites["village_rattachement_nom"].replace(fix_village)
    report["noms_corriges_encodage"] = len(CORRECTIONS)
    report["noms_a_verifier_lettre_perdue"] = len(A_VERIFIER)

    drop = localites["nom"].str.upper().str.contains("|".join(SUPPRIMER_SI_NOM_CONTIENT), regex=True)
    report["fiches_marquees_erronees_supprimees"] = int(drop.sum())
    localites = localites[~drop]

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
    with open(DOCS / "A_VERIFIER.md", "w", encoding="utf-8") as f:
        f.write("# Noms à vérifier sur le terrain\n\n"
                "Dans le fichier source, une lettre de ces noms a été abîmée par une erreur d'encodage "
                "et ne peut pas être retrouvée. Le caractère abîmé a été retiré. Si vous connaissez "
                "le bon nom, ouvrez un ticket « Correction de données ».\n\n"
                "| Fichier | Identifiant | Nom publié | Valeur brute dans la source | Lieu |\n|---|---|---|---|---|\n")
        names = {t: frames[t].set_index("id") for t in frames}
        for (table, ident), nom in A_VERIFIER.items():
            row = names[table].loc[ident]
            c_id = ident if table == "communes_secteurs_chefferies" else row["commune_secteur_chefferie_id"]
            c = csc.set_index("id").loc[c_id]
            t_ = tv.set_index("id").loc[c["territoire_ville_id"]]
            p_ = provinces.set_index("id").loc[t_["province_id"]]
            lieu = f"{p_['nom']} / {t_['nom']} / {c['nom']}"
            raw = raw_names[(table, ident)].replace("|", "\\|")
            f.write(f"| {table}.csv | {ident} | {nom} | `{raw}` | {lieu} |\n")
        f.write("\nCorrigés avec une lettre **probable** (à confirmer) : "
                + ", ".join(f"{v} ({k[1]})" for k, v in CORRECTIONS.items()
                            if k[1] in (2025978, 2012766, 2026791)) + ".\n")
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
