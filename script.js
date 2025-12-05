const map = L.map('map', {
  zoomControl: true,
  scrollWheelZoom: true,
}).setView([48.6616, 9.3501], 8);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>-Mitwirkende',
  maxZoom: 18,
}).addTo(map);

const markers = L.layerGroup().addTo(map);
const searchInput = document.getElementById('searchInput');
const clearSearchBtn = document.getElementById('clearSearch');
const listContainer = document.getElementById('placeList');
let allPlaces = [];

function badgeColor(region) {
  switch (region) {
    case 'Baden':
      return '#ff9f43';
    case 'Württemberg':
      return '#4dd0e1';
    default:
      return '#e95fa0';
  }
}

function renderList(places) {
  listContainer.innerHTML = '';
  if (!places.length) {
    listContainer.innerHTML = '<p>Keine Orte gefunden. Prüfe Schreibweise oder füge weitere Daten hinzu.</p>';
    return;
  }

  places.forEach((place) => {
    const item = document.createElement('article');
    item.className = 'list__item';
    item.setAttribute('role', 'listitem');

    const heading = document.createElement('h3');
    heading.textContent = place.name;

    const meta = document.createElement('div');
    meta.className = 'list__meta';
    meta.innerHTML = `
      <span class="tag ${regionClass(place.region)}">${place.region}</span>
      <a class="list__source" href="${place.sourceUrl}" target="_blank" rel="noreferrer">Quelle: ${place.sourceName}</a>
    `;

    const notes = document.createElement('p');
    notes.className = 'list__meta';
    notes.textContent = place.notes;

    item.appendChild(heading);
    item.appendChild(meta);
    item.appendChild(notes);

    item.addEventListener('click', () => focusMarker(place));

    listContainer.appendChild(item);
  });
}

function regionClass(region) {
  if (region === 'Baden') return 'tag--baden';
  if (region === 'Württemberg') return 'tag--wuerttemberg';
  return 'tag--mixed';
}

function renderMarkers(places) {
  markers.clearLayers();

  places.forEach((place) => {
    const marker = L.circleMarker([place.lat, place.lon], {
      radius: 8,
      fillColor: badgeColor(place.region),
      fillOpacity: 0.9,
      color: '#0b1d2c',
      weight: 2,
    }).addTo(markers);

    marker.bindPopup(`
      <strong>${place.name}</strong><br/>
      Landesteil: ${place.region}<br/>
      <em>${place.notes}</em><br/>
      <a href="${place.sourceUrl}" target="_blank" rel="noreferrer">Quelle: ${place.sourceName}</a>
    `);

    marker.on('click', () => {
      marker.openPopup();
    });

    place._marker = marker;
  });
}

function focusMarker(place) {
  if (!place?._marker) return;
  place._marker.openPopup();
  map.setView([place.lat, place.lon], 11, { animate: true });
}

function filterPlaces(term) {
  const query = term.trim().toLowerCase();
  if (!query) return allPlaces;
  return allPlaces.filter((p) =>
    [p.name, p.region, p.notes, p.sourceName].some((field) => field.toLowerCase().includes(query))
  );
}

async function loadData() {
  try {
    const response = await fetch('data/places.json');
    allPlaces = await response.json();
    renderList(allPlaces);
    renderMarkers(allPlaces);
  } catch (error) {
    console.error('Daten konnten nicht geladen werden', error);
    listContainer.innerHTML = '<p>Fehler beim Laden der Daten. Prüfe den Pfad data/places.json.</p>';
  }
}

searchInput.addEventListener('input', (event) => {
  const filtered = filterPlaces(event.target.value);
  renderList(filtered);
  renderMarkers(filtered);
});

clearSearchBtn.addEventListener('click', () => {
  searchInput.value = '';
  renderList(allPlaces);
  renderMarkers(allPlaces);
  searchInput.focus();
});

loadData();
