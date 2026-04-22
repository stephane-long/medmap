import json
import os
import time

import pandas as pd
import requests


def geocode_adresse(adresse_complete):
    """Géocode une adresse en utilisant l'API d'adresse du gouvernement avec gestion des pannes."""
    base_url = "https://api-adresse.data.gouv.fr/search/"
    params = {"q": adresse_complete, "limit": 1}

    # On fait 3 tentatives si le réseau coupe
    for attempt in range(3):
        try:
            response = requests.get(base_url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data["features"]:
                    coords = data["features"][0]["geometry"]["coordinates"]
                    return coords[0], coords[1]  # lon, lat
            return None, None  # Si code n'est pas 200 ou pas de résultat, on passe
        except Exception as e:
            print(f"Tentative {attempt + 1}/3 échouée pour {adresse_complete} : {e}")
            time.sleep(2)  # On attend 2 secondes avant de retenter

    return None, None


def process_praticiens(file_path):
    out_file = "data/generalistes_ville_idf_geocoded.csv"

    # Charger la base brute
    df = pd.read_csv(file_path, sep=",", encoding="utf-8")

    # Si un fichier partiel existe déjà, on le charge pour reprendre !
    if os.path.exists(out_file):
        print(f"Fichier partiel détecté ({out_file}). Reprise de la progression...")
        df_geocoded = pd.read_csv(out_file, sep=",", encoding="utf-8")
        # Fusionner pour récupérer les longitudes/latitudes déjà trouvées
        # On suppose que 'adresse' est la clé unique
        df = df.merge(
            df_geocoded[["adresse", "longitude", "latitude"]], on="adresse", how="left"
        )
    else:
        df["longitude"] = None
        df["latitude"] = None

    total = len(df)
    missing = df["longitude"].isna().sum()
    print(
        f"Praticiens totaux: {total} | Déjà géocodés: {total - missing} | Restants: {missing}"
    )

    count = 0
    for idx, row in df.iterrows():
        # On ne traite que ceux qui n'ont pas encore de coordonnées
        if pd.isna(row["longitude"]):
            lon, lat = geocode_adresse(row["adresse"])
            df.at[idx, "longitude"] = lon
            df.at[idx, "latitude"] = lat
            count += 1
            time.sleep(0.05)

            # Sauvegarder tous les 100 succès pour éviter de tout perdre
            if count % 100 == 0:
                print(f"Sauvegarde intermédiaire... ({count} nouveaux géocodages)")
                df.to_csv(out_file, index=False)

    # Nettoyage final
    df_clean = df.dropna(subset=["longitude", "latitude"])
    df_clean.to_csv(out_file, index=False)
    print(
        f"Sauvegarde FINALE terminée : {out_file} ({len(df_clean)} enregistrements complets)"
    )


if __name__ == "__main__":
    process_praticiens("data/generalistes_ville_idf.csv")
