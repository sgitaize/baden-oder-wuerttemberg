# Datenquellen

* **Geokoordinaten:** OpenStreetMap/OSM Nominatim-Koordinaten (WGS84), statisch hinterlegt.
* **Historische Zuordnung (Baden/Württemberg/Gemischt):** Für jeden Ort ist eine Quelle angegeben (Behörden, Universitäten, Stadtarchive). Die Spalte `region` spiegelt den historischen Landesteil wider und sollte bei neuen Datensätzen anhand belegbarer Quellen gepflegt werden.
* **Erweiterung:** Füge neue Orte in `places.json` als Objekte mit den Feldern `name`, `lat`, `lon`, `region` (`Baden`, `Württemberg`, `Gemischt`), `sourceName`, `sourceUrl`, `notes` hinzu. Empfohlene Quellen: Landesarchiv Baden-Württemberg (LEO-BW), Statistisches Landesamt Baden-Württemberg (Gemeindeverzeichnis), kommunale Statistikstellen oder peer-reviewte Publikationen.
