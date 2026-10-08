"""Export the raw inputs from build/cache/ into sources/ (versioned, readable formats).

  sources/historical_states_1939.geojson   OHM borders, full resolution (CC0)
  sources/osm_places_bw.csv                every named place node fetched from OSM (ODbL)
  sources/osm_gemeinden_bw.geojson         today's Gemeinden incl. Stadtkreise, simplified ~10 m (ODbL)
  sources/osm_kreise_bw.geojson            today's Land- and Stadtkreise, simplified ~10 m (ODbL)
  sources/gemeindeverzeichnis_1945.csv     municipality lists per Kreis, 1. 1. 1945 (territorial.de)
  sources/validation_report.json           result of the cross-check (agree / disagree / unmatched)
"""
import csv
import json
import re
import shutil

from shapely.geometry import mapping

from build import CACHE, ROOT, STATES, admin_areas, load, relation_polygon

OUT = ROOT.parent / "sources"
STATE_NAMES = {"B": "Republik Baden", "W": "Volksstaat Württemberg",
               "H": "Hohenzollerische Lande (Preußen)", "X": "Volksstaat Hessen"}


def rounded(geom, digits):
    def r(obj):
        if isinstance(obj, (list, tuple)):
            if obj and isinstance(obj[0], float):
                return [round(obj[0], digits), round(obj[1], digits)]
            return [r(o) for o in obj]
        return obj
    g = mapping(geom)
    g["coordinates"] = r(g["coordinates"])
    return g


def write_geojson(path, features):
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                               ensure_ascii=False, separators=(",", ":")))


def main():
    OUT.mkdir(exist_ok=True)

    feats = []
    for rel in load("ohm_states.json"):
        t = rel["tags"]
        code = STATES[rel["id"]]
        feats.append({"type": "Feature", "properties": {
            "code": code, "name": STATE_NAMES[code], "start_date": t.get("start_date"),
            "end_date": t.get("end_date"), "ohm_relation": rel["id"], "wikidata": t.get("wikidata"),
        }, "geometry": rounded(relation_polygon(rel), 6)})
    write_geojson(OUT / "historical_states_1939.geojson", feats)

    with open(OUT / "osm_places_bw.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["osm_node", "name", "place", "lat", "lon"])
        for el in sorted(load("osm_places.json"), key=lambda e: e["id"]):
            w.writerow([el["id"], el["tags"]["name"], el["tags"]["place"], el["lat"], el["lon"]])

    kreise = admin_areas("osm_admin6.json")
    gemeinden = admin_areas("osm_admin8.json") + [(t, p) for t, p in kreise if "kreis" not in t.get("name", "").lower()]
    for name, areas in (("osm_kreise_bw.geojson", kreise), ("osm_gemeinden_bw.geojson", gemeinden)):
        write_geojson(OUT / name, [{"type": "Feature", "properties": {
            "name": t.get("name"), "ags": t.get("de:amtlicher_gemeindeschluessel", ""),
            "wikidata": t.get("wikidata", ""),
        }, "geometry": rounded(p.simplify(0.0001, preserve_topology=True), 5)} for t, p in areas])

    with open(OUT / "gemeindeverzeichnis_1945.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["land", "kreis", "gemeinde", "quelle"])
        for k in json.loads((CACHE / "territorial.json").read_text()):
            kreis = re.sub(r"^Gemeindeverzeichnis\s+|\s*\[.*$", "", k["kreis"])
            for g in k["gemeinden"]:
                w.writerow([STATE_NAMES[k["land"]], kreis, g, k["url"]])

    shutil.copy(CACHE / "validation_report.json", OUT / "validation_report.json")
    for p in sorted(OUT.iterdir()):
        print(f"{p.name:40} {p.stat().st_size / 1e6:6.2f} MB")


if __name__ == "__main__":
    main()
