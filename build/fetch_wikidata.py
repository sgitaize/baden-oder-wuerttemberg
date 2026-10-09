"""Fetch facts for every OSM place / Gemeinde that links to Wikidata (wbgetentities API).

Writes cache/wikidata.json: {qid: {pop: [[year, value, source qid]], area, elev, first, inception,
dissolved, coa, image, article}} and cache/wikidata_sources.json: {source qid: German label}.
"""
import json
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

CACHE = Path(__file__).resolve().parent / "cache"
UA = "badenoderwuerttemberg-build/0.2 (https://baden-oder-württemberg.de)"
BATCH = 50
PROPS = {"P2046": "area", "P2044": "elev", "P1249": "first", "P571": "inception", "P576": "dissolved",
         "P94": "coa", "P18": "image"}


def get_entities(ids, props="claims|sitelinks"):
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
        "action": "wbgetentities", "ids": "|".join(ids), "props": props,
        "sitefilter": "dewiki", "languages": "de", "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r).get("entities", {})
        except Exception as exc:  # rate limit / network: back off
            print("retry", attempt, exc, flush=True)
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("wikidata failed")


def value(claim):
    snak = claim.get("mainsnak", {})
    if snak.get("snaktype") != "value":
        return None
    v = snak["datavalue"]["value"]
    if isinstance(v, dict):
        if "amount" in v:
            return float(v["amount"])
        if "time" in v:
            return v["time"].lstrip("+")[:10]
        return None
    return v


def parse(ent):
    d = {"pop": []}
    claims = ent.get("claims", {})
    for c in claims.get("P1082", []):
        amount = value(c)
        t = c.get("qualifiers", {}).get("P585", [{}])[0].get("datavalue", {}).get("value", {}).get("time", "")
        year = t.lstrip("+")[:4]
        if amount is None or not year.isdigit():
            continue
        src = ""
        for ref in c.get("references", []):
            for s in ref.get("snaks", {}).get("P248", []):
                src = s.get("datavalue", {}).get("value", {}).get("id", "") or src
        d["pop"].append([int(year), int(amount), src])
    for pid, key in PROPS.items():
        if claims.get(pid):
            best = sorted(claims[pid], key=lambda c: c.get("rank") != "preferred")[0]
            v = value(best)
            if v is not None:
                d[key] = round(v, 2) if isinstance(v, float) else v
    link = ent.get("sitelinks", {}).get("dewiki", {}).get("title")
    if link:
        d["article"] = link
    return d


def qids():
    out = set()
    for f in ("osm_places.json", "osm_admin8.json", "osm_admin6.json"):
        for e in json.loads((CACHE / f).read_text())["elements"]:
            q = e.get("tags", {}).get("wikidata", "")
            if q.startswith("Q"):
                out.add(q.split(";")[0])
    return sorted(out)


def main():
    ids = qids()
    result = {}
    for i in range(0, len(ids), BATCH):
        for q, ent in get_entities(ids[i:i + BATCH]).items():
            if "claims" in ent:
                result[q] = parse(ent)
        if i % 500 == 0:
            print(f"{i + BATCH}/{len(ids)}", flush=True)
        time.sleep(0.3)
    (CACHE / "wikidata.json").write_text(json.dumps(result, ensure_ascii=False))

    # Labels of the cited sources (e.g. Statistisches Landesamt), for attribution
    srcs = [q for q, _ in Counter(s for d in result.values() for _, _, s in d["pop"] if s).most_common()]
    labels = {}
    for i in range(0, len(srcs), BATCH):
        for q, ent in get_entities(srcs[i:i + BATCH], "labels").items():
            labels[q] = ent.get("labels", {}).get("de", {}).get("value", q)
    (CACHE / "wikidata_sources.json").write_text(json.dumps(labels, ensure_ascii=False, indent=1))
    print("done", len(result), "items,", len(labels), "sources", flush=True)


if __name__ == "__main__":
    main()
