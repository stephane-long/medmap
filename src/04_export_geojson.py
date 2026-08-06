import json
import os
from collections import defaultdict

import geopandas as gpd
import pandas as pd


def _build_adresse_index():
    """Retourne un dict adresse → liste de médecins depuis le CSV geocodé."""
    df = pd.read_csv("data/generalistes_ville_creuse_geocoded.csv")
    index = defaultdict(list)
    for _, row in df.iterrows():
        adresse = row["adresse"] if pd.notna(row["adresse"]) else ""
        if not adresse:
            continue
        savoir_faire = (
            row["Libellé savoir-faire"]
            if pd.notna(row["Libellé savoir-faire"])
            else row["Libellé profession"]
            if pd.notna(row["Libellé profession"])
            else ""
        )
        index[adresse].append(
            {
                "nom": row["Nom d'exercice"] if pd.notna(row["Nom d'exercice"]) else "",
                "prenom": row["Prénom d'exercice"]
                if pd.notna(row["Prénom d'exercice"])
                else "",
                "savoir_faire": savoir_faire,
            }
        )
    return index


def export_geojson():
    print("Chargement du GeoPackage...")
    grid = gpd.read_file("data/grille_accessibilite_creuse.gpkg")

    if grid.crs and grid.crs.to_epsg() != 4326:
        print(f"Reprojection depuis EPSG:{grid.crs.to_epsg()} vers WGS84...")
        grid = grid.to_crs(epsg=4326)

    print("Construction de l'index des cabinets...")
    adresse_index = _build_adresse_index()

    def medecins_json(adresse):
        if not adresse or pd.isna(adresse):
            return "[]"
        return json.dumps(adresse_index.get(adresse, []), ensure_ascii=False)

    grid["praticien_count"] = grid["praticien_adresse"].apply(
        lambda a: len(adresse_index.get(a, [])) if pd.notna(a) and a else 0
    )
    grid["praticiens_json"] = grid["praticien_adresse"].apply(medecins_json)

    cols = [
        "h3_index",
        "temps_trajet_min",
        "praticien_adresse",
        "praticien_count",
        "praticiens_json",
        "geometry",
    ]
    grid = grid[[c for c in cols if c in grid.columns]]

    out_file = "data/grille_accessibilite_creuse.geojson"
    grid.to_file(out_file, driver="GeoJSON")

    size_mb = os.path.getsize(out_file) / (1024 * 1024)
    print(f"Export terminé : {out_file} ({size_mb:.1f} Mo)")


if __name__ == "__main__":
    export_geojson()
