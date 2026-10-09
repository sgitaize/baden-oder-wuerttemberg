# Baden oder Württemberg?

**https://baden-oder-württemberg.de** – ein Ortsverzeichnis für das heutige Baden-Württemberg: Lag ein Ort vor 1945 in **Baden**, in **Württemberg**, in den preußischen **Hohenzollerischen Landen** – oder, im Fall von Bad Wimpfen, sogar in **Hessen**?

- 14.558 Einträge – Städte, Dörfer, Stadt- und Ortsteile, Weiler und Einzelhöfe sowie alle 1.101 Gemeinden –, jeweils mit heutiger Gemeinde und heutigem Kreis
- Kreis von 1945 als Beleg (verlinkt), Hinweis bei Orten in Grenzlage
- 47 heutige Gemeinden mit Ortsteilen auf beiden Seiten der alten Grenze (z. B. Villingen-Schwenningen, Schramberg, Tuttlingen), aufgeschlüsselt nach Ortsteilen
- **Steckbrief** zu jedem Ort: Einwohnerentwicklung als Diagramm, Fläche, Höhe, Einwohnerdichte, Ersterwähnung, Wappen und Foto, Abstand zur alten Grenze und nächster Ort „auf der anderen Seite“
- Karte mit den schraffierten Ländergrenzen von 1939
- Rückmeldungen zur Zuordnung und eine öffentliche **Ortschronik** zu jedem Ort – ohne Benutzerkonto, mit datensparsamem Captcha

## Inhalt

```
public/            Website (= Docroot)
  index.html       Seite
  assets/          app.js, style.css, favicon.svg
  data/            vom Build erzeugt: places.json, borders.json, facts.json, stats.json
  api/             PHP + SQLite: api.php (öffentlich), admin.php (Moderation), lib.php
sources/           aufbereitete Rohdaten (siehe unten), versioniert
build/             Datenaufbereitung: fetch.sh, fetch_territorial.py, fetch_wikidata.py, fetch_commons.py,
                   build.py, validate.py, export_sources.py
deploy/deploy.sh   Upload per FTPS – nur der committete und gepushte Stand
```

## Datenquellen

Alle Rohdaten wurden am **2026-10-08** abgerufen. Die Dateien in [`sources/`](sources/) sind die aufbereiteten Rohdaten, mit denen die Website gebaut ist.

| Datei | Inhalt | Quelle | Lizenz |
|-------|--------|--------|--------|
| `historical_states_1939.geojson` | Grenzen der vier Länder, volle Auflösung | OpenHistoricalMap | CC0 |
| `osm_places_bw.csv` | 14.413 benannte Ortspunkte (`osm_node, name, place, lat, lon`) | OpenStreetMap | ODbL |
| `osm_gemeinden_bw.geojson` | 1.101 heutige Gemeinden inkl. Stadtkreise und 2 gemeindefreie Gebiete (vereinfacht auf ~10 m, mit AGS) | OpenStreetMap | ODbL |
| `osm_kreise_bw.geojson` | 44 heutige Land- und Stadtkreise (vereinfacht auf ~10 m) | OpenStreetMap | ODbL |
| `gemeindeverzeichnis_1945.csv` | 3.355 Gemeinden mit Land und Kreis zum 1. 1. 1945 (`land, kreis, gemeinde, quelle`) | territorial.de | Fakten, Quelle je Zeile verlinkt |
| `wikidata_facts.json` | 3.677 Wikidata-Objekte: Einwohnerzeitreihen (Jahr, Wert, Beleg), Fläche, Höhe, Ersterwähnung, Gründung/Auflösung, Wappen, Foto, Wikipedia-Artikel | Wikidata | CC0 |
| `commons_images.json` | 4.318 Bilder: Vorschau-URL, Urheber*in, Lizenz | Wikimedia Commons | je Bild angegeben |
| `validation_report.json` | Ergebnis der Gegenprobe: übereinstimmend / widersprüchlich / nicht zugeordnet | eigene Auswertung | – |

### 1. Historische Ländergrenzen – OpenHistoricalMap

[OpenHistoricalMap](https://www.openhistoricalmap.org/) ist ein OpenStreetMap-Ableger für historische Karten, in dem Grenzen mit `start_date`/`end_date` erfasst sind. Über die Overpass-API (`overpass-api.openhistoricalmap.org`) habe ich zuerst alle `boundary=administrative`-Relationen mit `admin_level` 2 oder 4 im Raum Baden-Württemberg gesucht und dann die vier für den Stichtag **1. 1. 1939** gültigen ausgewählt:

| Relation | Name | gültig |
|----------|------|--------|
| [2661248](https://www.openhistoricalmap.org/relation/2661248) | Republik Baden | 1918 – 1.12.1945 |
| [2661270](https://www.openhistoricalmap.org/relation/2661270) | Volksstaat Württemberg | 1.12.1918 – 8.5.1945 |
| [2894236](https://www.openhistoricalmap.org/relation/2894236) | Hohenzollerische Lande | 19.11.1928 – 10.1945 |
| [2746244](https://www.openhistoricalmap.org/relation/2746244) | Volksstaat Hessen (für die Exklave Wimpfen) | 1.10.1932 – 19.9.1945 |

Abfrage: `rel(id:2661248,2661270,2894236,2746244); out geom;` – die Außen- und Innenringe werden in `build.py` mit shapely zu Polygonen zusammengesetzt.

Warum 1939? Das ist der letzte Stand vor Kriegsende, an dem sich die Länder kaum noch verändert haben; die Grenzen galten so im Wesentlichen seit 1810 (Hohenzollern seit 1850).

### 2. Orte und Gemeinden von heute – OpenStreetMap

Über die Overpass-API (`overpass-api.de`) innerhalb der Fläche `ISO3166-2=DE-BW`:

- alle Nodes mit `place` = `city`, `town`, `village`, `suburb`, `quarter`, `hamlet`, `isolated_dwelling` und einem `name`
- alle Relationen `boundary=administrative` mit `admin_level=6` (Kreise) und `admin_level=8` (Gemeinden), jeweils mit Geometrie

Stadtkreise (Stuttgart, Karlsruhe, Mannheim …) sind in OSM nur als `admin_level=6` erfasst und werden deshalb zusätzlich als Gemeinde behandelt. Übernommen werden nur Gemeinden mit baden-württembergischem Gemeindeschlüssel (`08…`); die Abfrage erwischt sonst z. B. das Schweizer Bettingen. Die gemeindefreien Gebiete Gutsbezirk Münsingen und „Rheinau“ (Rheininseln, Schlüssel `…971`) zählen nicht als Gemeinde. 136 Gemeinden haben keinen gleichnamigen Ortspunkt, sondern nur Ortsteile (z. B. Albstadt, Filderstadt, Ammerbuch); sie bekommen einen eigenen Eintrag am Mittelpunkt ihrer Fläche.

### 3. Gegenprobe – Gemeindeverzeichnisse 1945 (territorial.de)

Rolf Jehkes Projekt [Territoriale Veränderungen in Deutschland 1874–1945](https://territorial.de/) enthält für jeden Land- und Stadtkreis ein Gemeindeverzeichnis zum Stand 1. 1. 1945. `fetch_territorial.py` geht die Kreisübersichten für [Baden](https://territorial.de/baden/kreise.htm), [Württemberg](https://territorial.de/wuerttbg/kreise.htm), [Hohenzollern](https://territorial.de/hohenz/kreise.htm) und [Hessen](https://territorial.de/hessen/kreise.htm) durch, folgt dem Link „Gemeindeverzeichnis … 1945“ und liest die Gemeindetabellen aus (gedrosselt, jede Seite nur einmal).

Zwei Korrekturen sind im Skript dokumentiert: Die Seite des Landkreises Lahr trägt im Titel versehentlich „Landkreis Bruchsal“, und aus Hessen wird nur Wimpfen übernommen.

### 4. Steckbriefe – Wikidata und Wikimedia Commons

In OpenStreetMap sind 3.318 Ortspunkte sowie alle Gemeinden und Kreise per `wikidata`-Tag mit Wikidata verknüpft. `fetch_wikidata.py` lädt diese 3.677 Objekte über die API `wbgetentities` (50 pro Abruf) und liest aus:

| Eigenschaft | Wikidata | Abdeckung |
|-------------|----------|-----------|
| Einwohnerzahl mit Stichtag (`P585`) und Beleg (`P248`) | P1082 | 1.316 Objekte, fast alle Gemeinden 1961–2025 |
| Fläche | P2046 | 1.741 |
| Höhe über NN | P2044 | 2.195 |
| Ersterwähnung | P1249 | 206 |
| Gründung / Auflösung (Eingemeindung) | P571 / P576 | 85 / 7 |
| Wappen / Foto | P94 / P18 | 2.217 / 2.137 |
| Artikel in der deutschen Wikipedia | Sitelink `dewiki` | 3.219 |

Die Einwohnerzahlen der Gemeinden stammen dort überwiegend aus den Gemeindeverzeichnissen des Statistischen Landesamts Baden-Württemberg (1975, 2022–2025) und den Volkszählungen. Für das Diagramm werden alle Werte vor 1960, die Volkszählungsjahre, jedes fünfte Jahr und der neueste Wert verwendet. Hat ein Ortsteil keine eigenen Zahlen, zeigt die Seite die Werte der Gemeinde und schreibt das dazu.

`fetch_commons.py` holt für jedes Wappen und Foto über die Commons-API (`imageinfo`, `extmetadata`) eine Vorschau mit 480 px Breite, Urheber*in und Lizenz. Beides steht auf der Website unter dem Bild.

Werte vor 1945 sind in Wikidata nur für rund 70 Orte erfasst. Die amtliche Reihe „Bevölkerungsentwicklung seit 1871“ des Statistischen Landesamts war im neuen Statistikportal (`daten.statistik-bw.de/genesisonline`) nicht frei abrufbar – eine mögliche Erweiterung.

## Methode

1. **Zuordnung:** Jeder Ortspunkt wird per Punkt-in-Polygon dem historischen Land zugeordnet, in dem er liegt (alle Orte liegen in genau einem Land).
2. **Heutige Gemeinde:** ebenfalls per Punkt-in-Polygon. Als **geteilt** gilt eine Gemeinde, wenn bewohnte Orte (ohne Einzelhöfe) auf beiden Seiten der alten Grenze liegen – das sind 47. Zusätzlich wird berechnet, welcher Flächenanteil in welchem alten Land liegt (Anteile unter 2 % gelten als Digitalisierungsrauschen). Liegt nur unbewohnte Fläche jenseits der Grenze (z. B. Schiltach, Haßmersheim), steht das als Hinweis dabei.
3. **Grenzlage:** Liegt ein Ort näher als 250 m an der Grenze zwischen zwei alten Ländern, wird das angezeigt (156 Einträge, davon viele Einzelhöfe). Die Außengrenze zu Bayern, Frankreich und der Schweiz zählt nicht.
4. **Abstand und Nachbarort:** Für jeden Ort wird der Abstand zur nächsten inneren Grenze berechnet; der nächstgelegene Ort im jeweils anderen Land wird im Browser ermittelt.
5. **Gegenprobe:** Die Gemeindenamen von 1945 werden normalisiert (ß → ss, „Bad“, „a. N.“, „, Stadt“ usw. entfernt) und mit den Orten abgeglichen. Bei mehrdeutigen Namen gewinnt der Ort, der am nächsten am Schwerpunkt der übrigen Gemeinden desselben Kreises liegt. Ergebnis: **3.111 von 3.119** eindeutig vergleichbaren Gemeinden (99,7 %) stimmen mit der Kartenzuordnung überein; die 8 Abweichungen sind überwiegend Namensdoppelungen (z. B. zwei „Bittelbronn“) und werden auf der Website markiert. 236 Gemeinden von 1945 ließen sich keinem heutigen Ortspunkt zuordnen (Namensänderungen, Zusammenlegungen) – Details in `validation_report.json`.

Stichproben bekannter Grenzfälle: Villingen badisch, Schwenningen württembergisch, Tennenbronn (heute Schramberg) badisch, Möhringen (heute Tuttlingen) badisch, Bad Herrenalb und Maulbronn württembergisch, Kürnbach badisch, Sigmaringen und Hechingen hohenzollerisch, Bad Wimpfen hessisch – alle korrekt.

**Grenzen der Methode:** Die Grenzlinien sind digitalisierte Rekonstruktionen. Kleine Gebietstausche einzelner Gemarkungen können fehlen, und ein Ortspunkt sagt nichts über abgelegene Teile einer Gemarkung. Deshalb gibt es auf der Website zu jedem Ort die Möglichkeit, eine Berichtigung zu melden.

## Daten neu erzeugen

```bash
cd build
uv venv .venv && uv pip install --python .venv/bin/python shapely
./fetch.sh                          # lädt alles nach build/cache/ (~65 MB, nicht im Repo; ca. 10 Minuten)
.venv/bin/python build.py           # erzeugt public/data/*.json und gibt die Statistik aus
.venv/bin/python validate.py        # zeigt Widersprüche und nicht zugeordnete Gemeinden
.venv/bin/python export_sources.py  # schreibt sources/
```

## Lokal starten

```bash
php -S 127.0.0.1:8099 -t public     # PHP ≥ 8.1 mit pdo_sqlite
```

## Rückmeldungen, Ortschronik, Datenschutz

- `api/api.php` speichert Rückmeldungen (nur für die Moderation sichtbar) und Chronik-Einträge (öffentlich) in SQLite.
- Captcha: Proof of Work nach dem Vorbild von [ALTCHA](https://altcha.org/) – der Browser sucht eine Zahl, deren SHA-256-Hash zur vom Server signierten Aufgabe passt (~0,5 s). Jede gelöste Aufgabe gilt nur einmal. Dazu ein Honeypot-Feld und höchstens 6 Beiträge pro Stunde.
- Es werden keine Cookies gesetzt und keine IP-Adressen gespeichert, nur ein täglich wechselnder Hash für das Rate-Limit.
- Moderation unter `/api/admin.php`; das Token steht in `api/config.php` (siehe `config.sample.php`, nicht im Repo).

## Lizenzhinweise

Kartendaten und Ortsdaten © OpenStreetMap-Mitwirkende, verfügbar unter der [Open Database License](https://www.openstreetmap.org/copyright). Historische Grenzen von OpenHistoricalMap (CC0). Steckbrief-Daten von Wikidata (CC0); Wappen und Fotos von Wikimedia Commons unter der jeweils am Bild genannten Lizenz. Gemeindeverzeichnisse 1945 nach [territorial.de](https://territorial.de/) (Rolf Jehke).

---
Ein Projekt von [Simon Gutjahr](https://simongutjahr.de) · [Impressum](https://simongutjahr.de/impressum/)
