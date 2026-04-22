
# Projet DataViz : Accessibilité Médicale en Essonne

## Concept
Carte interactive montrant le temps de trajet théorique vers le praticien le plus proche.

## Stack Technique
- **Data :** Python (GeoPandas, OSRM)
- **Backend :** Synology DS224+ (Docker, PostGIS, Martin Tile Server)
- **Frontend :** MapLibre GL JS, Svelte/Tailwind
- **Hébergement Frontend :** OVH (fichiers statiques)
- **Hébergement Backend :** Synology DS224+ sécurisé et exposé via Cloudflare Tunnels

## Roadmap
1. **Extraction & Calcul** : Matrice de temps de trajet par spécialité.
2. **Infrastructure** : Setup Docker sur le NAS (PostGIS + Martin).
3. **Frontend** : Développement de la carte et du filtrage dynamique.
4. **Publication** : Déploiement OVH (Front) et configuration de route API via Cloudflare Tunnels.
