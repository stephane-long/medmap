## 1 préparation du fichier de médecins (.csv)
Utiliser le script **import_praticiens.ipynb**.
Sélection des colonnes inutiles, suppression des lignes sans adresse, filtrage des médecins sur la zone souhaitée.

## 2 Géocodage de l'adresse des médecins en utilisant l'API gouvernementale
Utiliser le script **01_extract_praticiens.py**
Fichier d'entrée : data/generalistes_ville_creuse.csv
Fichier de sortie : data/generalistes_ville_creuse_geocoded.csv

<u>Remarque</u> : le fichier d'entrée/sortie est en dur dans le script (bloc `if __name__`). Pour changer de département, il faut éditer directement `process_praticiens("data/generalistes_ville_<zone>.csv")` et le nom du `out_file`.

Reprend depuis le dernier checkpoint si le fichier de sortie existe déjà (sauvegarde tous les 100 géocodages réussis, 3 tentatives avec délai de 2s par adresse en cas d'échec réseau).

## 3 Création de la géométrie (polygone) de la zone observée (ex : Essonne, Creuse)
Utilisation de l'API geo.api.gouv.fr : téléchargement des contours de toutes les communes sur la zone au format GeoJSON. Lecture des données avec geoPandas qui sait lire un GeoJSON directement depuis une URL. Création du polygone regroupant toutes les communes.
On génère une grille d'hexagones H3 dans ce polygone de résolution 8 ou 9.

Utilisation des librairies Python GeoPandas et h3.
Utilisation du script **02_generate_grid.py**

On recrée un dataframe GeoPandas à partir des hexagones H3 (une ligne = un héxagone H3).
Grille stockée dans data/grille_creuse.gpkg (résolution 8 utilisée pour la Creuse, soit ~0,7 km²/hexagone).

<u>Remarque</u> : comme pour l'étape 2, le code du département (`23`) et le nom du fichier de sortie sont en dur dans `get_area_boundary()` et le bloc `if __name__` — à éditer pour changer de zone.

## 4 Calcul des temps de trajet
Prérequis : installer le moteur de routage OSRM dans un container Docker en local (port 5000). Une image officielle est dispo.

On charge la grille et les données des praticiens.
On prépare le serveur OSRM avec l'extrait OSM de la Creuse (`creuse-latest.osm.pbf`).

**Lancer setup_osrm_creuse.bat** pour télécharger les données sur OpenStreetMap et installer l'image Docker en local (port 5000). Le script télécharge `creuse-latest.osm.pbf` depuis download.openstreetmap.fr, puis enchaîne `osrm-extract` → `osrm-partition` → `osrm-customize` avant de lancer le conteneur `osrm-creuse`.

<u>Remarque</u> : si un ancien conteneur OSRM (ex. `osrm-idf`) tourne encore sur le port 5000, il faut le stopper (`docker stop osrm-idf && docker rm osrm-idf`) avant de relancer le script, sinon le port est déjà occupé.

Calculer les temps de trajet (après installation de OSRM sur localhost:5000)
**python src/03_compute_matrix.py**
Entrée : grille_creuse.gpkg + praticiens geocodés
Sortie  : data/grille_accessibilite_creuse.gpkg

Pour chaque cellule h3 on extrait les 50 praticiens les plus proches, puis on calcule le temps de trajet pour chaque praticien avec le serveur OSRM afin de déterminer le plus proche.

### Ce que contient le fichier geopackage (gpkg) 
Une couche géométrique avec les hexagones de la grille H3.
Pour chaque hexagone, des attributs supplémentaires :
h3_index : identifiant de l’hexagone
centroid_lon : longitude du centre
centroid_lat : latitude du centre
temps_trajet_min : temps de trajet minimum vers le praticien le plus proche
praticien_nom : nom du praticien retenu
praticien_prenom : prénom du praticien
praticien_savoir_faire : spécialité/savoir-faire
praticien_adresse : adresse du praticien
geometry : la géométrie de l’hexagone

## 5 Préparation du fichier GeoJSON pour le Web
Charge grille_accessibilite_creuse.gpkg.
Le script **04_export_geojson.py** transforme la grille d’accessibilité géographique en un fichier GeoJSON prêt à être utilisé dans une carte web. Son rôle principal est d’exporter les données déjà calculées sous un format plus simple à consommer côté frontend.
Le résultat est un GeoJSON enrichi pour l’affichage cartographique, avec les informations de praticiens liées à chaque cellule.

## 6 Préparation du fichier des praticiens
Le script **05_export_praticiens.py** sert à créer un fichier GeoJSON de points représentant les cabinets/praticiens, en regroupant ceux qui partagent la même position.

<u>Remarque</u> : le filtre de zone (`Code postal (coord. structure)` commençant par `23` pour la Creuse) est en dur ligne 12 — à adapter en cas de changement de département.

## 7 Déploiement
Il faut builder le code Web avec Vite (`npm run build` dans `client/`, génère `client/dist/`) puis uploader le contenu du dossier `dist/` sur l'espace d'hébergement (OVH).

Avant le build, copier les fichiers de données générés dans `client/public/` (Vite les inclut tels quels dans `dist/`) :

data/praticiens.geojson ->  client/public/praticiens.geojson
data/grille_accessibilite_creuse.geojson -> client/public/grille_accessibilite.geojson

## 8 Fonctionnement du site Web (frontend)

Site statique dans `client/`, sans backend : les GeoJSON produits par le pipeline Python (étapes 4-5) sont chargés côté navigateur avec `fetch()`.

`npm run dev` sert les fichiers source avec rechargement à chaud pour développer ; `npm run build` bundle/minifie tout dans `client/dist/`, prêt à héberger tel quel (voir étape 7). Le dossier `client/public/` n'est pas transformé, juste copié — c'est là qu'atterrissent les GeoJSON.

MapLibre GL JS s'occupe de tout ce qui est géospatial :
- charge un fond de carte vectoriel externe et gratuit (`tiles.openfreemap.org`)
- affiche la grille H3 et les praticiens comme des **sources GeoJSON** + des **layers** (`fill`/`line` pour les hexagones, `circle` pour les praticiens)
- colore/dimensionne les éléments via des **expressions déclaratives** (`interpolate`, `case`) plutôt qu'en JS manuel — ex. dégradé de couleur selon `temps_trajet_min`
- fournit les popups au clic (`maplibregl.Popup`) et les contrôles zoom/échelle prêts à l'emploi

**JS natif du navigateur** : gère tout ce qui n'est pas la carte elle-même — le slider de filtre (`map.setFilter`), la case à cocher (`map.setLayoutProperty` pour la visibilité), et la recherche de commune (`fetch` vers `api-adresse.data.gouv.fr` avec un debounce de 300ms, puis `map.flyTo()` vers le résultat choisi).

En résumé : MapLibre s'occupe du rendu géospatial, le JS natif gère l'UI autour (panneaux, recherche, filtre), Vite empaquette le tout pour la mise en prod.

## 9 Points de vigilance en cas de changement de zone

Certains éléments restent codés en dur et ne sont **pas** mis à jour automatiquement par le pipeline Python — à vérifier manuellement à chaque changement de département :

- `client/index.html` : titre de la page (`<title>`) et texte "Couverture actuelle : ..." dans le panneau — mentionnent encore l'Essonne.
- `client/src/main.js` : centre de la carte au chargement (`center: [2.44, 48.58]`, coordonnées Essonne) — à recentrer sur la nouvelle zone.
- `client/src/main.js` : `GEOJSON_URL` pointe vers `/grille_accessibilite.geojson` — cohérent avec le renommage fait à la copie (étape 7), mais à garder synchronisé si le nom de fichier change.
- Scripts `01_extract_praticiens.py`, `02_generate_grid.py`, `05_export_praticiens.py` : chemins de fichiers et filtres géographiques (code département) en dur, sans argument en ligne de commande — voir remarques aux étapes 2, 3 et 6.

---

## Glossaire des technologies

> **GeoJSON** — Format standard (RFC 7946) pour encoder des structures géographiques (points, lignes, polygones) en JSON, avec leurs propriétés attachées. Directement consommable par les librairies cartographiques web (MapLibre, Leaflet, deck.gl...) sans transformation.

> **GeoPandas** — Extension de la librairie Python pandas pour manipuler des données géospatiales : ajoute un type de colonne `geometry` (points, polygones...) et des opérations géographiques (reprojection, dissolve/fusion, lecture/écriture de GeoJSON, Shapefile, GeoPackage...) directement sur des DataFrames. Utilisée dans le projet pour fusionner les contours de communes en un polygone départemental, construire la grille H3, et lire/écrire les fichiers `.gpkg`.

> **H3** — Système d'indexation spatiale développé par Uber, qui découpe la surface du globe en une grille de cellules hexagonales imbriquées à différentes résolutions. Sert à indexer et agréger efficacement de gros volumes de données géolocalisées. kepler.gl (aussi issu d'Uber) a un support natif pour visualiser des grilles H3.

> **OpenStreetMap (.osm.pbf)** — Base de données géographique collaborative et libre (contributions citoyennes, cadastre, imagerie...), contenant tous les objets géographiques d'une zone : routes, bâtiments, cours d'eau, POI, etc. Distribuée par extraits régionaux/départementaux au format binaire compressé `.pbf` (Protocol Buffer), qui sert de matière première à OSRM.

> **OSRM (Open Source Routing Machine)** — Moteur de calcul d'itinéraires open source, écrit en C++, conçu pour calculer trajets et distances sur de très grands réseaux routiers avec une latence très faible (quelques millisecondes par requête, même à l'échelle d'un continent). S'appuie sur les données OpenStreetMap comme source du réseau routier — gratuit et personnalisable, contrairement aux API propriétaires (Google Directions, Mapbox Directions, qui utilise d'ailleurs OSRM en interne). Prend en entrée un graphe routier (nœuds = intersections, arêtes = tronçons avec vitesse limite, sens unique, type de voie...) et répond à des questions du type "chemin le plus rapide entre A et B ?" ou "temps de trajet entre 1 point et N points ?".

> **MapLibre GL JS** — Librairie de rendu cartographique en WebGL (fork open-source de Mapbox GL JS), utilisée pour afficher fonds de carte vectoriels, couches de données (GeoJSON), styles data-driven et interactions (popups, contrôles zoom/échelle) directement dans le navigateur.

> **Vite** — Outil de build JavaScript (pas un framework). Sert les fichiers source avec rechargement à chaud en développement, puis bundle/minifie le tout pour la production en un dossier statique prêt à héberger.

> **WGS84** — Système géodésique standard (le même que le GPS) utilisé pour exprimer des positions en coordonnées géographiques (longitude, latitude) en degrés décimaux. C'est le système utilisé par GeoJSON, MapLibre (`center: [longitude, latitude]`) et les API de géocodage du projet — à ne pas confondre avec l'ordre "latitude, longitude" utilisé par d'autres outils (Google Maps, etc.).
