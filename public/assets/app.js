'use strict';

const STATE = {
  B: { name: 'Baden', adj: 'badisch', long: 'Republik Baden', color: '--B' },
  W: { name: 'Württemberg', adj: 'württembergisch', long: 'Volksstaat Württemberg', color: '--W' },
  H: { name: 'Hohenzollern', adj: 'hohenzollerisch', long: 'Hohenzollerische Lande (Preußen)', color: '--H' },
  X: { name: 'Hessen', adj: 'hessisch', long: 'Volksstaat Hessen', color: '--X' },
};
const TYPE = ['Stadt', 'Stadt', 'Dorf', 'Stadtteil', 'Ortsteil', 'Weiler'];
const API = 'api/api.php';

const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const fmt = (n) => n.toLocaleString('de-DE');

function norm(s) {
  return s.toLowerCase()
    .replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss')
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/\bst\.\s*/g, 'sankt ')
    .replace(/[^a-z0-9]+/g, ' ').trim();
}

let DB = null;      // { places: [...], gemeinden, kreise1945 }
let byOsm = new Map();
let map, borderLayer, tileLayer, marker;
let current = null;

/* ---------- Theme ---------- */
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem('theme', theme); } catch (e) { /* private mode */ }
  if (map) setTiles();
  if (borderLayer) borderLayer.setStyle(borderStyle);
}
$('#themeToggle').addEventListener('click', () => {
  applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
});
try { const t = localStorage.getItem('theme'); if (t) document.documentElement.dataset.theme = t; } catch (e) { /* ignore */ }

/* ---------- Data ---------- */
async function loadData() {
  const [places, borders, stats] = await Promise.all([
    fetch('data/places.json').then((r) => r.json()),
    fetch('data/borders.json').then((r) => r.json()),
    fetch('data/stats.json').then((r) => r.json()),
  ]);
  DB = places;
  DB.items = places.places.map((p) => {
    const g = p[5] >= 0 ? places.gemeinden[p[5]] : null;
    const item = {
      name: p[0], type: p[1], lat: p[2], lon: p[3], state: p[4], gem: g, flag: p[6], osm: p[7],
      k45: p[8] >= 0 ? places.kreise1945[p[8]] : null,
    };
    item.key = norm(item.name);
    byOsm.set(String(item.osm), item);
    return item;
  });
  renderStats(stats);
  initMap(borders);
  route();
}

/* ---------- Search ---------- */
const input = $('#q');
const list = $('#suggestions');
let hits = [];
let active = -1;

function search(q) {
  const n = norm(q);
  if (n.length < 2) return [];
  const res = [];
  for (const it of DB.items) {
    let score;
    if (it.key === n) score = 0;
    else if (it.key.startsWith(n)) score = 1;
    else if (it.key.includes(' ' + n)) score = 2;
    else if (n.length >= 3 && it.key.includes(n)) score = 3;
    else continue;
    res.push([score * 10 + it.type, it]);
  }
  res.sort((a, b) => a[0] - b[0] || a[1].name.localeCompare(b[1].name, 'de'));
  return res.slice(0, 12).map((r) => r[1]);
}

function context(it) {
  const parts = [];
  if (it.gem && it.gem.name !== it.name) parts.push(`${TYPE[it.type]} von ${it.gem.name}`);
  else parts.push(TYPE[it.type]);
  if (it.gem && it.gem.kreis && it.gem.kreis !== it.gem.name) parts.push(it.gem.kreis);
  return parts.join(' · ');
}

function renderSuggestions() {
  active = -1;
  if (!input.value.trim()) { list.hidden = true; return; }
  if (!hits.length) {
    list.innerHTML = '<li class="s-empty">Kein Ort gefunden – prüf die Schreibweise oder versuch den heutigen Gemeindenamen.</li>';
  } else {
    list.innerHTML = hits.map((it, i) => `
      <li role="option" id="opt${i}" data-i="${i}" aria-selected="false">
        <span class="dot dot--${it.state}" title="${STATE[it.state].name}"></span>
        <span><span class="s-name">${esc(it.name)}</span><br /><span class="s-meta">${esc(context(it))} · ${STATE[it.state].name}</span></span>
      </li>`).join('');
  }
  list.hidden = false;
  input.parentElement.setAttribute('aria-expanded', 'true');
}

function closeSuggestions() {
  list.hidden = true;
  input.parentElement.setAttribute('aria-expanded', 'false');
}

function setActive(i) {
  const opts = list.querySelectorAll('[role=option]');
  if (!opts.length) return;
  active = (i + opts.length) % opts.length;
  opts.forEach((o, j) => o.setAttribute('aria-selected', j === active ? 'true' : 'false'));
  opts[active].scrollIntoView({ block: 'nearest' });
  input.setAttribute('aria-activedescendant', opts[active].id);
}

input.addEventListener('input', () => {
  if (!DB) return;
  hits = search(input.value);
  renderSuggestions();
});
input.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowDown') { e.preventDefault(); setActive(active + 1); }
  else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(active - 1); }
  else if (e.key === 'Enter') {
    e.preventDefault();
    const it = hits[active >= 0 ? active : 0];
    if (it) choose(it);
  } else if (e.key === 'Escape') closeSuggestions();
});
list.addEventListener('mousedown', (e) => {
  const li = e.target.closest('[data-i]');
  if (li) { e.preventDefault(); choose(hits[+li.dataset.i]); }
});
input.addEventListener('blur', () => setTimeout(closeSuggestions, 120));
document.querySelectorAll('[data-try]').forEach((b) => b.addEventListener('click', () => {
  input.value = b.dataset.try;
  hits = search(input.value);
  if (hits[0]) choose(hits[0]);
}));

function slug(s) { return norm(s).replace(/ /g, '-'); }
function choose(it) {
  closeSuggestions();
  input.value = it.name;
  location.hash = `ort/${it.osm}-${slug(it.name)}`;
}

/* ---------- Routing ---------- */
function route() {
  const m = location.hash.match(/^#ort\/(\d+)/);
  if (!m || !DB) return;
  const it = byOsm.get(m[1]);
  if (it) showResult(it);
}
window.addEventListener('hashchange', route);

/* ---------- Result ---------- */
function mixedParts(it) {
  if (!it.gem || Object.keys(it.gem.shares).length < 2) return null;
  const groups = {};
  for (const p of DB.items) {
    if (p.gem !== it.gem || p.type > 4 || p.name === it.gem.name) continue;
    (groups[p.state] ||= []).push(p);
  }
  return groups;
}

const isMixedTown = (it) => it.gem && it.gem.name === it.name && it.type <= 1 && Object.keys(it.gem.shares).length > 1;

function verdictText(it) {
  const s = STATE[it.state];
  if (isMixedTown(it)) {
    const names = Object.keys(it.gem.shares).map((k) => `<strong style="color:var(${STATE[k].color})">${STATE[k].adj}</strong>`);
    return `Teils, teils: ${names.slice(0, -1).join(', ')} und ${names.at(-1)}.`;
  }
  switch (it.state) {
    case 'B': return `Lag vor 1945 in <strong>Baden</strong>.`;
    case 'W': return `Lag vor 1945 in <strong>Württemberg</strong>.`;
    case 'H': return `Weder noch: <strong>Hohenzollern</strong> – bis 1945 preußisch!`;
    case 'X': return `Überraschung: Das war <strong>Hessen</strong>!`;
    default: return s.name;
  }
}

function shareBar(shares) {
  return `<div class="share-bar" aria-hidden="true">${Object.entries(shares)
    .map(([k, v]) => `<span style="width:${v * 100}%;background:var(${STATE[k].color})"></span>`).join('')}</div>`;
}

function showResult(it) {
  current = it;
  const wrap = $('#ergebnis');
  const el = $('#result');
  el.replaceChildren($('#tplResult').content.cloneNode(true));
  el.dataset.state = it.state;
  $('.result__kicker', el).textContent = context(it);
  $('.result__title', el).textContent = it.name;
  $('.result__verdict', el).innerHTML = verdictText(it);
  document.title = `${it.name}: ${STATE[it.state].adj} – Baden oder Württemberg?`;

  const notes = [];
  if (it.flag === 1) notes.push(`<div class="note note--warn"><strong>Grenzlage:</strong> ${esc(it.name)} liegt sehr nah an der alten Landesgrenze (unter 250&nbsp;m). Die Zuordnung ist wahrscheinlich, aber nicht ganz sicher – Ortskundige bitte prüfen!</div>`);
  if (it.flag === 2) notes.push(`<div class="note note--warn"><strong>Quellen widersprechen sich:</strong> Laut Gemeindeverzeichnis 1945 gehört ein Ort dieses Namens zum ${esc(it.k45[0])} (${STATE[it.k45[1]].name}). Vermutlich eine Namensdoppelung – Hinweise willkommen.</div>`);
  if (it.state === 'H') notes.push(`<div class="note">Die Fürstentümer Hohenzollern-Hechingen und -Sigmaringen kamen 1850 an Preußen. Bis 1945 waren die „Hohenzollerischen Lande“ ein preußischer Regierungsbezirk mit Sitz in Sigmaringen.</div>`);
  if (it.state === 'X') notes.push(`<div class="note">Wimpfen war bis 1945 eine Exklave des Volksstaats Hessen mitten zwischen Baden und Württemberg. Erst nach dem Krieg kam es zu Württemberg-Baden, endgültig 1952 zu Baden-Württemberg.</div>`);
  if (it.gem && Object.keys(it.gem.shares).length > 1) {
    const parts = Object.entries(it.gem.shares).map(([k, v]) => `${Math.round(v * 100)}&nbsp;% ${STATE[k].name}`).join(', ');
    const groups = mixedParts(it);
    const lines = Object.keys(it.gem.shares).filter((k) => groups[k]).map((k) => `<div><b style="color:var(${STATE[k].color})">${STATE[k].name}:</b> ${groups[k]
      .sort((a, b) => a.type - b.type || a.name.localeCompare(b.name, 'de')).slice(0, 25)
      .map((p) => `<a href="#ort/${p.osm}-${slug(p.name)}">${esc(p.name)}</a>`).join(', ')}${groups[k].length > 25 ? ' …' : ''}</div>`).join('');
    notes.push(`<div class="note"><strong>Gemischte Gemeinde:</strong> Die heutige Gemeinde ${esc(it.gem.name)} umfasst Gebiete aus mehreren alten Ländern (${parts} der Fläche).${shareBar(it.gem.shares)}<div class="parts">${lines}</div></div>`);
  }
  $('.result__notes', el).innerHTML = notes.join('');

  const facts = [
    ['Damals', isMixedTown(it)
      ? Object.keys(it.gem.shares).map((k) => STATE[k].long).join(' / ') + `<br /><small>Ortskern: ${STATE[it.state].name}</small>`
      : STATE[it.state].long],
    ['Kreis 1945', it.k45 && it.k45[1] === it.state
      ? `<a href="${esc(it.k45[2])}" target="_blank" rel="noopener">${esc(it.k45[0])}</a>` : '–'],
    ['Heute', it.gem ? esc(it.gem.name) + (it.gem.kreis && it.gem.kreis !== it.gem.name ? `, ${esc(it.gem.kreis)}` : '') : '–'],
    ['Koordinaten', `<a href="https://www.openstreetmap.org/node/${it.osm}" target="_blank" rel="noopener">${it.lat.toFixed(4)}, ${it.lon.toFixed(4)}</a>`],
  ];
  $('.result__facts', el).innerHTML = facts.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('');
  $('.stories__place', el).textContent = it.name;

  el.addEventListener('click', onResultClick);
  setupForm($('.form--feedback', el), 'feedback');
  setupForm($('.form--story', el), 'story');
  loadStories(it);

  wrap.hidden = false;
  wrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (map) {
    if (marker) marker.remove();
    marker = L.circleMarker([it.lat, it.lon], {
      radius: 9, weight: 3, color: cssVar('--text'), fillColor: cssVar(STATE[it.state].color), fillOpacity: 1,
    }).addTo(map).bindPopup(`<strong>${esc(it.name)}</strong><br />${STATE[it.state].name}`);
    map.setView([it.lat, it.lon], 11);
  }
}

function onResultClick(e) {
  const act = e.target.closest('[data-act]')?.dataset.act;
  if (!act) return;
  const el = $('#result');
  if (act === 'share') {
    const url = location.href;
    const text = `${current.name} war ${STATE[current.state].adj}!`;
    if (navigator.share) navigator.share({ title: 'Baden oder Württemberg?', text, url }).catch(() => {});
    else navigator.clipboard?.writeText(url).then(() => { e.target.textContent = 'Link kopiert ✓'; });
  } else if (act === 'feedback') {
    const f = $('.form--feedback', el);
    f.hidden = !f.hidden;
    if (!f.hidden) f.querySelector('textarea').focus();
  } else if (act === 'story') {
    const f = $('.form--story', el);
    f.hidden = !f.hidden;
    if (!f.hidden) f.querySelector('textarea').focus();
  }
}

/* ---------- Stories ---------- */
async function loadStories(it) {
  const ul = $('#result .stories__list');
  try {
    const r = await fetch(`${API}?a=stories&place=${it.osm}`);
    if (!r.ok) throw new Error(r.status);
    const data = await r.json();
    if (current !== it) return;
    if (!data.stories.length) {
      ul.innerHTML = `<li class="stories__empty">Noch keine Geschichten zu ${esc(it.name)}. Erzähl die erste!</li>`;
      return;
    }
    ul.innerHTML = data.stories.map(renderStory).join('');
  } catch (e) {
    ul.innerHTML = '<li class="stories__empty">Geschichten konnten gerade nicht geladen werden.</li>';
  }
}

function renderStory(s) {
  const date = new Date(s.created * 1000).toLocaleDateString('de-DE', { day: 'numeric', month: 'long', year: 'numeric' });
  return `<li class="story"><p>${esc(s.body)}</p><footer>— ${esc(s.author || 'anonym')}, ${date}</footer></li>`;
}

/* ---------- Captcha (Proof of Work, ALTCHA-artig) ---------- */
async function sha256hex(str) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

async function solve(ch) {
  for (let n = 0; n <= ch.maxnumber; n++) {
    if (await sha256hex(ch.salt + n) === ch.challenge) return n;
  }
  throw new Error('unsolvable');
}

function setupCaptcha(box) {
  const id = 'cap' + Math.random().toString(36).slice(2);
  box.innerHTML = `<input type="checkbox" id="${id}" /><label for="${id}">Ich bin kein Roboter<small>Kurze Rechenaufgabe im Browser, ohne Cookies</small></label>`;
  box.payload = null;
  const cb = box.querySelector('input');
  cb.addEventListener('change', async () => {
    if (!cb.checked || box.payload) return;
    cb.hidden = true;
    const spin = document.createElement('span');
    spin.className = 'spin';
    box.prepend(spin);
    box.querySelector('small').textContent = 'Wird geprüft …';
    try {
      const ch = await fetch(`${API}?a=captcha`).then((r) => r.json());
      const number = await solve(ch);
      box.payload = btoa(JSON.stringify({ algorithm: ch.algorithm, challenge: ch.challenge, number, salt: ch.salt, signature: ch.signature }));
      box.classList.add('done');
      box.querySelector('small').textContent = 'Bestätigt ✓';
    } catch (e) {
      cb.checked = false;
      box.querySelector('small').textContent = 'Fehlgeschlagen – bitte nochmal versuchen.';
    } finally {
      spin.remove();
      cb.hidden = false;
    }
  });
}

function setupForm(form, kind) {
  const box = $('.captcha', form);
  setupCaptcha(box);
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const status = $('.form__status', form);
    const btn = $('button[type=submit]', form);
    if (!box.payload) {
      status.className = 'form__status err';
      status.textContent = 'Bitte bestätige zuerst „Ich bin kein Roboter“.';
      return;
    }
    const body = Object.fromEntries(new FormData(form));
    Object.assign(body, {
      a: kind, captcha: box.payload, place: current.osm, placeName: current.name, state: current.state,
    });
    btn.disabled = true;
    status.className = 'form__status';
    status.textContent = 'Wird gesendet …';
    try {
      const r = await fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.error || 'Senden fehlgeschlagen.');
      status.className = 'form__status ok';
      if (kind === 'story') {
        status.textContent = 'Danke! Deine Geschichte ist veröffentlicht.';
        const ul = $('#result .stories__list');
        $('.stories__empty', ul)?.remove();
        ul.insertAdjacentHTML('afterbegin', renderStory(data.story));
      } else {
        status.textContent = 'Danke! Wir schauen uns das an.';
      }
      form.reset();
      setupCaptcha(box);
    } catch (err) {
      status.className = 'form__status err';
      status.textContent = err.message;
      setupCaptcha(box);
    } finally {
      btn.disabled = false;
    }
  });
}

/* ---------- Map ---------- */
function borderStyle(f) {
  return { color: cssVar(STATE[f.properties.code].color), weight: 1.5, fillColor: cssVar(STATE[f.properties.code].color), fillOpacity: 0.22 };
}

function setTiles() {
  if (tileLayer) tileLayer.remove();
  tileLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>-Mitwirkende · Grenzen 1939: <a href="https://www.openhistoricalmap.org/">OpenHistoricalMap</a>',
    maxZoom: 18,
  }).addTo(map);
  tileLayer.bringToBack();
}

function initMap(borders) {
  map = L.map('map', { scrollWheelZoom: false, zoomSnap: 0.5 }).setView([48.65, 9.0], 7.5);
  setTiles();
  borderLayer = L.geoJSON(borders, { style: borderStyle, interactive: false }).addTo(map);
  map.fitBounds(borderLayer.getBounds(), { padding: [10, 10] });
  map.on('focus', () => map.scrollWheelZoom.enable());
  map.on('blur', () => map.scrollWheelZoom.disable());
  map.on('click', (e) => {
    const it = nearest(e.latlng.lat, e.latlng.lng);
    if (!it) return;
    L.popup().setLatLng(e.latlng).setContent(
      `<strong>${esc(it.name)}</strong> (${STATE[it.state].name})<br /><a href="#ort/${it.osm}-${slug(it.name)}">Details ansehen</a>`,
    ).openOn(map);
  });
}

function nearest(lat, lon) {
  let best = null;
  let bd = Infinity;
  const k = Math.cos((lat * Math.PI) / 180);
  for (const it of DB.items) {
    if (it.type > 3) continue;
    const d = (it.lat - lat) ** 2 + ((it.lon - lon) * k) ** 2;
    if (d < bd) { bd = d; best = it; }
  }
  return bd < 0.0004 ? best : null; // ~2 km
}

/* ---------- Stats ---------- */
function renderStats(s) {
  $('#heroStats').textContent = `${fmt(s.places)} Orte · ${fmt(s.gemeinden)} heutige Gemeinden · ${s.mixedGemeinden} davon mit Gebieten aus mehreren alten Ländern`;
  const tiles = ['B', 'W', 'H', 'X'].map((k) => `<div class="stat" style="--c:var(${STATE[k].color})"><b>${fmt(s.byState[k] || 0)}</b><span>Orte in ${STATE[k].name}</span></div>`);
  tiles.push(`<div class="stat" style="--c:var(--accent)"><b>${s.mixedGemeinden}</b><span>heutige Gemeinden mit badischen <em>und</em> württembergischen (oder hohenzollerischen) Teilen</span></div>`);
  $('#stats').innerHTML = tiles.join('');
  const v = s.validation;
  $('#validationText').textContent = `Von ${fmt(v.compared)} Gemeinden, die sich eindeutig zuordnen ließen, stimmen ${fmt(v.agree)} (${(v.agree / v.compared * 100).toFixed(1).replace('.', ',')} %) mit der Karte überein.`;
}

/* ---------- Privacy toggle ---------- */
$('#privacyLink').addEventListener('click', (e) => {
  e.preventDefault();
  const p = $('#datenschutz');
  p.hidden = !p.hidden;
  if (!p.hidden) p.scrollIntoView({ behavior: 'smooth' });
});

loadData().catch((e) => {
  console.error(e);
  $('#heroStats').textContent = 'Die Ortsdaten konnten nicht geladen werden. Bitte Seite neu laden.';
});
