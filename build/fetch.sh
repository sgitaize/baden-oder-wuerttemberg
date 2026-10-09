#!/usr/bin/env bash
# Lädt alle Rohdaten nach build/cache/ (danach: .venv/bin/python build.py)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
mkdir -p cache
UA='badenoderwuerttemberg-build (https://baden-oder-württemberg.de)'

overpass() { # url query outfile
  for try in 1 2 3 4 5; do
    curl -s -m 600 -A "$UA" "$1" --data-urlencode "data=$2" > "$3"
    head -c 1 "$3" | grep -q '{' && return 0
    echo "Overpass busy, retry $try …"; sleep $((try * 15))
  done
  echo "Fehler beim Laden von $3"; return 1
}

BW='area["ISO3166-2"="DE-BW"][admin_level=4]->.bw;'
# Historische Länder 1939 aus OpenHistoricalMap (CC0)
overpass https://overpass-api.openhistoricalmap.org/api/interpreter \
  '[out:json][timeout:250];(rel(id:2661248,2661270,2894236,2746244););out geom;' cache/ohm_states.json
# Orte und heutige Verwaltungsgrenzen aus OpenStreetMap (ODbL)
overpass https://overpass-api.de/api/interpreter \
  "[out:json][timeout:500];$BW(node(area.bw)[\"place\"~\"^(city|town|village|suburb|hamlet|quarter|isolated_dwelling)$\"][\"name\"];);out body;" cache/osm_places.json
for lvl in 6 8; do
  overpass https://overpass-api.de/api/interpreter \
    "[out:json][timeout:500];${BW}rel(area.bw)[boundary=administrative][admin_level=$lvl];out geom;" cache/osm_admin$lvl.json
done
# Gemeindeverzeichnisse 1945 (territorial.de)
python3 fetch_territorial.py
# Steckbriefe: Wikidata (Einwohner, Fläche, Höhe, Wappen …) und Bildnachweise von Wikimedia Commons
python3 fetch_wikidata.py
python3 fetch_commons.py
