import json

import geopandas as gpd
import h3
import requests
from shapely.geometry import Point, Polygon


def get_essonne_boundary():
    """Récupère le polygone du département de l'Essonne (91) en fusionnant ses communes."""
    print("Téléchargement des frontières de l'Essonne...")
    # L'API ne renvoie pas le contour au niveau département, mais elle le fait au niveau commune !
    # On télécharge donc toutes les communes du 91 au format GeoJSON avec leurs contours.
    url = "https://geo.api.gouv.fr/departements/91/communes?format=geojson&geometry=contour"

    # GeoPandas sait lire un GeoJSON directement depuis une URL
    gdf_communes = gpd.read_file(url)

    # On fusionne (dissolve) toutes les communes pour obtenir un seul gros polygone (le département)
    # On crée une fausse colonne pour que dissolve() rassemble tout en une seule ligne
    gdf_communes["dep"] = "91"
    gdf_essonne = gdf_communes.dissolve(by="dep")

    return gdf_essonne


def fill_with_h3(gdf_boundary, resolution=8):
    """
    Remplit le polygone donné avec des hexagones H3 à la résolution indiquée.
    """
    print(f"Génération de la grille H3 (Résolution {resolution})...")

    # 1. Obtenir les coordonnées géographiques du polygone extérieur
    boundary_geom = gdf_boundary.geometry.iloc[0]

    if boundary_geom.geom_type == "Polygon":
        polygons = [boundary_geom]
    else:  # MultiPolygon
        polygons = list(boundary_geom.geoms)

    hexagons = set()
    for poly in polygons:
        # H3 demande le format [lat, lon] pour ses fonctions de base
        exterior_coords = [(lat, lon) for lon, lat in poly.exterior.coords]

        geo_polygon = h3.LatLngPoly(exterior_coords)
        hexs = h3.polygon_to_cells(geo_polygon, resolution)
        hexagons.update(hexs)

    print(f"{len(hexagons)} hexagones générés.")

    # Créer le DataFrame final avec la géométrie (polygone) et le point central (centroïde)
    rows = []
    for h in hexagons:
        # Récupérer les frontières de l'hexagone pour dessiner le polygone
        try:
            bounds = h3.cell_to_boundary(h)  # v4
            center = h3.cell_to_latlng(h)
        except AttributeError:
            bounds = h3.h3_to_geo_boundary(h)  # v3
            center = h3.h3_to_geo(h)

        # Inverser lat/lon pour Shapely (lon, lat)
        poly = Polygon([(lon, lat) for lat, lon in bounds])
        point = Point(center[1], center[0])

        rows.append(
            {
                "h3_index": h,
                "geometry": poly,
                "centroid_lon": center[1],
                "centroid_lat": center[0],
            }
        )

    grid_gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    return grid_gdf


if __name__ == "__main__":
    boundary = get_essonne_boundary()
    # Résolution 8 = hexagones d'environ 0.7 km2 de surface, soit des milliers de points pour le 91
    # Résolution 9 = hexagones d'environ 0.1 km2
    grid = fill_with_h3(boundary, resolution=9)

    out_file = "data/grille_essonne.gpkg"
    grid.to_file(out_file, driver="GPKG")
    print(f"Grille sauvegardée dans {out_file}")
