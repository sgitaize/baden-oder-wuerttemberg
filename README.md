# Baden & Württemberg Kartenexplorer

Statische Website, die Orte in Baden-Württemberg auf einer interaktiven Leaflet-Karte zeigt. Jeder Ort trägt eine Quelle zur historischen Zuordnung (Baden, Württemberg oder gemischt).

## Nutzung

1. Repo klonen oder Dateien auf einen Webspace (z. B. Netcup) kopieren.
2. Stelle sicher, dass `data/places.json` mit den gewünschten Orten gefüllt ist.
3. Öffne `index.html` im Browser. Für lokale Tests empfiehlt sich ein einfacher HTTP-Server, damit das Laden der JSON-Datei funktioniert:
   ```bash
   python -m http.server 8000
   ```
   Dann im Browser `http://localhost:8000` öffnen.

## Datenpflege

- Quellen pro Ort sind verpflichtend und sollten auf Behörden-, Forschungs- oder peer-reviewte Publikationen verweisen.
- Erweiterungen erfolgen in `data/places.json`. Hinweise siehe `data/README.md`.

## Technologie

- Leaflet + OpenStreetMap-Tiles für die Karte
- Statisches HTML/CSS/JS (keine Build-Tools erforderlich)
