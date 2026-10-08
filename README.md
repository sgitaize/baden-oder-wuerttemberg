# Baden oder Württemberg?

**https://baden-oder-württemberg.de** – schlag nach, ob ein Ort im heutigen Baden-Württemberg vor 1945 **badisch**, **württembergisch**, **hohenzollerisch** (preußisch) oder sogar **hessisch** war.

- über 9.000 Städte, Dörfer, Ortsteile und Weiler, mit heutiger Gemeinde und Kreis
- Karte mit den Ländergrenzen von 1939
- gemischte Gemeinden (z. B. Villingen-Schwenningen) mit Aufschlüsselung nach Ortsteilen
- Hinweise bei Grenzlage und widersprüchlichen Quellen
- Rückmeldungen zur Zuordnung und öffentliche „Geschichten“ zu jedem Ort – ohne Konto, mit datensparsamem Captcha (Proof of Work im Browser, keine Cookies, keine IP-Speicherung)

## Quellen & Methode

| Was | Quelle | Lizenz |
|-----|--------|--------|
| Historische Ländergrenzen (Republik Baden 1918–45, Volksstaat Württemberg 1918–45, Hohenzollerische Lande 1928–45, Volksstaat Hessen 1932–45) | [OpenHistoricalMap](https://www.openhistoricalmap.org/) | CC0 |
| Orte, heutige Gemeinden und Kreise | [OpenStreetMap](https://www.openstreetmap.org/copyright) | ODbL |
| Gegenprobe: Gemeindeverzeichnisse aller Kreise, Stand 1. 1. 1945 | [territorial.de](https://territorial.de/) (Rolf Jehke) | Verlinkung als Beleg |

Jeder Ort wird per Koordinate dem historischen Land zugeordnet (Stichtag 1. 1. 1939). Anschließend wird die Zuordnung gegen die Gemeindeverzeichnisse 1945 geprüft: Von 3.119 eindeutig vergleichbaren Gemeinden stimmen 3.111 (99,7 %) überein; die Abweichungen sind überwiegend Namensdoppelungen. Orte unter 250 m von der alten Grenze werden als „Grenzlage“ markiert.

## Aufbau

```
public/          Website (Docroot): index.html, assets/, data/ (generiert), api/ (PHP + SQLite)
build/           Datenaufbereitung: fetch.sh (Rohdaten laden), build.py, validate.py
deploy/deploy.sh Upload per FTPS (nur committeter + gepushter Stand)
```

## Lokal starten

```bash
php -S 127.0.0.1:8099 -t public       # PHP ≥ 8.1 mit pdo_sqlite
```

## Daten neu erzeugen

```bash
cd build
uv venv .venv && uv pip install --python .venv/bin/python shapely
./fetch.sh && .venv/bin/python build.py
```

## Moderation

`/api/admin.php` – Login mit dem Admin-Token aus `api/config.php` (siehe `config.sample.php`). Rückmeldungen als erledigt markieren, Geschichten aus- oder einblenden und löschen.

---
Ein Projekt von [Simon Gutjahr](https://simongutjahr.de) · [Impressum](https://simongutjahr.de/impressum/)
