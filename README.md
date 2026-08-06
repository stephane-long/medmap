# MedMap

Cartographie de l'accessibilité aux médecins généralistes dans la **Creuse (23)**. Le projet calcule, pour chaque hexagone d'une grille H3 couvrant le département, le temps de trajet en voiture jusqu'au généraliste le plus proche, et restitue le résultat sur une carte interactive — un outil de visualisation de la désertification médicale.

Développé initialement sur l'Essonne (91), puis migré vers la Creuse.

## Aperçu du fonctionnement

1. Un pipeline **Python** géocode les praticiens, génère une grille hexagonale H3 sur le département, puis calcule les temps de trajet via un serveur de routage **OSRM** local.
2. Le résultat est exporté en **GeoJSON**.
3. Un frontend **Vite + MapLibre GL JS** (site statique, sans backend) affiche la carte interactive.

Pour le détail pas-à-pas de chaque étape (avec remarques et pièges connus), voir **[`process.md`](process.md)** — qui contient aussi un glossaire des technologies utilisées (GeoJSON, H3, OSRM, GeoPandas, MapLibre GL JS, Vite, WGS84...).

## Structure du repo

```
src/                          # Pipeline de traitement des données (Python)
├── 01_extract_praticiens.py  # Géocodage des adresses (api-adresse.data.gouv.fr)
├── 02_generate_grid.py       # Grille H3 sur le département (geo.api.gouv.fr)
├── 03_compute_matrix.py      # Calcul des temps de trajet (OSRM)
├── 04_export_geojson.py      # Export de la grille d'accessibilité en GeoJSON
├── 05_export_praticiens.py   # Export des cabinets/praticiens en GeoJSON
└── import_praticiens.py      # Exploration/parsing des données brutes

client/                       # Frontend statique (Vite + MapLibre GL JS)
├── index.html
├── src/                      # main.js (carte, couches, interactions), style.css
└── public/                   # GeoJSON générés + assets statiques

data/                         # Données (ignoré par Git, sauf CSV sources)
import_praticiens.ipynb       # Notebook d'exploration/préparation des données brutes
setup_osrm_creuse.bat         # Setup Docker OSRM — Creuse
process.md                    # Notes détaillées de workflow + glossaire technique
```

## Prérequis

- **Python 3** avec un environnement virtuel (`.venv/`)
- **Node.js** + npm (pour le frontend)
- **Docker Desktop** (pour le serveur de routage OSRM)

### Dépendances Python

```bash
pip install -r requirements.txt
```

Pour ouvrir `import_praticiens.ipynb` (étape 1, préparation du CSV brut), Jupyter n'est pas inclus dans `requirements.txt` — installer séparément si besoin (`pip install jupyterlab` ou via l'extension Jupyter de votre IDE).

## Mise en route

### 1. Pipeline de données

```bash
# Activer le venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac

# Géocoder les praticiens
python src/01_extract_praticiens.py

# Générer la grille H3 sur la Creuse
python src/02_generate_grid.py

# Démarrer OSRM (Docker) — nécessaire avant l'étape suivante
./setup_osrm_creuse.bat

# Calculer les temps de trajet
python src/03_compute_matrix.py

# Exporter les GeoJSON pour le frontend
python src/04_export_geojson.py
python src/05_export_praticiens.py
```

Copier ensuite les GeoJSON générés (`data/praticiens.geojson`, `data/grille_accessibilite_creuse.geojson`) dans `client/public/` (voir `process.md` pour le détail des noms de fichiers attendus).

### 2. Frontend

```bash
cd client
npm install
npm run dev       # serveur de dev, http://localhost:5173
```

`npm run build` génère un site statique dans `client/dist/`, prêt à héberger (déploiement actuel : hébergement mutualisé OVH).

## Changer de département

Les chemins de fichiers et filtres géographiques (code département) sont codés en dur dans les scripts — voir la section *Points de vigilance* de `process.md` pour la liste exhaustive des endroits à adapter (scripts `01`, `02`, `05`, ainsi que `client/index.html` et `client/src/main.js`).

## Infrastructure cible (non encore implémentée)

Backend PostGIS + Martin Tile Server sur NAS Synology, reverse proxy Cloudflare Tunnels. Le frontend actuel (GeoJSON statique) est une première itération volontairement simple.
