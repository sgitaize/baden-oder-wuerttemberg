"""Cross-check places (polygon based) against territorial.de 1945 lists.

Prints conflicts and writes cache/territorial_match.json: osm id -> territorial entry index.
"""
import json
import math
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = {"B": "Baden", "W": "Württemberg", "H": "Hohenzollern", "X": "Hessen"}


def norm(name):
    n = name.lower().replace("ß", "ss")
    n = re.sub(r",.*$", "", n)
    n = re.sub(r"\s*\(.*\)", "", n)
    n = re.sub(r"^bad\s+", "", n)
    n = re.sub(r"\s+(a\.|am|an|im|i\.|ob|o\.|bei|b\.|auf|unter|u\.)(\s.*|$)", "", n)
    n = re.sub(r"[^a-zäöü]", "", n)
    return n


def compute(all_places, terr):
    """Return ({osm id: territorial index}, {osm id: conflicting territorial index}, report)."""
    places = [p for p in all_places if p[1] <= 3]  # city..suburb
    by_name = defaultdict(list)
    for p in places:
        by_name[norm(p[0])].append(p)

    # Pass 1: unique matches per kreis -> kreis centroid
    entries = []
    for ki, k in enumerate(terr):
        if k["land"] == "X" and "Bergstra" not in k["kreis"]:
            continue
        for g in k["gemeinden"]:
            if k["land"] == "X" and "Wimpfen" not in g:
                continue
            entries.append((ki, g, norm(g)))
    cent = defaultdict(list)
    for ki, g, n in entries:
        cands = by_name.get(n, [])
        if len(cands) == 1:
            cent[ki].append((cands[0][2], cands[0][3]))
    centroid = {ki: (sum(a for a, _ in v) / len(v), sum(b for _, b in v) / len(v)) for ki, v in cent.items()}

    match, conflict_ids, conflicts, missing, ok = {}, {}, [], [], 0
    for ki, g, n in entries:
        land = terr[ki]["land"]
        cands = by_name.get(n, [])
        if not cands:
            missing.append(f"{g} ({NAME[land]}, {terr[ki]['kreis']})")
            continue
        c = centroid.get(ki)
        if c:  # nearest candidate to the kreis centroid, within 40 km
            best = min(cands, key=lambda p: math.dist((p[2], p[3]), c))
            if math.dist((best[2], best[3]), c) > 0.45:
                missing.append(f"{g} (zu weit weg)")
                continue
        elif len(cands) == 1:
            best = cands[0]
        else:
            missing.append(f"{g} (mehrdeutig)")
            continue
        if best[4] == land:
            ok += 1
            match[best[7]] = ki
        else:
            conflict_ids[best[7]] = ki
            conflicts.append(f"{g}: 1945 {NAME[land]} ({terr[ki]['kreis'].split('Landkreis')[-1].split('[')[0].strip()}) "
                             f"vs Karte {NAME[best[4]]} @ {best[2]},{best[3]} border={best[6]}")
    report = {"ok": ok, "conflicts": conflicts, "unmatched": missing, "total": len(entries)}
    return match, conflict_ids, report


def main():
    data = json.loads((ROOT.parent / "public" / "data" / "places.json").read_text())
    terr = json.loads((ROOT / "cache" / "territorial.json").read_text())
    _, _, r = compute(data["places"], terr)
    print(f"ok={r['ok']} conflicts={len(r['conflicts'])} unmatched={len(r['unmatched'])} of {r['total']}")
    print("\n".join(r["conflicts"]))
    print("--- unmatched:", "; ".join(r["unmatched"]))


if __name__ == "__main__":
    main()
