import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import './style.css';

const GEOJSON_URL      = '/grille_accessibilite.geojson';
const PRATICIENS_URL   = '/praticiens.geojson';
const MAP_STYLE        = 'https://tiles.openfreemap.org/styles/bright';
const GEOCODE_URL      = 'https://api-adresse.data.gouv.fr/search/';

const map = new maplibregl.Map({
  container: 'map',
  style: MAP_STYLE,
  center: [1.87, 46.17],
  zoom: 9,
});

map.addControl(new maplibregl.NavigationControl(), 'top-right');
map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-right');

// ---------------------------------------------------------------------------
// Couche hexagones
// ---------------------------------------------------------------------------
map.on('load', async () => {
  const [hexData, pratData] = await Promise.all([
    fetch(GEOJSON_URL).then((r) => r.json()),
    fetch(PRATICIENS_URL).then((r) => r.json()),
  ]);

  // --- Hexagones ---
  map.addSource('hexagones', { type: 'geojson', data: hexData });

  map.addLayer({
    id: 'hexagones-fill',
    type: 'fill',
    source: 'hexagones',
    paint: {
      'fill-color': [
        'case',
        ['==', ['get', 'temps_trajet_min'], null],
        '#aaaaaa',
        [
          'interpolate', ['linear'], ['get', 'temps_trajet_min'],
          0,  '#1a9641',
          5, '#a6d96a',
          10, '#ffffbf',
          20, '#fdae61',
          30, '#d7191c',
        ],
      ],
      'fill-opacity': 0.75,
    },
  });

  map.addLayer({
    id: 'hexagones-outline',
    type: 'line',
    source: 'hexagones',
    paint: {
      'line-color': '#ffffff',
      'line-width': 0.5,
      'line-opacity': 0.4,
    },
  });

  // --- Praticiens ---
  map.addSource('praticiens', { type: 'geojson', data: pratData });

  map.addLayer({
    id: 'praticiens-circle',
    type: 'circle',
    source: 'praticiens',
    paint: {
      'circle-radius': [
        'interpolate', ['linear'], ['get', 'count'],
        1, 5,
        3, 8,
        6, 11,
        10, 14,
      ],
      'circle-color': '#2563eb',
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': 1.5,
      'circle-opacity': 0.9,
    },
  });

  initPopups();
  initFilter();
  initTogglePraticiens();
});

// ---------------------------------------------------------------------------
// Popups (handler unique avec priorité praticien > hexagone)
// ---------------------------------------------------------------------------
function initPopups() {
  const popup = new maplibregl.Popup({ closeButton: true, maxWidth: '280px' });

  // En mobile le popup est rendu en feuille basse : il occuperait la même place
  // que le panneau de contrôle, qu'on escamote donc le temps de la consultation.
  popup.on('open',  () => document.body.classList.add('popup-open'));
  popup.on('close', () => document.body.classList.remove('popup-open'));

  map.on('click', (e) => {
    // Priorité 1 : praticien (couche supérieure)
    const pratFeatures = map.queryRenderedFeatures(e.point, { layers: ['praticiens-circle'] });
    if (pratFeatures.length) {
      const p = pratFeatures[0].properties;
      const medecins = JSON.parse(p.medecins);
      const badge = medecins.length > 1 ? `${medecins.length} médecins` : 'Médecin';
      const items = medecins.map((m) => `
        <div class="popup-medecin-item">
          <div class="popup-name">${m.prenom} ${m.nom}</div>
          <div class="popup-detail">${m.savoir_faire}</div>
        </div>
      `).join('<hr class="popup-divider">');

      collapseSheet();
      popup
        .setLngLat(pratFeatures[0].geometry.coordinates)
        .setHTML(`
          <div class="popup-medecin">
            <span class="popup-badge">${badge}</span>
            <div class="popup-medecin-list">${items}</div>
            <div class="popup-detail popup-adresse">${p.adresse ?? ''}</div>
          </div>
        `)
        .addTo(map);
      return;
    }

    // Priorité 2 : hexagone
    const hexFeatures = map.queryRenderedFeatures(e.point, { layers: ['hexagones-fill'] });
    if (hexFeatures.length) {
      const p = hexFeatures[0].properties;
      const temps = p.temps_trajet_min != null
        ? `${Math.round(p.temps_trajet_min)} min en voiture`
        : 'Injoignable';

      const medecins = JSON.parse(p.praticiens_json || '[]');
      const badge = medecins.length > 1 ? `pour rejoindre les ${medecins.length} médecins les plus proches` : 'pour rejoindre le médecin le plus proche';
      const items = medecins.map((m) => `
        <div class="popup-medecin-item">
          <div class="popup-name">${m.prenom} ${m.nom}</div>
          <div class="popup-detail">${m.savoir_faire}</div>
        </div>
      `).join('<hr class="popup-divider">');

      collapseSheet();
      popup
        .setLngLat(e.lngLat)
        .setHTML(`
          <div class="popup-content">
            <div class="popup-time">${temps}</div>
            <span class="popup-badge">${badge}</span>
            <div class="popup-medecin-list">${items}</div>
            <div class="popup-detail popup-adresse">${p.praticien_adresse ?? ''}</div>
          </div>
        `)
        .addTo(map);
    }
  });

  map.on('mouseenter', 'praticiens-circle', () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', 'praticiens-circle', () => { map.getCanvas().style.cursor = ''; });
  map.on('mouseenter', 'hexagones-fill',   () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', 'hexagones-fill',   () => { map.getCanvas().style.cursor = ''; });
}

// ---------------------------------------------------------------------------
// Toggle visibilité des praticiens
// ---------------------------------------------------------------------------
function initTogglePraticiens() {
  const toggle = document.getElementById('toggle-praticiens');
  toggle.addEventListener('change', () => {
    const visibility = toggle.checked ? 'visible' : 'none';
    map.setLayoutProperty('praticiens-circle', 'visibility', visibility);
  });
}

// ---------------------------------------------------------------------------
// Filtre slider
// ---------------------------------------------------------------------------
function initFilter() {
  const slider = document.getElementById('filter-slider');
  const label  = document.getElementById('filter-value');

  slider.addEventListener('input', () => {
    const seuil = parseInt(slider.value);
    label.textContent = seuil === 0 ? 'Toutes' : `> ${seuil} min`;

    const filter = seuil === 0 ? null : ['>', ['get', 'temps_trajet_min'], seuil];
    map.setFilter('hexagones-fill', filter);
    map.setFilter('hexagones-outline', filter);
  });
}

// ---------------------------------------------------------------------------
// Recherche de commune
// ---------------------------------------------------------------------------
const searchInput   = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');
let searchTimer;

searchInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  const q = searchInput.value.trim();
  if (q.length < 2) { hide(); return; }
  searchTimer = setTimeout(() => fetchCommunes(q), 300);
});

async function fetchCommunes(q) {
  try {
    const url = `${GEOCODE_URL}?q=${encodeURIComponent(q)}&type=municipality&limit=6`;
    const res  = await fetch(url);
    const json = await res.json();
    renderResults(json.features ?? []);
  } catch { hide(); }
}

function renderResults(features) {
  searchResults.innerHTML = '';
  if (!features.length) { hide(); return; }

  searchResults.classList.remove('hidden');
  features.forEach((f) => {
    const li = document.createElement('li');
    li.textContent = `${f.properties.city} (${f.properties.postcode})`;
    li.addEventListener('click', () => {
      // En mobile, on décale le centrage pour que la commune ne finisse pas
      // sous le sheet (bas) ou sous la barre de recherche (haut).
      const padding = isMobile() ? { top: 70, bottom: 140, left: 0, right: 0 } : undefined;
      map.flyTo({ center: f.geometry.coordinates, zoom: 13, padding });
      searchInput.value = li.textContent;
      searchInput.blur();
      hide();
    });
    searchResults.appendChild(li);
  });
}

function hide() { searchResults.classList.add('hidden'); }

document.addEventListener('click', (e) => {
  if (!e.target.closest('#search-wrapper')) hide();
});

// ---------------------------------------------------------------------------
// Mobile — barre de recherche en haut, panneau de contrôle en bottom sheet
// ---------------------------------------------------------------------------
const MOBILE_QUERY = '(max-width: 768px)';
const mqMobile     = window.matchMedia(MOBILE_QUERY);
const isMobile     = () => mqMobile.matches;

const topbar        = document.getElementById('mobile-topbar');
const controlPanel  = document.getElementById('control-panel');
const searchWrapper = document.getElementById('search-wrapper');
const searchDivider = document.getElementById('search-divider');
const sheetHandle   = document.getElementById('sheet-handle');
const titlePanel    = document.getElementById('title-panel');
const infoBackdrop  = document.getElementById('info-backdrop');

/**
 * Le champ de recherche est en bas du panneau sur desktop, mais doit passer
 * en haut de l'écran sur mobile — sinon le clavier virtuel le recouvre.
 * On déplace le nœud plutôt que de dupliquer le markup ; ça n'arrive qu'au
 * franchissement du breakpoint (rotation, redimensionnement).
 */
function syncSearchPlacement() {
  if (isMobile()) {
    if (searchWrapper.parentElement !== topbar) topbar.insertBefore(searchWrapper, topbar.firstChild);
  } else if (searchWrapper.parentElement !== controlPanel) {
    controlPanel.insertBefore(searchWrapper, searchDivider);
  }
}

function setSheetExpanded(expanded) {
  controlPanel.classList.toggle('is-expanded', expanded);
  sheetHandle.setAttribute('aria-expanded', String(expanded));
  sheetHandle.setAttribute('aria-label', expanded ? 'Replier les filtres' : 'Déplier les filtres');
}

function collapseSheet() {
  if (isMobile()) setSheetExpanded(false);
}

function initSheet() {
  sheetHandle.addEventListener('click', () => {
    setSheetExpanded(!controlPanel.classList.contains('is-expanded'));
  });

  // Drag vertical sur la poignée : au-delà de 30px, on déplie/replie.
  let startY = null;
  sheetHandle.addEventListener('pointerdown', (e) => { startY = e.clientY; });
  sheetHandle.addEventListener('pointermove', (e) => {
    if (startY === null) return;
    const delta = e.clientY - startY;
    if (Math.abs(delta) < 30) return;
    setSheetExpanded(delta < 0);
    startY = null;
  });
  const endDrag = () => { startY = null; };
  sheetHandle.addEventListener('pointerup', endDrag);
  sheetHandle.addEventListener('pointercancel', endDrag);
}

function initInfoPanel() {
  const open  = () => { titlePanel.classList.add('is-open');   infoBackdrop.classList.add('is-open'); };
  const close = () => { titlePanel.classList.remove('is-open'); infoBackdrop.classList.remove('is-open'); };

  document.getElementById('info-btn').addEventListener('click', open);
  document.getElementById('info-close').addEventListener('click', close);
  infoBackdrop.addEventListener('click', close);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });

  // Repasser en desktop doit rendre le panneau à son état normal
  mqMobile.addEventListener('change', close);
}

syncSearchPlacement();
mqMobile.addEventListener('change', syncSearchPlacement);
initSheet();
initInfoPanel();
