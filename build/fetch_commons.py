"""Fetch thumbnail URL, author and license for every image referenced in cache/wikidata.json.

Writes cache/commons.json: {file name: {thumb, page, artist, license}}.
"""
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

CACHE = Path(__file__).resolve().parent / "cache"
UA = "badenoderwuerttemberg-build/0.2 (https://baden-oder-württemberg.de)"


def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def main():
    wd = json.loads((CACHE / "wikidata.json").read_text())
    files = sorted({d[k] for d in wd.values() for k in ("coa", "image") if d.get(k)})
    out = {}
    for i in range(0, len(files), 50):
        chunk = files[i:i + 50]
        url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "titles": "|".join("File:" + f for f in chunk), "prop": "imageinfo",
            "iiprop": "url|extmetadata", "iiurlwidth": 480, "iiextmetadatafilter": "Artist|LicenseShortName",
            "format": "json"})
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            pages = json.load(r)["query"]["pages"].values()
        for p in pages:
            info = (p.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata", {})
            name = p["title"].split(":", 1)[1]
            out[name] = {
                "thumb": info.get("thumburl", ""),
                "page": info.get("descriptionurl", ""),
                "artist": clean(meta.get("Artist", {}).get("value"))[:120],
                "license": clean(meta.get("LicenseShortName", {}).get("value")),
            }
        if i % 500 == 0:
            print(f"{i + 50}/{len(files)}", flush=True)
        time.sleep(0.3)
    (CACHE / "commons.json").write_text(json.dumps(out, ensure_ascii=False))
    print("done", len(out), flush=True)


if __name__ == "__main__":
    main()
