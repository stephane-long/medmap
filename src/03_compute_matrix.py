import geopandas as gpd
import pandas as pd
import requests
import json
import numpy as np

# URL locale de votre serveur OSRM Docker (Port 5000)
OSRM_BASE_URL = "http://localhost:5000/table/v1/driving/"

def get_travel_time(src_lon, src_lat, dest_lons, dest_lats):
    """
    Appelle OSRM pour calculer le temps de trajet depuis un point source vers N cibles.
    OSRM `table` renvoie une matrice. On veut extraire le temps minimum parmi les cibles.
    """
    # Construire la requête: source_coord;dest_coord1;dest_coord2...
    coords_list = [f"{src_lon},{src_lat}"]
    for lon, lat in zip(dest_lons, dest_lats):
        coords_list.append(f"{lon},{lat}")
    
    coords_str = ";".join(coords_list)
    
    # sources=0 (le premier point est la source)
    # destinations=1;2;3... (le reste sont les destinations)
    dest_indices = ";".join([str(i) for i in range(1, len(coords_list))])
    url = f"{OSRM_BASE_URL}{coords_str}?sources=0&destinations={dest_indices}&annotations=duration"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # on récupère la ligne 0 des durées (depuis notre source unique 0)
            durations_seconds = data['durations'][0]
            # On ignore les valeurs nulles (trajet impossible)
            valid_durations = [d for d in durations_seconds if d is not None]
            if valid_durations:
                # Retourne le temps vers le praticien le plus proche (en minutes)
                min_seconds = min(valid_durations)
                return min_seconds / 60.0
    except Exception as e:
        print(f"Erreur requête OSRM: {e}")
        
    return None

def compute_accessibility():
    print("Chargement de la grille et des praticiens...")
    grid = gpd.read_file("data/grille_essonne.gpkg")
    
    try:
        praticiens = pd.read_csv("data/praticiens_essonne_geocoded.csv")
    except FileNotFoundError:
        print("Erreur: Le fichier des praticiens n'existe pas. Lancez d'abord 01_extract_praticiens.py")
        return

    dest_lons = praticiens['longitude'].values
    dest_lats = praticiens['latitude'].values
    
    # Pour ne pas surcharger OSRM avec des requêtes gigantesques, 
    # si vous avez beaucoup de cibles (>500), on peut filtrer par bounding box (proximité volumétrique) 
    # Mais en local, OSRM peut encaisser une matrice 1 x 500 sans broncher.
    # On va tester avec une limite si nécessaire. Pour l'instant on envoie tout si < 1000.
    
    # NOTE : La taille d'une requête URL a une limite ~8000 caractères. 
    # OSRM limite par défaut la table à 100x100.
    # Il faudra soit lancer le conteneur Docker avec `--max-table-size=1000` 
    # soit restreindre à la recherche des 90 praticiens les plus proches (vol d'oiseau) avant d'appeler OSRM.
    
    travel_times = []
    
    total = len(grid)
    for idx, row in grid.iterrows():
        if idx % 100 == 0:
            print(f"Traitement {idx}/{total}...")
            
        src_lon = row['centroid_lon']
        src_lat = row['centroid_lat']
        
        # Astuce : On ne prend que les 50 praticiens les plus proches géométriquement
        # pour éviter d'exploser l'URL.
        geom_distances = np.sqrt((dest_lons - src_lon)**2 + (dest_lats - src_lat)**2)
        closest_indices = np.argsort(geom_distances)[:50]
        
        closest_lons = dest_lons[closest_indices]
        closest_lats = dest_lats[closest_indices]
        
        t_time = get_travel_time(src_lon, src_lat, closest_lons, closest_lats)
        travel_times.append(t_time)
        
    grid['temps_trajet_min'] = travel_times
    
    out_file = "data/grille_accessibilite_finale.gpkg"
    grid.to_file(out_file, driver="GPKG")
    print(f"Calcul terminé ! Matrice sauvegardée: {out_file}")

if __name__ == "__main__":
    compute_accessibility()
