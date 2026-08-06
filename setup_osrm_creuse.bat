@echo off
echo ========================================================
echo Preparation de la carte Creuse pour OSRM via Docker
echo ========================================================

if not exist "data\creuse-latest.osm.pbf" (
    echo 0. Telechargement de l'extrait OSM Creuse...
    curl -L -o "data\creuse-latest.osm.pbf" "https://download.openstreetmap.fr/extracts/europe/france/limousin/creuse-latest.osm.pbf"
) else (
    echo 0. Extrait OSM Creuse deja present, telechargement ignore.
)

echo Nettoyage d'un eventuel ancien conteneur osrm-creuse...
docker stop osrm-creuse >nul 2>&1
docker rm osrm-creuse >nul 2>&1

echo 1. Extraction du graphe routier...
docker run -t -v "%cd%\data:/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /opt/car.lua /data/creuse-latest.osm.pbf

echo 2. Partitionnement du graphe...
docker run -t -v "%cd%\data:/data" ghcr.io/project-osrm/osrm-backend osrm-partition /data/creuse-latest.osrm

echo 3. Personnalisation des poids...
docker run -t -v "%cd%\data:/data" ghcr.io/project-osrm/osrm-backend osrm-customize /data/creuse-latest.osrm

echo ========================================================
echo Lancement de l'API OSRM en arriere-plan (Port 5000)...
echo ========================================================
docker run -d --name osrm-creuse -p 5000:5000 -v "%cd%\data:/data" ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld /data/creuse-latest.osrm

echo Termine ! OSRM est accessible sur http://localhost:5000
pause
