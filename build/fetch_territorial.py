"""Fetch the 1945 municipality lists per Landkreis from territorial.de (Rolf Jehke).

Used to cross-check the polygon-based classification and as per-place source link.
Writes cache/territorial.json: [{land, kreis, url, gemeinden: [...]}].
"""
import html
import json
import re
import time
import urllib.request
from pathlib import Path

BASE = "https://territorial.de/"
LANDS = {"B": "baden/kreise.htm", "W": "wuerttbg/kreise.htm", "H": "hohenz/kreise.htm", "X": "hessen/kreise.htm"}
OUT = Path(__file__).resolve().parent / "cache" / "territorial.json"


PAGES = OUT.parent / "territorial_pages"


def get(url):
    PAGES.mkdir(exist_ok=True)
    cached = PAGES / re.sub(r"[^a-z0-9]+", "_", url.lower())
    if cached.exists():
        return cached.read_text()
    page = fetch(url)
    cached.write_text(page)
    return page


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "bow-build/0.1 (simongutjahr.de)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    time.sleep(0.7)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def links(page):
    return re.findall(r'href="([^"#]+)"[^>]*>(.*?)</a>', page, re.S)


def text(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).split()


def main():
    result = []
    seen = set()
    for land, index in LANDS.items():
        index_url = BASE + index
        kreis_pages = sorted({urllib.parse.urljoin(index_url, h) for h, _ in links(get(index_url))
                              if h.count("/") == 1 and not h.startswith("..")})
        for kp in kreis_pages:
            try:
                page = get(kp)
            except Exception as exc:
                print("fail", kp, exc)
                continue
            for h, label in links(page):
                label = " ".join(text(label))
                if "Gemeindeverzeichnis" not in label or "1945" not in label:
                    continue
                url = urllib.parse.urljoin(kp, h)
                if url in seen:
                    continue
                seen.add(url)
                gp = get(url)
                title = " ".join(text(re.search(r"<h2>(.*?)</h2>", gp, re.S).group(1)))
                names = []
                for row in re.findall(r"<tr>(.*?)</tr>", gp, re.S):
                    cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
                    if len(cells) >= 3 and re.fullmatch(r"\d+\.", " ".join(text(cells[0]))):
                        name = next((" ".join(text(c)) for c in cells[1:] if text(c)), "")
                        if name:
                            names.append(name)
                result.append({"land": land, "kreis": title, "url": url, "gemeinden": names})
                print(land, title, len(names))
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    import urllib.parse
    main()
