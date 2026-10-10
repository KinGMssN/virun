"""Download ~10 freely-licensed photos per city from Wikimedia Commons API.

Saves to ~/workspace/virun-assets/resources/images/<city>/photos/<city>_NN.jpg
and writes raw_meta.json with author/license attribution.
"""
import json, os, re, urllib.request, urllib.parse, html, time

BASE = os.path.expanduser("~/workspace/virun-assets")
PHOTOS_PER_CITY = 10

QUERIES = {
    "kashmir": ["Kashmir valley landscape", "Dal Lake Srinagar"],
    "goa": ["Goa beach", "Basilica of Bom Jesus Goa"],
    "hyderabad": ["Charminar", "Hussain Sagar Hyderabad"],
    "visakhapatnam": ["RK Beach Visakhapatnam", "Araku Valley"],
}

UA = {"User-Agent": "VirunDatasetBot/1.0 (hackathon prototype image dataset)"}


def api_search(query, limit=14):
    params = {
        "action": "query", "format": "json",
        "generator": "search",
        "gsrsearch": "%s filetype:bitmap" % query,
        "gsrnamespace": 6, "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 1600,
        "iiextmetadatafilter": "Artist|LicenseShortName",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def clean_html(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def main():
    os.makedirs(BASE, exist_ok=True)
    meta = {}
    for city, queries in QUERIES.items():
        cdir = os.path.join(BASE, "resources", "images", city, "photos")
        os.makedirs(cdir, exist_ok=True)
        got = 0
        seen = set()
        for q in queries:
            if got >= PHOTOS_PER_CITY:
                break
            try:
                data = api_search(q)
            except Exception as e:
                print("[%s] search failed for %r: %s" % (city, q, e), flush=True)
                continue
            pages = (data.get("query") or {}).get("pages") or {}
            # prefer larger / richer results first is not guaranteed; keep API order
            for pid in sorted(pages, key=lambda x: int(x)):
                if got >= PHOTOS_PER_CITY:
                    break
                page = pages[pid]
                info = (page.get("imageinfo") or [{}])[0]
                durl = info.get("thumburl") or info.get("url")
                if not durl or durl in seen:
                    continue
                if not re.search(r"\.(jpe?g|png)(\?|$)", durl, re.I):
                    continue
                seen.add(durl)
                fname = "%s_%02d.jpg" % (city, got + 1)
                fpath = os.path.join(cdir, fname)
                try:
                    req = urllib.request.Request(durl, headers=UA)
                    with urllib.request.urlopen(req, timeout=60) as r:
                        blob = r.read()
                    if len(blob) < 20000:  # skip tiny/placeholder files
                        continue
                    with open(fpath, "wb") as f:
                        f.write(blob)
                except Exception as e:
                    print("[%s] download failed: %s" % (city, str(e)[:90]), flush=True)
                    continue
                em = info.get("extmetadata") or {}
                meta[fname] = {
                    "city": city,
                    "file": "resources/images/" + city + "/photos/" + fname,
                    "source_url": info.get("descriptionurl"),
                    "author": clean_html((em.get("Artist") or {}).get("value")),
                    "license": clean_html((em.get("LicenseShortName") or {}).get("value")),
                    "query": q,
                }
                got += 1
                print("[%s] %d/%d %s (%d KB)" % (city, got, PHOTOS_PER_CITY, fname, len(blob) // 1024), flush=True)
                time.sleep(0.4)
        print("[%s] done: %d photos" % (city, got), flush=True)
    with open(os.path.join(BASE, "raw_meta.json"), "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print("wrote raw_meta.json with %d entries" % len(meta), flush=True)


main()
