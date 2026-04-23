import os

import geopandas as gpd
import pandas as pd
import requests
import numpy as np

OSRM_BASE_URL = "http://localhost:5000/table/v1/driving/"
CHECKPOINT_FILE = "data/checkpoint_matrix.csv"


def get_travel_time(src_lon, src_lat, dest_lons, dest_lats):
    """
    Appelle OSRM pour calculer le temps de trajet depuis un point source vers N cibles.
    Retourne (temps_min_en_minutes, index_local_du_praticien_le_plus_proche).
    L'index local correspond à la position dans dest_lons/dest_lats (pas dans le CSV global).
    """
    coords_list = [f"{src_lon},{src_lat}"]
    for lon, lat in zip(dest_lons, dest_lats):
        coords_list.append(f"{lon},{lat}")

    coords_str = ";".join(coords_list)
    dest_indices = ";".join([str(i) for i in range(1, len(coords_list))])
    url = f"{OSRM_BASE_URL}{coords_str}?sources=0&destinations={dest_indices}&annotations=duration"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            durations_seconds = data["durations"][0]
            valid = [(i, d) for i, d in enumerate(durations_seconds) if d is not None]
            if valid:
                local_idx, min_seconds = min(valid, key=lambda x: x[1])
                return min_seconds / 60.0, local_idx
    except Exception as e:
        print(f"Erreur requête OSRM: {e}")

    return None, None


def _save_checkpoint(done):
    rows = [{"h3_index": h, "temps_trajet_min": v["temps_trajet_min"], "praticien_idx": v["praticien_idx"]} for h, v in done.items()]
    pd.DataFrame(rows).to_csv(CHECKPOINT_FILE, index=False)


def compute_accessibility():
    print("Chargement de la grille et des praticiens...")
    grid = gpd.read_file("data/grille_essonne.gpkg")

    try:
        praticiens = pd.read_csv("data/generalistes_ville_idf_geocoded.csv", sep=",")
    except FileNotFoundError:
        print(
            "Erreur: Le fichier des praticiens n'existe pas. Lancez d'abord 01_extract_praticiens.py"
        )
        return

    dest_lons = praticiens["longitude"].to_numpy(dtype=float)
    dest_lats = praticiens["latitude"].to_numpy(dtype=float)

    # Pour ne pas surcharger OSRM avec des requêtes gigantesques,
    # si vous avez beaucoup de cibles (>500), on peut filtrer par bounding box (proximité volumétrique)
    # Mais en local, OSRM peut encaisser une matrice 1 x 500 sans broncher.

    # NOTE : La taille d'une requête URL a une limite ~8000 caractères.
    # OSRM limite par défaut la table à 100x100.
    # Il faudra soit lancer le conteneur Docker avec `--max-table-size=1000`
    # soit restreindre à la recherche des 50 praticiens les plus proches (vol d'oiseau) avant d'appeler OSRM.

    # Reprise depuis checkpoint si disponible
    done = {}
    if os.path.exists(CHECKPOINT_FILE):
        df_ckpt = pd.read_csv(CHECKPOINT_FILE)
        for _, row in df_ckpt.iterrows():
            done[row["h3_index"]] = {
                "temps_trajet_min": row["temps_trajet_min"] if pd.notna(row["temps_trajet_min"]) else None,
                "praticien_idx": int(row["praticien_idx"]) if pd.notna(row["praticien_idx"]) else None,
            }
        print(f"Checkpoint détecté : {len(done)} hexagones déjà calculés.")

    total = len(grid)
    print(f"{total} hexagones à traiter.")
    src_lons = grid["centroid_lon"].to_numpy(dtype=float)
    src_lats = grid["centroid_lat"].to_numpy(dtype=float)
    h3_indices = grid["h3_index"].tolist()

    computed = 0

    for idx, (h3_idx, src_lon, src_lat) in enumerate(
        zip(h3_indices, src_lons, src_lats)
    ):
        if h3_idx in done:
            continue

        if computed % 100 == 0:
            print(f"Traitement {idx}/{total} ({computed} nouveaux)...")

        geom_distances = np.sqrt(
            (dest_lons - src_lon) ** 2 + (dest_lats - src_lat) ** 2
        )
        closest_indices = np.argpartition(geom_distances, 50)[:50]

        t_time, local_idx = get_travel_time(
            src_lon, src_lat, dest_lons[closest_indices], dest_lats[closest_indices]
        )
        original_idx = int(closest_indices[local_idx]) if local_idx is not None else None
        done[h3_idx] = {"temps_trajet_min": t_time, "praticien_idx": original_idx}
        computed += 1

        if computed % 100 == 0:
            _save_checkpoint(done)
            print(f"Checkpoint sauvegardé ({len(done)}/{total}).")

    # Sauvegarde finale
    _save_checkpoint(done)
    grid["temps_trajet_min"] = grid["h3_index"].map(lambda h: done.get(h, {}).get("temps_trajet_min"))

    # Enrichissement avec les infos du praticien le plus proche
    praticien_idx_series = grid["h3_index"].map(lambda h: done.get(h, {}).get("praticien_idx"))
    cols = {
        "praticien_nom": "Nom d'exercice",
        "praticien_prenom": "Prénom d'exercice",
        "praticien_savoir_faire": "Libellé savoir-faire",
        "praticien_adresse": "adresse",
    }
    for col_out, col_in in cols.items():
        grid[col_out] = praticien_idx_series.apply(
            lambda i: praticiens.iloc[int(i)][col_in] if pd.notna(i) else None
        )

    out_file = "data/grille_accessibilite_finale.gpkg"
    grid.to_file(out_file, driver="GPKG")
    print(f"Calcul terminé ! Matrice sauvegardée: {out_file}")
    os.remove(CHECKPOINT_FILE)
    print("Checkpoint supprimé.")


if __name__ == "__main__":
    compute_accessibility()
