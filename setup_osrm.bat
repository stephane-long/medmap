@echo off
echo ========================================================
echo Preparation de la carte Ile-de-France pour OSRM via Docker
echo ========================================================

echo 1. Extraction du graphe routier...
docker run -t -v "%cd%\data:/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /opt/car.lua /data/ile-de-france-latest.osm.pbf

echo 2. Partitionnement du graphe...
docker run -t -v "%cd%\data:/data" ghcr.io/project-osrm/osrm-backend osrm-partition /data/ile-de-france-latest.osrm

echo 3. Personnalisation des poids...
docker run -t -v "%cd%\data:/data" ghcr.io/project-osrm/osrm-backend osrm-customize /data/ile-de-france-latest.osrm

echo ========================================================
echo Lancement de l'API OSRM en arriere-plan (Port 5000)...
echo ========================================================
docker run -d --name osrm-idf -p 5000:5000 -v "%cd%\data:/data" ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld /data/ile-de-france-latest.osrm

echo Termine ! OSRM est accessible sur http://localhost:5000
pause
