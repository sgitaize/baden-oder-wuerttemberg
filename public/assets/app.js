'use strict';

const STATE = {
  B: { name: 'Baden', adj: 'badisch', long: 'Republik Baden', color: '--B', hatch: 45 },
  W: { name: 'Württemberg', adj: 'württembergisch', long: 'Volksstaat Württemberg', color: '--W', hatch: -45 },
  H: { name: 'Hohenzollern', adj: 'hohenzollerisch', long: 'Hohenzollerische Lande (Preußen)', color: '--H', hatch: 0 },
  X: { name: 'Hessen', adj: 'hessisch', long: 'Volksstaat Hessen', color: '--X', hatch: 90 },
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
const slug = (s) => norm(s).replace(/ /g, '-');

let DB = null;
const byOsm = new Map();
let map, borderLayer, marker;
let current = null;

/* ---------- Theme ---------- */
function setThemeLabel() {
  $('#themeToggle').textContent = document.documentElement.dataset.theme === 'dark' ? 'Tag' : 'Nacht';
}
$('#themeToggle').addEventListener('click', () => {
  const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem('theme', theme); } catch (e) { /* private mode */ }
  setThemeLabel();
  if (borderLayer) { updatePatterns(); borderLayer.setStyle(borderStyle); }
});
try { const t = localStorage.getItem('theme'); if (t) document.documentElement.dataset.theme = t; } catch (e) { /* ignore */ }
setThemeLabel();

/* ---------- Data ---------- */
async function loadData() {
  const [places, borders, stats] = await Promise.all([
    fetch('data/places.json').then((r) => r.json()),
    fetch('data/borders.json').then((r) => r.json()),
    fetch('data/stats.json').then((r) => r.json()),
  ]);
  DB = places;
  DB.items = places.places.map((p) => {
    const item = {
      name: p[0], type: p[1], lat: p[2], lon: p[3], state: p[4],
      gem: p[5] >= 0 ? places.gemeinden[p[5]] : null, flag: p[6], osm: p[7],
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

/* ---------- Search on the sign ---------- */
const input = $('#q');
const list = $('#suggestions');
const sign = $('#sign');
const signSub = $('#signSub');
const SIGN_DEFAULT = signSub.textContent;
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
  return parts.join(', ');
}

function renderSuggestions() {
  active = -1;
  if (!input.value.trim()) { closeSuggestions(); return; }
  list.innerHTML = hits.length
    ? hits.map((it, i) => `
      <li role="option" id="opt${i}" data-i="${i}" aria-selected="false">
        <span class="s-name">${esc(it.name)}</span>
        <span class="s-state" style="--c:var(${STATE[it.state].color})">${STATE[it.state].name}</span>
        <span class="s-meta">${esc(context(it))}</span>
      </li>`).join('')
    : '<li class="s-empty">Kein Ort gefunden. Vielleicht unter dem heutigen Gemeindenamen?</li>';
  list.hidden = false;
  input.setAttribute('aria-expanded', 'true');
}

function closeSuggestions() {
  list.hidden = true;
  input.setAttribute('aria-expanded', 'false');
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
  signSub.textContent = SIGN_DEFAULT;
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
  hits = search(b.dataset.try);
  if (hits[0]) choose(hits[0]);
}));

function choose(it) {
  closeSuggestions();
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
const isMixedTown = (it) => it.gem && it.gem.name === it.name && it.type <= 1 && Object.keys(it.gem.shares).length > 1;

function headline(it) {
  if (isMixedTown(it)) {
    const others = Object.keys(it.gem.shares).filter((k) => k !== it.state).map((k) => STATE[k].name).join(' und ');
    return {
      big: Object.keys(it.gem.shares).map((k) => `<span class="mark" style="--c:var(${STATE[k].color})">${STATE[k].adj}</span>`).join(' &amp; '),
      line: `${esc(it.name)} ist erst durch die Gemeindereform zusammengewachsen. Der Ortskern lag in ${STATE[it.state].name}, Teile der heutigen Stadt in ${others}.`,
    };
  }
  const line = {
    B: `${esc(it.name)} lag vor 1945 in der Republik Baden.`,
    W: `${esc(it.name)} lag vor 1945 im Volksstaat Württemberg.`,
    H: `Weder noch: ${esc(it.name)} gehörte zu den Hohenzollerischen Landen – und war damit bis 1945 preußisch.`,
    X: `Überraschung: ${esc(it.name)} war bis 1945 eine Exklave des Volksstaats Hessen.`,
  }[it.state];
  return { big: `<span class="mark">${STATE[it.state].adj}</span>`, line };
}

function mixedTable(it) {
  const groups = {};
  for (const p of DB.items) {
    if (p.gem !== it.gem || p.type > 4 || p.name === it.gem.name) continue;
    (groups[p.state] ||= []).push(p);
  }
  const rows = Object.keys(it.gem.shares).filter((k) => groups[k]).map((k) => {
    const ps = groups[k].sort((a, b) => a.type - b.type || a.name.localeCompare(b.name, 'de'));
    const links = ps.slice(0, 30).map((p) => `<a href="#ort/${p.osm}-${slug(p.name)}">${esc(p.name)}</a>`).join(', ');
    return `<tr><th style="--c:var(${STATE[k].color})"><i></i>${STATE[k].name}</th><td>${links}${ps.length > 30 ? ' …' : ''} <span>${Math.round(it.gem.shares[k] * 100)}&nbsp;%&nbsp;der&nbsp;Fläche</span></td></tr>`;
  }).join('');
  return `<table class="parts"><caption>Die heutige Gemeinde ${esc(it.gem.name)} nach altem Land</caption>${rows}</table>`;
}

function showResult(it) {
  current = it;
  const el = $('#result');
  el.replaceChildren($('#tplResult').content.cloneNode(true));
  el.dataset.state = it.state;

  input.value = it.name;
  sign.dataset.state = it.state;
  signSub.textContent = isMixedTown(it)
    ? Object.keys(it.gem.shares).map((k) => STATE[k].long.split(' (')[0]).join(' / ')
    : STATE[it.state].long;

  const h = headline(it);
  $('.res__ctx', el).textContent = context(it);
  $('.res__big', el).innerHTML = h.big;
  $('.res__line', el).innerHTML = h.line;
  document.title = `${it.name}: ${STATE[it.state].adj} – Baden oder Württemberg?`;

  const rows = [
    ['Land bis 1945', isMixedTown(it) ? Object.keys(it.gem.shares).map((k) => STATE[k].long).join(' / ') : STATE[it.state].long],
    ['Kreis 1945', it.k45 && it.k45[1] === it.state
      ? `<a href="${esc(it.k45[2])}" target="_blank" rel="noopener">${esc(it.k45[0])}</a>` : '<span title="Im Gemeindeverzeichnis 1945 nicht eindeutig gefunden">—</span>'],
    ['Gemeinde heute', it.gem ? esc(it.gem.name) : '—'],
    ['Kreis heute', it.gem && it.gem.kreis && it.gem.kreis !== it.gem.name ? esc(it.gem.kreis) : (it.gem ? 'kreisfrei' : '—')],
    ['Lage', `<a class="mono" href="https://www.openstreetmap.org/node/${it.osm}" target="_blank" rel="noopener">${it.lat.toFixed(4)}° N, ${it.lon.toFixed(4)}° O</a>`],
  ];
  $('.ledger', el).innerHTML = rows.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('');

  if (it.gem && Object.keys(it.gem.shares).length > 1) $('.res__mixed', el).innerHTML = mixedTable(it);

  const notes = [];
  if (it.flag === 1) notes.push(['warn', `<b>Grenzlage.</b> ${esc(it.name)} liegt weniger als 250&nbsp;m von der alten Landesgrenze entfernt. Die Zuordnung ist wahrscheinlich, aber nicht sicher – Ortskundige bitte prüfen.`]);
  if (it.flag === 2) notes.push(['warn', `<b>Quellen widersprechen sich.</b> Laut Gemeindeverzeichnis 1945 gehört ein Ort dieses Namens zum ${esc(it.k45[0])} (${STATE[it.k45[1]].name}). Vermutlich eine Namensdoppelung.`]);
  if (it.state === 'H') notes.push(['', 'Die Fürstentümer Hohenzollern-Hechingen und -Sigmaringen kamen 1850 an Preußen. Bis 1945 waren die Hohenzollerischen Lande ein preußischer Regierungsbezirk mit Sitz in Sigmaringen.']);
  if (it.state === 'X') notes.push(['', 'Wimpfen war bis 1945 hessische Exklave zwischen Baden und Württemberg. Nach dem Krieg kam es zu Württemberg-Baden, 1952 zu Baden-Württemberg.']);
  $('.notes', el).innerHTML = notes.map(([cls, t]) => `<li class="${cls}">${t}</li>`).join('');

  $('.chronik__place', el).textContent = it.name;
  el.addEventListener('click', onResultClick);
  setupForm($('.form--feedback', el), 'feedback');
  setupForm($('.form--story', el), 'story');
  loadStories(it);

  $('#ergebnis').hidden = false;
  $('.sign-wrap').scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (map) {
    if (marker) marker.remove();
    marker = L.circleMarker([it.lat, it.lon], {
      radius: 7, weight: 3, color: '#111', fillColor: cssVar('--sign'), fillOpacity: 1,
    }).addTo(map).bindTooltip(it.name, { permanent: true, direction: 'right', offset: [8, 0] });
    map.setView([it.lat, it.lon], 11);
  }
}

function onResultClick(e) {
  const act = e.target.closest('[data-act]')?.dataset.act;
  if (!act) return;
  const el = $('#result');
  if (act === 'share') {
    const url = location.href;
    if (navigator.share) navigator.share({ title: 'Baden oder Württemberg?', text: `${current.name} war ${STATE[current.state].adj}!`, url }).catch(() => {});
    else navigator.clipboard?.writeText(url).then(() => { e.target.textContent = 'Link kopiert'; });
    return;
  }
  const f = $(act === 'feedback' ? '.form--feedback' : '.form--story', el);
  f.hidden = !f.hidden;
  if (!f.hidden) f.querySelector('textarea').focus();
}

/* ---------- Ortschronik ---------- */
async function loadStories(it) {
  const ol = $('#result .chronik__list');
  try {
    const r = await fetch(`${API}?a=stories&place=${it.osm}`);
    if (!r.ok) throw new Error(r.status);
    const data = await r.json();
    if (current !== it) return;
    ol.innerHTML = data.stories.length
      ? data.stories.map(renderStory).join('')
      : `<li class="chronik__empty">Noch kein Eintrag zu ${esc(it.name)}.</li>`;
  } catch (e) {
    ol.innerHTML = '<li class="chronik__empty">Die Chronik konnte gerade nicht geladen werden.</li>';
  }
}

function renderStory(s) {
  const d = new Date(s.created * 1000);
  const date = d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
  return `<li class="entry"><time datetime="${d.toISOString().slice(0, 10)}">${date}</time><div><p>${esc(s.body)}</p><footer>— ${esc(s.author || 'ohne Namen')}</footer></div></li>`;
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
  box.className = 'captcha';
  box.innerHTML = `<input type="checkbox" id="${id}" /><label for="${id}">Ich bin kein Roboter<small>Dein Browser löst eine kleine Rechenaufgabe. Keine Cookies.</small></label>`;
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
      box.querySelector('small').textContent = 'Bestätigt.';
    } catch (e) {
      cb.checked = false;
      box.querySelector('small').textContent = 'Hat nicht geklappt – bitte nochmal.';
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
      status.textContent = 'Bitte zuerst „Ich bin kein Roboter“ ankreuzen.';
      return;
    }
    const body = Object.fromEntries(new FormData(form));
    Object.assign(body, { a: kind, captcha: box.payload, place: current.osm, placeName: current.name, state: current.state });
    btn.disabled = true;
    status.className = 'form__status';
    status.textContent = 'Wird gesendet …';
    try {
      const r = await fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.error || 'Senden fehlgeschlagen.');
      status.className = 'form__status ok';
      if (kind === 'story') {
        status.textContent = 'Danke! Dein Eintrag steht in der Chronik.';
        const ol = $('#result .chronik__list');
        $('.chronik__empty', ol)?.remove();
        ol.insertAdjacentHTML('afterbegin', renderStory(data.story));
      } else {
        status.textContent = 'Danke! Wir sehen uns das an.';
      }
      form.reset();
    } catch (err) {
      status.className = 'form__status err';
      status.textContent = err.message;
    } finally {
      setupCaptcha(box);
      btn.disabled = false;
    }
  });
}

/* ---------- Map with hatched states ---------- */
function updatePatterns() {
  const svg = map.getPanes().overlayPane.querySelector('svg');
  if (!svg) return;
  let defs = svg.querySelector('defs');
  if (!defs) { defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs'); svg.prepend(defs); }
  defs.innerHTML = Object.entries(STATE).map(([k, s]) => {
    const c = cssVar(s.color);
    const mark = k === 'X'
      ? `<circle cx="3" cy="3" r="1.3" fill="${c}" />`
      : `<line x1="0" y1="0" x2="0" y2="7" stroke="${c}" stroke-width="1.6" />`;
    return `<pattern id="hatch-${k}" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(${s.hatch})">${mark}</pattern>`;
  }).join('');
}

function borderStyle(f) {
  const k = f.properties.code;
  return { color: cssVar(STATE[k].color), weight: 2, opacity: 0.9, fillColor: `url(#hatch-${k})`, fillOpacity: 0.55 };
}

function initMap(borders) {
  map = L.map('map', { scrollWheelZoom: false, zoomSnap: 0.5 }).setView([48.65, 9.0], 7.5);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>-Mitwirkende · Grenzen 1939: <a href="https://www.openhistoricalmap.org/">OpenHistoricalMap</a>',
    maxZoom: 18,
  }).addTo(map);
  borderLayer = L.geoJSON(borders, { style: borderStyle, interactive: false }).addTo(map);
  updatePatterns();
  map.fitBounds(borderLayer.getBounds(), { padding: [6, 6] });
  map.on('focus', () => map.scrollWheelZoom.enable());
  map.on('blur', () => map.scrollWheelZoom.disable());
  map.on('click', (e) => {
    const it = nearest(e.latlng.lat, e.latlng.lng);
    if (!it) return;
    L.popup().setLatLng(e.latlng).setContent(
      `<strong>${esc(it.name)}</strong> – ${STATE[it.state].adj}<br /><a href="#ort/${it.osm}-${slug(it.name)}">Eintrag aufschlagen</a>`,
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

/* ---------- Statistik ---------- */
function renderStats(s) {
  $('#countPlaces').textContent = fmt(s.places);
  const rows = ['B', 'W', 'H', 'X'].map((k) => `<tr><td><i style="--c:var(${STATE[k].color})"></i>Orte in ${STATE[k].long}</td><td>${fmt(s.byState[k] || 0)}</td></tr>`);
  rows.push(`<tr class="sum"><td>Orte insgesamt</td><td>${fmt(s.places)}</td></tr>`);
  rows.push(`<tr><td>Heutige Gemeinden</td><td>${fmt(s.gemeinden)}</td></tr>`);
  rows.push(`<tr><td>davon mit Gebiet aus mehreren alten Ländern</td><td>${fmt(s.mixedGemeinden)}</td></tr>`);
  $('#stats').innerHTML = `<caption>Statistik des Verzeichnisses</caption>${rows.join('')}`;
  const v = s.validation;
  $('#validationText').textContent = `Von ${fmt(v.compared)} eindeutig vergleichbaren Gemeinden stimmen ${fmt(v.agree)} (${(v.agree / v.compared * 100).toFixed(1).replace('.', ',')} %) mit der Karte überein; die übrigen sind überwiegend Namensdoppelungen. Wo es passt, ist der Kreis von 1945 als Beleg verlinkt.`;
}

/* ---------- Datenschutz ---------- */
$('#privacyLink').addEventListener('click', () => {
  const p = $('#datenschutz');
  p.hidden = !p.hidden;
  if (!p.hidden) p.scrollIntoView({ behavior: 'smooth' });
});

loadData().catch((e) => {
  console.error(e);
  signSub.textContent = 'Ortsdaten konnten nicht geladen werden – bitte neu laden.';
});
