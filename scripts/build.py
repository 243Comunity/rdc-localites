#!/usr/bin/env python3
"""Génère tous les formats publiés dans dist/ à partir des CSV de data/.

    python scripts/build.py

Sorties :
  dist/json/<table>.json            une liste par niveau
  dist/geojson/villages.geojson     points GPS des villages
  dist/geojson/localites.geojson    points GPS des localités
  dist/rdc-localites.sqlite         base SQLite prête à l'emploi
  dist/api/v1/...                   API statique (fichiers JSON à servir tels quels)
  dist/index.html                   page de démonstration (copiée depuis site/)

Bibliothèque standard uniquement : aucun serveur, aucune dépendance.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from collections import defaultdict
from pathlib import Path

from common import ROOT, TABLES, load_all

DIST = ROOT / "dist"
API = DIST / "api" / "v1"
VERSION = (ROOT / "VERSION").read_text().strip()


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def build_json(db):
    for t, rows in db.items():
        dump(DIST / "json" / f"{t}.json", rows)


def build_geojson(db):
    for t in ("villages", "localites"):
        feats = []
        for r in db[t]:
            if r["latitude"] is None:
                continue
            props = {k: v for k, v in r.items() if k not in ("latitude", "longitude")}
            feats.append({"type": "Feature",
                          "geometry": {"type": "Point", "coordinates": [r["longitude"], r["latitude"]]},
                          "properties": props})
        dump(DIST / "geojson" / f"{t}.geojson", {"type": "FeatureCollection", "features": feats})


SQL_TYPES = {"id": "INTEGER PRIMARY KEY"}


def build_sqlite(db):
    path = DIST / "rdc-localites.sqlite"
    path.unlink(missing_ok=True)
    con = sqlite3.connect(path)
    for t, rows in db.items():
        cols = list(rows[0].keys())
        defs = []
        for c in cols:
            if c == "id":
                defs.append("id TEXT PRIMARY KEY" if t == "localites" else "id INTEGER PRIMARY KEY")
            elif c in ("latitude", "longitude", "altitude", "precision_m"):
                defs.append(f"{c} REAL")
            elif c.endswith("_id") or c == "nb_points_gps":
                defs.append(f"{c} INTEGER")
            else:
                defs.append(f"{c} TEXT")
        con.execute(f"CREATE TABLE {t} ({', '.join(defs)})")
        con.executemany(f"INSERT INTO {t} VALUES ({','.join('?' * len(cols))})",
                        [tuple(r[c] for c in cols) for r in rows])
    for t, col in [("territoires_villes", "province_id"),
                   ("communes_secteurs_chefferies", "territoire_ville_id"),
                   ("groupements_quartiers", "commune_secteur_chefferie_id"),
                   ("villages", "groupement_quartier_id"),
                   ("localites", "groupement_quartier_id"),
                   ("localites", "commune_secteur_chefferie_id")]:
        con.execute(f"CREATE INDEX idx_{t}_{col} ON {t}({col})")
    con.execute("CREATE TABLE meta (cle TEXT PRIMARY KEY, valeur TEXT)")
    con.execute("INSERT INTO meta VALUES ('version', ?)", (VERSION,))
    con.commit()
    con.execute("VACUUM")
    con.close()


def build_api(db):
    by_id = {t: {r["id"]: r for r in rows} for t, rows in db.items()}
    children = defaultdict(lambda: defaultdict(list))
    for r in db["territoires_villes"]:
        children["provinces"][r["province_id"]].append(r)
    for r in db["communes_secteurs_chefferies"]:
        children["territoires_villes"][r["territoire_ville_id"]].append(r)
    for r in db["groupements_quartiers"]:
        children["communes_secteurs_chefferies"][r["commune_secteur_chefferie_id"]].append(r)
    for r in db["villages"]:
        children["groupements_quartiers"][r["groupement_quartier_id"]].append(r)
    loc_by_g, loc_by_c = defaultdict(list), defaultdict(list)
    for r in db["localites"]:
        if r["groupement_quartier_id"] is not None:
            loc_by_g[r["groupement_quartier_id"]].append(r)
        else:
            loc_by_c[r["commune_secteur_chefferie_id"]].append(r)

    def short(r):
        return {k: r[k] for k in ("id", "nom", "type") if k in r}

    def path_of(table, r):
        """Chemin complet depuis la province (fil d'Ariane)."""
        chain = []
        if table in ("groupements_quartiers",):
            c = by_id["communes_secteurs_chefferies"][r["commune_secteur_chefferie_id"]]
        elif table == "communes_secteurs_chefferies":
            c = r
        else:
            c = None
        if c is not None and c is not r:
            chain.insert(0, {"niveau": "commune_secteur_chefferie", **short(c)})
        tv = (by_id["territoires_villes"][c["territoire_ville_id"]] if c is not None
              else r if table == "territoires_villes" else None)
        if tv is not None and tv is not r:
            chain.insert(0, {"niveau": "territoire_ville", **short(tv)})
        p_id = tv["province_id"] if tv is not None else None
        if p_id is not None:
            chain.insert(0, {"niveau": "province", **short(by_id["provinces"][p_id])})
        return chain

    if API.exists():
        shutil.rmtree(API)

    dump(API / "index.json", {
        "nom": "RDC Localités",
        "version": VERSION,
        "niveaux": ["provinces", "territoires-villes", "communes-secteurs-chefferies",
                    "groupements-quartiers"],
        "effectifs": {t: len(rows) for t, rows in db.items()},
    })
    dump(API / "provinces.json", [short(r) for r in db["provinces"]])

    for r in db["provinces"]:
        dump(API / "provinces" / f"{r['id']}.json",
             {**r, "territoires_villes": [short(x) for x in children["provinces"][r["id"]]]})
    for r in db["territoires_villes"]:
        dump(API / "territoires-villes" / f"{r['id']}.json",
             {**r, "chemin": path_of("territoires_villes", r),
              "communes_secteurs_chefferies": [short(x) for x in children["territoires_villes"][r["id"]]]})
    for r in db["communes_secteurs_chefferies"]:
        dump(API / "communes-secteurs-chefferies" / f"{r['id']}.json",
             {**r, "chemin": path_of("communes_secteurs_chefferies", r),
              "groupements_quartiers": [short(x) for x in children["communes_secteurs_chefferies"][r["id"]]],
              "localites_sans_groupement": loc_by_c.get(r["id"], [])})
    for r in db["groupements_quartiers"]:
        dump(API / "groupements-quartiers" / f"{r['id']}.json",
             {**r, "chemin": path_of("groupements_quartiers", r),
              "villages": children["groupements_quartiers"][r["id"]],
              "localites": loc_by_g.get(r["id"], [])})


def build_site():
    """Copie la page de démonstration (site/) à la racine de dist/."""
    src = ROOT / "site"
    if src.exists():
        shutil.copytree(src, DIST, dirs_exist_ok=True)


def main():
    db = load_all()
    DIST.mkdir(exist_ok=True)
    build_json(db)
    build_geojson(db)
    build_sqlite(db)
    build_api(db)
    build_site()
    n_files = sum(1 for _ in DIST.rglob("*") if _.is_file())
    print(f"dist/ généré : {n_files} fichiers (version {VERSION}).")


if __name__ == "__main__":
    main()
