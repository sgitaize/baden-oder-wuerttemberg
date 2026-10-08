"""Build the lookup data for the website.

Inputs (build/cache/, fetched by fetch.sh):
  ohm_states.json  historical state borders from OpenHistoricalMap (CC0)
  osm_places.json  named places in Baden-Württemberg from OpenStreetMap (ODbL)
  osm_admin6.json  today's Landkreise / Stadtkreise (OSM)
  osm_admin8.json  today's Gemeinden (OSM)

Outputs (../data/):
  places.json   every place with its historical state
  borders.json  simplified historical borders as GeoJSON for the map
  stats.json    counts for the website
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

from shapely.geometry import LineString, Point, mapping
import shapely
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree

import validate

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache"
OUT = ROOT.parent / "public" / "data"

# OpenHistoricalMap relations valid for the reference date 1939-01-01
STATES = {
    2661248: "B",  # Republik Baden 1918–1945
    2661270: "W",  # Volksstaat Württemberg 1918–1945
    2894236: "H",  # Hohenzollerische Lande (Preußen) 1928–1945
    2746244: "X",  # Volksstaat Hessen 1932–1945 (Exklave Wimpfen)
}
PLACE_TYPES = {"city": 0, "town": 1, "village": 2, "suburb": 3, "quarter": 4, "hamlet": 5}
# Points closer than this to a historical border are flagged as uncertain
BORDER_UNCERTAIN_M = 250
# Share below which a historical state is ignored for a Gemeinde (sliver noise)
MIN_SHARE = 0.02


def relation_polygon(rel):
    def lines(role):
        return [
            LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
            for m in rel["members"]
            if m["type"] == "way" and m.get("role", "outer") == role and len(m.get("geometry", [])) > 1
        ]

    outer = unary_union(list(polygonize(unary_union(lines("outer")))))
    inner_lines = lines("inner")
    if inner_lines:
        outer = outer.difference(unary_union(list(polygonize(unary_union(inner_lines)))))
    return outer.buffer(0)


# Rough local metric projection (good enough for distances/areas within BW)
def to_metric(geom):
    return shapely.transform(geom, lambda c: c * [73500.0, 111200.0])


def load(name):
    return json.loads((CACHE / name).read_text())["elements"]


def admin_areas(name):
    areas = []
    for rel in load(name):
        try:
            poly = relation_polygon(rel)
        except Exception as exc:  # broken relation in OSM, report and skip
            print(f"skip {rel['tags'].get('name')}: {exc}", file=sys.stderr)
            continue
        if poly.is_empty:
            print(f"skip {rel['tags'].get('name')}: empty", file=sys.stderr)
            continue
        areas.append((rel["tags"], poly))
    return areas


def main():
    states = {}
    for rel in load("ohm_states.json"):
        states[STATES[rel["id"]]] = relation_polygon(rel)
    state_lines_m = {k: to_metric(v.boundary) for k, v in states.items()}

    kreise = admin_areas("osm_admin6.json")
    gemeinden = admin_areas("osm_admin8.json")
    # Stadtkreise are only tagged admin_level 6 in OSM: treat them as Gemeinden too
    gemeinden += [(t, p) for t, p in kreise if "kreis" not in t.get("name", "").lower()]
    bw = unary_union([p for _, p in kreise])

    def locate(areas, tree, pt):
        for i in tree.query(pt, predicate="intersects"):
            return areas[int(i)][0]
        return None

    kreis_tree = STRtree([p for _, p in kreise])
    gem_tree = STRtree([p for _, p in gemeinden])

    # Gemeinden: share of today's area per historical state
    gem_out = []
    for tags, poly in gemeinden:
        total = to_metric(poly).area
        shares = {}
        for code, st in states.items():
            a = to_metric(poly.intersection(st)).area / total
            if a >= MIN_SHARE:
                shares[code] = round(a, 3)
        kreis = locate(kreise, kreis_tree, poly.representative_point())
        gem_out.append({
            "name": tags.get("name"),
            "ags": tags.get("de:amtlicher_gemeindeschluessel", ""),
            "kreis": kreis.get("name") if kreis else "",
            "shares": dict(sorted(shares.items(), key=lambda kv: -kv[1])),
        })
    gem_index = {g["ags"] + g["name"]: i for i, g in enumerate(gem_out)}

    places = []
    unassigned = 0
    for el in load("osm_places.json"):
        t = el["tags"]
        if t["place"] not in PLACE_TYPES:
            continue
        pt = Point(el["lon"], el["lat"])
        if not bw.contains(pt):
            continue
        hits = [c for c, st in states.items() if st.contains(pt)]
        if len(hits) != 1:
            unassigned += 1
            continue
        code = hits[0]
        ptm = to_metric(pt)
        dist = min(line.distance(ptm) for line in state_lines_m.values())
        gem = locate(gemeinden, gem_tree, pt)
        gi = gem_index.get(gem.get("de:amtlicher_gemeindeschluessel", "") + gem.get("name")) if gem else None
        places.append([
            t["name"],
            PLACE_TYPES[t["place"]],
            round(el["lat"], 5),
            round(el["lon"], 5),
            code,
            gi if gi is not None else -1,
            1 if dist < BORDER_UNCERTAIN_M else 0,
            el["id"],
        ])
    places.sort(key=lambda p: (p[1], p[0]))

    # Cross-check with the 1945 municipality lists (territorial.de) and attach them as source
    terr = json.loads((CACHE / "territorial.json").read_text())
    match, conflict_ids, report = validate.compute(places, terr)
    used = sorted(set(match.values()) | set(conflict_ids.values()))
    terr_index = {ki: i for i, ki in enumerate(used)}
    sources = []
    for ki in used:
        k = terr[ki]
        name = re.sub(r"^Gemeindeverzeichnis\s+|\s*\[.*$", "", k["kreis"])
        sources.append([name, k["land"], k["url"]])
    for p in places:
        osm = p[7]
        if osm in match:
            p.append(terr_index[match[osm]])
        elif osm in conflict_ids:
            p[6] = 2  # sources disagree
            p.append(terr_index[conflict_ids[osm]])
        else:
            p.append(-1)
    (ROOT / "cache" / "validation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))

    # Borders for the map: clip to today's BW, simplify (~150 m)
    features = []
    for code, st in states.items():
        geom = st.intersection(bw.buffer(0.01)).simplify(0.0015, preserve_topology=True)
        features.append({"type": "Feature", "properties": {"code": code}, "geometry": mapping(geom)})

    def round_coords(obj):
        if isinstance(obj, (list, tuple)):
            if obj and isinstance(obj[0], float):
                return [round(obj[0], 4), round(obj[1], 4)]
            return [round_coords(o) for o in obj]
        return obj

    for f in features:
        f["geometry"]["coordinates"] = round_coords(f["geometry"]["coordinates"])

    OUT.mkdir(exist_ok=True)
    (OUT / "places.json").write_text(json.dumps(
        {"fields": ["name", "type", "lat", "lon", "state", "gemeinde", "flag", "osm", "kreis1945"],
         "gemeinden": gem_out, "kreise1945": sources, "places": places},
        ensure_ascii=False, separators=(",", ":")))
    (OUT / "borders.json").write_text(json.dumps(
        {"type": "FeatureCollection", "features": features}, separators=(",", ":")))

    by_state = Counter(p[4] for p in places)
    mixed = [g for g in gem_out if len(g["shares"]) > 1]
    stats = {
        "places": len(places),
        "gemeinden": len(gem_out),
        "byState": dict(by_state),
        "mixedGemeinden": len(mixed),
        "borderFlagged": sum(1 for p in places if p[6] == 1),
        "sourcesDisagree": sum(1 for p in places if p[6] == 2),
        "validation": {"agree": report["ok"], "disagree": len(report["conflicts"]), "compared": report["ok"] + len(report["conflicts"])},
    }
    (OUT / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    print(json.dumps(stats, ensure_ascii=False), f"unassigned={unassigned}")
    print("gemischt:", ", ".join(sorted(f"{g['name']} {g['shares']}" for g in mixed)))


if __name__ == "__main__":
    main()
