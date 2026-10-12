#!/usr/bin/env python3
"""Statische Seiten für Suchmaschinen und Direktlinks, erzeugt aus public/data/*.json:
  /gemeinde/<slug>/   je heutiger Gemeinde: Land vor 1945, Kreis 1945, alle Ortsteile mit Zuordnung
  /kreis/<slug>/      je Kreis (Stand 1945): Land, Beleg territorial.de, zugehörige heutige Gemeinden
  /orte/              Übersicht aller Kreise 1945 und Gemeinden A–Z
  /sitemap.xml, /robots.txt
Nutzung: python3 build/pages.py   (ohne Abhängigkeiten; nach build.py ausführen)"""
import collections, html, json, os, re, shutil, unicodedata
from datetime import date

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public')
SITE = 'https://xn--baden-oder-wrttemberg-kic.de'
STATE = {'B': ('Baden', 'badisch'), 'W': ('Württemberg', 'württembergisch'),
         'H': ('Hohenzollern', 'hohenzollerisch'), 'X': ('Hessen', 'hessisch')}
TYPE = ['Stadt', 'Stadt', 'Dorf', 'Stadtteil', 'Ortsteil', 'Weiler', 'Hof', 'Gemeinde']
esc = html.escape


def slug(s):
    s = s.lower().replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if not unicodedata.combining(c))
    s = re.sub(r'\bst\.\s*', 'sankt ', s)
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def de_num(n):
    return f'{n:,}'.replace(',', '.')


def page(title, desc, path, body, crumbs):
    nav = ' · '.join(f'<a href="{h}">{esc(t)}</a>' for t, h in crumbs)
    return f'''<!DOCTYPE html>
<html lang="de" data-theme="dark">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}" />
  <link rel="canonical" href="{SITE}{path}" />
  <meta property="og:title" content="{esc(title)}" />
  <meta property="og:description" content="{esc(desc)}" />
  <meta property="og:image" content="{SITE}/assets/og.png" />
  <meta name="theme-color" content="#151719" />
  <link rel="icon" href="/assets/favicon.svg" type="image/svg+xml" />
  <link rel="stylesheet" href="/assets/fonts.css" />
  <link rel="stylesheet" href="/assets/style.css" />
  <script>try {{ const t = localStorage.getItem('theme'); if (t) document.documentElement.dataset.theme = t; }} catch (e) {{}}</script>
</head>
<body>
  <div class="mast-bar"><header class="mast">
    <a class="mast__title" href="/">Baden <i>oder</i> Württemberg</a>
    <nav class="mast__nav" aria-label="Navigation"><a href="/">Ort suchen</a><a href="/orte/">Alle Orte</a><a href="/quiz/">Quiz</a></nav>
  </header></div>
  <main class="legal static">
    <p class="crumbs">{nav}</p>
{body}
  </main>
  <footer class="colophon">
    <p>Herausgegeben von <a href="https://simongutjahr.de">Simon Gutjahr</a> · <a href="https://github.com/sgitaize/baden-oder-wuerttemberg">Quellcode &amp; Daten auf GitHub</a> · <a href="/presse/">Presse</a> · <a href="https://simongutjahr.de/impressum/">Impressum</a> · <a href="/datenschutz.html">Datenschutz</a></p>
    <p class="colophon__small">Orts- und Kartendaten © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>-Mitwirkende (<a href="https://opendatacommons.org/licenses/odbl/1-0/">ODbL</a>) · historische Grenzen <a href="https://www.openhistoricalmap.org/">OpenHistoricalMap</a> · Gemeindeverzeichnisse 1945 <a href="https://territorial.de/">territorial.de</a></p>
  </footer>
</body>
</html>
'''


def mark(k):
    return f'<span class="mark" style="--c:var(--{k})">{STATE[k][1]}</span>'


def write(path, text):
    f = os.path.join(ROOT, path.strip('/'), 'index.html') if path.endswith('/') else os.path.join(ROOT, path.strip('/'))
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, 'w', encoding='utf-8') as fh:
        fh.write(text)


QUIZ_JS = r"""
(() => {
  const ST = { B: ['Baden', 'badisch', '--B'], W: ['Württemberg', 'württembergisch', '--W'], H: ['Hohenzollern', 'hohenzollerisch', '--H'], X: ['Hessen', 'hessisch', '--X'] };
  const TYPE = ['Stadt', 'Stadt', 'Dorf'];
  const N = 10, $ = (s) => document.querySelector(s);
  const norm = (s) => s.toLowerCase().replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss')
    .normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\bst\.\s*/g, 'sankt ').replace(/[^a-z0-9]+/g, ' ').trim();
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  let near = [], far = [], G = [], round = 0, score = 0, cur = null, used = new Set();
  let best = 0; try { best = +localStorage.getItem('quizBest') || 0; } catch (e) {}
  const pick = () => { for (;;) { const pool = Math.random() < 0.7 ? near : far, p = pool[Math.floor(Math.random() * pool.length)]; if (!used.has(p[7])) { used.add(p[7]); return p; } } };
  function show() {
    cur = pick(); round++;
    const g = cur[5] >= 0 ? G[cur[5]] : null;
    $('#qPlace').textContent = cur[0];
    $('#qCtx').textContent = (g && g.name !== cur[0] ? TYPE[cur[1]] + ' von ' + g.name + ', ' : TYPE[cur[1]] + ', ') + (g ? g.kreis : '');
    $('#qRes').innerHTML = ''; $('#qNext').hidden = true;
    document.querySelectorAll('[data-s]').forEach((b) => { b.disabled = false; });
    $('#qScore').textContent = 'Frage ' + round + ' von ' + N + ' · ' + score + ' richtig';
  }
  function answer(s) {
    document.querySelectorAll('[data-s]').forEach((b) => { b.disabled = true; });
    const ok = s === cur[4]; if (ok) score++;
    const link = '/#ort/' + cur[7] + '-' + norm(cur[0]).replace(/ /g, '-');
    $('#qRes').innerHTML = (ok ? '<b>Richtig!</b> ' : '<b>Leider nein.</b> ') + esc(cur[0]) + ' war ' +
      '<span class="mark" style="--c:var(' + ST[cur[4]][2] + ')">' + ST[cur[4]][1] + '</span>' +
      (cur[9] != null && cur[9] < 3 ? ' – nur ' + String(cur[9]).replace('.', ',') + '&nbsp;km von der alten Grenze.' : '.') +
      ' <a href="' + link + '">Mehr zum Ort</a>';
    $('#qScore').textContent = 'Frage ' + round + ' von ' + N + ' · ' + score + ' richtig';
    $('#qNext').textContent = round < N ? 'Nächster Ort' : 'Ergebnis';
    $('#qNext').hidden = false; $('#qNext').focus();
  }
  function done() {
    if (score > best) { best = score; try { localStorage.setItem('quizBest', String(best)); } catch (e) {} }
    const txt = 'Baden oder Württemberg? Ich habe ' + score + ' von ' + N + ' Orten richtig zugeordnet.';
    $('#qPlace').textContent = score + ' / ' + N;
    $('#qCtx').textContent = score >= 9 ? 'Landeskundliche Spitzenklasse!' : score >= 7 ? 'Sehr ordentlich – du kennst dich aus.' : score >= 5 ? 'Solide. Die alte Grenze ist tückisch.' : 'Die Grenze verlief oft anders, als man denkt.';
    $('#qRes').innerHTML = 'Dein Bestwert: ' + best + ' / ' + N;
    document.querySelectorAll('[data-s]').forEach((b) => { b.disabled = true; });
    $('#qNext').textContent = 'Nochmal'; $('#qNext').hidden = false;
    $('#qShare').hidden = false;
    $('#qShare').onclick = () => {
      const url = location.origin + '/quiz/';
      if (navigator.share) navigator.share({ text: txt, url }).catch(() => {});
      else navigator.clipboard.writeText(txt + ' ' + url).then(() => { $('#qShare').textContent = 'Kopiert'; });
    };
    round = N + 1;
  }
  document.querySelectorAll('[data-s]').forEach((b) => b.addEventListener('click', () => answer(b.dataset.s)));
  $('#qNext').addEventListener('click', () => {
    if (round > N) { round = 0; score = 0; used.clear(); $('#qShare').hidden = true; $('#qShare').textContent = 'Ergebnis teilen'; show(); }
    else if (round === N) done(); else show();
  });
  fetch('/data.php?f=places').then((r) => r.json()).then((d) => {
    G = d.gemeinden;
    for (const p of d.places) if (p[1] <= 2 && p[6] === 0) (p[9] != null && p[9] < 8 ? near : far).push(p);
    $('#qOpts').hidden = false; show();
  }).catch(() => { $('#qPlace').textContent = 'Daten nicht erreichbar'; });
})();
"""


def quiz_and_press(P, G, K45, stats):
    body = f"""    <header class="sec__head"><span class="sec__no">Quiz</span><h1>Badisch oder württembergisch?</h1></header>
    <p class="sec__lead">Zehn Orte, eine Frage: Wo lag der Ort vor 1945? Die meisten liegen nah an der alten Landesgrenze – Bauchgefühl hilft nur bedingt.</p>
    <div class="quiz__card">
      <p class="quiz__place" id="qPlace">Lade Orte …</p>
      <p class="quiz__ctx" id="qCtx"></p>
      <div class="quiz__opts" id="qOpts" hidden>
        <button class="stamp" type="button" data-s="B" style="--c:var(--B)">Baden</button>
        <button class="stamp" type="button" data-s="W" style="--c:var(--W)">Württemberg</button>
        <button class="stamp" type="button" data-s="H" style="--c:var(--H)">Hohenzollern</button>
        <button class="stamp" type="button" data-s="X" style="--c:var(--X)">Hessen</button>
      </div>
      <p class="quiz__res" id="qRes" role="status"></p>
      <p><button class="stamp" type="button" id="qNext" hidden>Nächster Ort</button> <button class="stamp" type="button" id="qShare" hidden>Ergebnis teilen</button></p>
    </div>
    <p class="quiz__score" id="qScore"></p>
    <script>{QUIZ_JS}</script>"""
    write('/quiz/', page('Quiz: Badisch oder württembergisch? – Baden oder Württemberg?', 'Zehn Orte aus Baden-Württemberg: Lagen sie vor 1945 in Baden, Württemberg, Hohenzollern oder Hessen? Teste dein Wissen über die alte Landesgrenze.', '/quiz/', body, [('Start', '/')]))

    bs = stats['byState']
    body = f"""    <header class="sec__head"><span class="sec__no">Presse</span><h1>Presse &amp; Medien</h1></header>
    <p class="sec__lead"><b>baden-oder-württemberg.de</b> beantwortet eine Frage, die in Baden-Württemberg bis heute Gespräche füllt: War mein Ort früher badisch oder württembergisch? Für {de_num(stats['places'])} Orte, Ortsteile und Wohnplätze zeigt die Seite, in welchem Land sie vor 1945 lagen – mit Karte, Quellen und einer Ortschronik zum Mitschreiben.</p>
    <h2>Zahlen</h2>
    <dl class="ledger">
      <div><dt>Orte, Ortsteile, Wohnplätze</dt><dd>{de_num(stats['places'])}</dd></div>
      <div><dt>davon badisch</dt><dd>{de_num(bs.get('B', 0))}</dd></div>
      <div><dt>davon württembergisch</dt><dd>{de_num(bs.get('W', 0))}</dd></div>
      <div><dt>davon hohenzollerisch</dt><dd>{de_num(bs.get('H', 0))}</dd></div>
      <div><dt>davon hessisch (Bad Wimpfen)</dt><dd>{de_num(bs.get('X', 0))}</dd></div>
      <div><dt>heutige Gemeinden</dt><dd>{de_num(stats['gemeinden'])}</dd></div>
      <div><dt>Gemeinden mit badischen und württembergischen Teilen</dt><dd>{stats['mixedGemeinden']}</dd></div>
      <div><dt>Kreise im Jahr 1945</dt><dd>{len(K45)}</dd></div>
      <div><dt>Übereinstimmung mit den Gemeindeverzeichnissen 1945</dt><dd>{de_num(stats['validation']['agree'])} von {de_num(stats['validation']['compared'])}</dd></div>
    </dl>
    <h2>Was die Seite kann</h2>
    <ul>
      <li><b>Ortsschild-Suche:</b> Ortsname eintippen, das gelbe Schild zeigt das alte Land.</li>
      <li><b>Historische Karte</b> mit den Landesgrenzen 1918–1945 (Baden, Württemberg, Hohenzollerische Lande, Hessen).</li>
      <li><b>Damals → Heute:</b> Gemeinde, Kreis und Land 1945 neben der heutigen Gemeinde – auch für die {stats['mixedGemeinden']} Gemeinden, die durch die Gemeindereform über die alte Grenze hinweg zusammengewachsen sind (z.&nbsp;B. Villingen-Schwenningen).</li>
      <li><b>Ortschronik:</b> Leser*innen schreiben Erinnerungen, Familiengeschichten und Dialekt-Anekdoten zu ihrem Ort.</li>
      <li><b><a href="/quiz/">Quiz</a></b> mit Orten nahe der alten Grenze, <b><a href="/orte/">Verzeichnis</a></b> aller Gemeinden und Kreise 1945.</li>
    </ul>
    <h2>Methode und Quellen</h2>
    <p>Grundlage sind die historischen Landesgrenzen aus der <a href="https://www.openhistoricalmap.org/">OpenHistoricalMap</a> und die Orte aus <a href="https://www.openstreetmap.org/">OpenStreetMap</a>. Jeder Ort wird geometrisch den Ländern von 1945 zugeordnet und mit den Gemeindeverzeichnissen 1945 von <a href="https://territorial.de/">territorial.de</a> gegengeprüft. Orte nah an der Grenze sind gekennzeichnet. Code und Daten sind offen: <a href="https://github.com/sgitaize/baden-oder-wuerttemberg">GitHub</a> (MIT, Daten ODbL).</p>
    <h2>Bildmaterial</h2>
    <p><a href="/assets/og.png">Vorschaubild (1200 × 630 px, PNG)</a> – frei verwendbar für Berichte über die Seite.</p>
    <h2>Kontakt</h2>
    <p>Simon Gutjahr, Karlsruhe · <a href="mailto:kontakt@simongutjahr.de">kontakt@simongutjahr.de</a> · <a href="https://simongutjahr.de">simongutjahr.de</a></p>"""
    write('/presse/', page('Presse – Baden oder Württemberg?', 'Pressematerial zu baden-oder-württemberg.de: Zahlen, Methode, Quellen, Bildmaterial und Kontakt.', '/presse/', body, [('Start', '/')]))


def main():
    d = json.load(open(os.path.join(ROOT, 'data', 'places.json'), encoding='utf-8'))
    facts = json.load(open(os.path.join(ROOT, 'data', 'facts.json'), encoding='utf-8'))
    G, K45 = d['gemeinden'], d['kreise1945']
    P = [dict(zip(d['fields'], p)) for p in d['places']]
    for k in ('gemeinde', 'kreis'):
        shutil.rmtree(os.path.join(ROOT, k), ignore_errors=True)

    by_gem = collections.defaultdict(list)
    for p in P:
        by_gem[p['gemeinde']].append(p)
    # eindeutige Slugs: bei Namensgleichheit Kreis anhängen
    names = collections.Counter(g['name'] for g in G)
    gslug = [slug(g['name']) if names[g['name']] == 1 else slug(g['name'] + ' ' + g['kreis']) for g in G]
    kslug = [slug(k[0]) for k in K45]
    gem_k45 = {}   # Gemeinde -> Kreise 1945 (nach Anzahl Orte)
    k45_gems = collections.defaultdict(set)
    for gi, ps in by_gem.items():
        c = collections.Counter(p['kreis1945'] for p in ps if p['kreis1945'] >= 0)
        gem_k45[gi] = [k for k, _ in c.most_common()]
        for k in c:
            k45_gems[k].add(gi)

    urls = ['/', '/orte/', '/quiz/', '/presse/']
    # ---------- Gemeinden ----------
    for gi, g in enumerate(G):
        if not by_gem.get(gi):
            continue   # z. B. gemeindefreie Gebiete ohne Ort
        ps = sorted(by_gem.get(gi, []), key=lambda p: (p['type'] == 7, p['name'] != g['name'], p['name']))
        ps = [p for p in ps if p['type'] != 7] or ps
        states = sorted(g['shares'], key=lambda k: -g['shares'][k])
        main_p = next((p for p in ps if p['name'] == g['name']), ps[0] if ps else None)
        kreis = g['kreis'] if g['kreis'] != g['name'] else 'kreisfreie Stadt'
        if len(states) == 1:
            s = states[0]
            answer = f'{esc(g["name"])} war vor 1945 {mark(s)}.'
            lead = f'Das gesamte heutige Gemeindegebiet von {esc(g["name"])} ({esc(kreis)}) lag vor 1945 in {STATE[s][0]}.'
            desc = f'{g["name"]} ({kreis}) war vor 1945 {STATE[s][1]}: alle Ortsteile lagen in {STATE[s][0]}. Mit Kreis 1945, Ortsteilen, Karte und Quellen.'
        else:
            answer = f'{esc(g["name"])} war vor 1945 geteilt: ' + ' &amp; '.join(mark(k) for k in states) + '.'
            lead = f'{esc(g["name"])} ({esc(kreis)}) ist durch die Gemeindereform aus Orten zusammengewachsen, die vor 1945 in verschiedenen Ländern lagen: ' + \
                ', '.join(f'{STATE[k][0]} ({round(g["shares"][k] * 100)} % der Fläche)' for k in states) + '.'
            desc = f'{g["name"]} ({kreis}) lag vor 1945 teils in ' + ' und teils in '.join(STATE[k][0] for k in states) + '. Welcher Ortsteil wohin gehörte – mit Karte und Quellen.'
        k45 = gem_k45.get(gi, [])
        rows = []
        if k45:
            rows.append(('Kreis 1945', ', '.join(f'<a href="/kreis/{kslug[k]}/">{esc(K45[k][0])}</a>' for k in k45)))
        rows.append(('Kreis heute', esc(kreis)))
        f = facts.get(g.get('qid') or '', {})
        if f.get('p'):
            y, n = f['p'][-1]
            rows.append((f'Einwohner*innen {y}', de_num(int(n))))
        if f.get('a'):
            rows.append(('Fläche', f'{str(f["a"]).replace(".", ",")} km²'))
        ledger = '\n'.join(f'      <div><dt>{a}</dt><dd>{b}</dd></div>' for a, b in rows)
        trs = '\n'.join(
            f'      <tr><th style="--c:var(--{p["state"]})"><i></i>{STATE[p["state"]][0]}</th><td><a href="/#ort/{p["osm"]}-{slug(p["name"])}">{esc(p["name"])}</a>'
            f' <span>{TYPE[p["type"]]}{" · Grenzlage" if p["flag"] == 1 else ""}</span></td></tr>' for p in ps)
        mapl = f'/#ort/{main_p["osm"]}-{slug(main_p["name"])}' if main_p else '/'
        body = f'''    <header class="sec__head"><span class="sec__no">Gemeinde</span><h1>{esc(g["name"])}: Baden oder Württemberg?</h1></header>
    <p class="static__answer">{answer}</p>
    <p class="sec__lead">{lead}</p>
    <dl class="ledger">
{ledger}
    </dl>
    <p><a class="stamp" href="{mapl}">Auf der Karte ansehen</a></p>
    <h2>Ortsteile und Wohnplätze ({len(ps)})</h2>
    <table class="parts"><tbody>
{trs}
    </tbody></table>
    <p class="note">Zuordnung nach den Landesgrenzen 1918–1945 (OpenHistoricalMap), gegengeprüft mit den Gemeindeverzeichnissen 1945. Etwas falsch? Auf der <a href="{mapl}">Ortsseite</a> kannst du eine Berichtigung schicken oder einen Eintrag in die Ortschronik schreiben.</p>'''
        path = f'/gemeinde/{gslug[gi]}/'
        crumbs = [('Start', '/'), ('Alle Orte', '/orte/')] + ([(K45[k45[0]][0], f'/kreis/{kslug[k45[0]]}/')] if k45 else [])
        write(path, page(f'{g["name"]}: Baden oder Württemberg? – vor 1945 {" / ".join(STATE[k][1] for k in states)}', desc, path, body, crumbs))
        urls.append(path)

    # ---------- Kreise 1945 ----------
    for ki, (kname, ks, src) in enumerate(K45):
        gems = sorted(k45_gems.get(ki, []), key=lambda gi: G[gi]['name'])
        n_orte = sum(1 for p in P if p['kreis1945'] == ki)
        lis = '\n'.join(f'      <li><a href="/gemeinde/{gslug[gi]}/">{esc(G[gi]["name"])}</a> <span>{esc(G[gi]["kreis"])}</span></li>' for gi in gems)
        body = f'''    <header class="sec__head"><span class="sec__no">Kreis 1945</span><h1>{esc(kname)}</h1></header>
    <p class="static__answer">Der {esc(kname)} gehörte 1945 zu {mark(ks)}.</p>
    <p class="sec__lead">{de_num(n_orte)} heutige Orte und Wohnplätze lagen 1945 im {esc(kname)}. Sie gehören heute zu diesen {len(gems)} Gemeinden:</p>
    <ul class="cols">
{lis}
    </ul>
    <p class="note">Beleg: <a href="{esc(src)}">Gemeindeverzeichnis des {esc(kname)}, Stand 1.1.1945</a> (territorial.de, Rolf Jehke).</p>'''
        path = f'/kreis/{kslug[ki]}/'
        write(path, page(f'{kname} (1945) – {STATE[ks][0]}', f'Der {kname} gehörte 1945 zu {STATE[ks][0]}. Alle heutigen Gemeinden mit Orten aus dem {kname}.', path, body,
                         [('Start', '/'), ('Alle Orte', '/orte/')]))
        urls.append(path)

    # ---------- Übersicht ----------
    secs = []
    for s in ('B', 'W', 'H', 'X'):
        ks = sorted((k for k in range(len(K45)) if K45[k][1] == s), key=lambda k: K45[k][0].replace('Stadtkreis ', '').replace('Landkreis ', ''))
        if ks:
            secs.append(f'    <h2>{STATE[s][0]}</h2>\n    <ul class="cols">\n' + '\n'.join(f'      <li><a href="/kreis/{kslug[k]}/">{esc(K45[k][0])}</a></li>' for k in ks) + '\n    </ul>')
    letters = collections.defaultdict(list)
    for gi in sorted((gi for gi in range(len(G)) if by_gem.get(gi)), key=lambda gi: slug(G[gi]['name'])):
        letters[slug(G[gi]['name'])[0].upper()].append(gi)
    az = '\n'.join(f'    <h3 id="{L}">{L}</h3>\n    <ul class="cols">\n' + '\n'.join(
        f'      <li><a href="/gemeinde/{gslug[gi]}/">{esc(G[gi]["name"])}</a>{" <span>geteilt</span>" if G[gi]["mixed"] else ""}</li>' for gi in gis) + '\n    </ul>'
        for L, gis in sorted(letters.items()))
    jump = ' '.join(f'<a href="#{L}">{L}</a>' for L in sorted(letters))
    body = f'''    <header class="sec__head"><span class="sec__no">Verzeichnis</span><h1>Alle Orte</h1></header>
    <p class="sec__lead">{len(K45)} Kreise (Stand 1945) und {de_num(sum(1 for gi in range(len(G)) if by_gem.get(gi)))} heutige Gemeinden in Baden-Württemberg – mit allen {de_num(len(P))} Orten, Ortsteilen und Wohnplätzen.</p>
    <h2>Kreise 1945</h2>
{chr(10).join(secs)}
    <h2>Gemeinden heute, A–Z</h2>
    <p class="az">{jump}</p>
{az}'''
    write('/orte/', page('Alle Orte und Kreise – Baden oder Württemberg?', f'Verzeichnis aller {len(G)} Gemeinden in Baden-Württemberg und der {len(K45)} Kreise von 1945: badisch, württembergisch, hohenzollerisch oder hessisch?', '/orte/', body, [('Start', '/')]))

    quiz_and_press(P, G, K45, json.load(open(os.path.join(ROOT, 'data', 'stats.json'), encoding='utf-8')))
    today = date.today().isoformat()
    with open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8') as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        fh.write(''.join(f'  <url><loc>{SITE}{u}</loc><lastmod>{today}</lastmod></url>\n' for u in urls))
        fh.write('</urlset>\n')
    with open(os.path.join(ROOT, 'robots.txt'), 'w', encoding='utf-8') as fh:
        fh.write(f'User-agent: *\nDisallow: /api/\nSitemap: {SITE}/sitemap.xml\n')
    print(f'{sum(1 for gi in range(len(G)) if by_gem.get(gi))} Gemeinde-Seiten, {len(K45)} Kreis-Seiten, sitemap mit {len(urls)} Adressen')


if __name__ == '__main__':
    main()
