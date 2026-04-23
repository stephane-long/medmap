import json
from collections import defaultdict

import pandas as pd


def export_praticiens():
    print("Chargement des praticiens...")
    df = pd.read_csv("data/generalistes_ville_idf_geocoded.csv")

    # Restreindre à l'Essonne (91)
    df = df[df["Code postal (coord. structure)"].astype(str).str.startswith("91")]
    df = df.dropna(subset=["longitude", "latitude"])

    # Regrouper par coordonnées (un cabinet = un point, même si plusieurs médecins)
    groups = defaultdict(lambda: {"adresse": "", "medecins": []})
    for _, row in df.iterrows():
        key = (round(float(row["longitude"]), 6), round(float(row["latitude"]), 6))
        if not groups[key]["adresse"]:
            groups[key]["adresse"] = row["adresse"] if pd.notna(row["adresse"]) else ""
        savoir_faire = (
            row["Libellé savoir-faire"] if pd.notna(row["Libellé savoir-faire"])
            else row["Libellé profession"] if pd.notna(row["Libellé profession"])
            else ""
        )
        groups[key]["medecins"].append({
            "nom":         row["Nom d'exercice"]    if pd.notna(row["Nom d'exercice"])    else "",
            "prenom":      row["Prénom d'exercice"] if pd.notna(row["Prénom d'exercice"]) else "",
            "savoir_faire": savoir_faire,
        })

    features = []
    for (lon, lat), data in groups.items():
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "adresse":  data["adresse"],
                "count":    len(data["medecins"]),
                "medecins": json.dumps(data["medecins"], ensure_ascii=False),
            },
        })

    geojson = {"type": "FeatureCollection", "features": features}

    out_file = "data/praticiens.geojson"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)

    nb_cabinets = len(features)
    nb_medecins = sum(len(g["medecins"]) for g in groups.values())
    print(f"Export terminé : {out_file} ({nb_medecins} médecins · {nb_cabinets} cabinets)")


if __name__ == "__main__":
    export_praticiens()
