#!/usr/bin/env python3
"""Nightly data refresh for the energy tracker.
Sources:
  - EIA-860M monthly generator inventory (xlsx, no API key): battery storage fleet + pipeline
  - FERC eLibrary Advanced Search API: filings matching "data center" (rolling window)
Outputs: docs/data/battery.json, docs/data/ferc.json, docs/data/meta.json
"""
import io, json, re, sys, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
import pandas as pd

EIA_BASE = "https://www.eia.gov/electricity/data/eia860m/xls/{}_generator{}.xlsx"
MONTHS = ["january","february","march","april","may","june","july","august","september","october","november","december"]
FERC_URL = "https://elibrary.ferc.gov/eLibrarywebapi/api/Search/AdvancedSearch"
FERC_DOCINFO = "https://elibrary.ferc.gov/eLibrary/docinfo?accession_number={}"
OUT = "docs/data"

UA = {"User-Agent": "energy-tracker-data-bot (public data refresh; contact: site owner)"}

def fetch(url, data=None, headers=None, timeout=120):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def latest_eia860m():
    """Find the newest EIA-860M file, trying this month backwards."""
    now = datetime.now(timezone.utc)
    for back in range(0, 6):
        d = (now.replace(day=1) - timedelta(days=1)).replace(day=1) if back else now
        # step back `back` months properly
        y, m = now.year, now.month
        for _ in range(back):
            m -= 1
            if m == 0: m, y = 12, y - 1
        url = EIA_BASE.format(MONTHS[m-1], y)
        try:
            blob = fetch(url, timeout=180)
            if len(blob) > 1_000_000:
                return blob, url, f"{MONTHS[m-1].capitalize()} {y}"
        except Exception as e:
            print(f"  eia try {MONTHS[m-1]} {y}: {e}", file=sys.stderr)
    raise RuntimeError("No EIA-860M file found in the last 6 months")

def num(s):
    return pd.to_numeric(s, errors="coerce")

def battery_frame(xlsx_bytes, sheet, status_kind):
    df = pd.read_excel(io.BytesIO(xlsx_bytes), sheet_name=sheet, skiprows=2)
    mask = (df["Energy Source Code"].astype(str).str.upper() == "MWH") & \
           (df["Technology"].astype(str).str.contains("Batter", case=False, na=False))
    df = df[mask].copy()
    df["mw"] = num(df["Nameplate Capacity (MW)"]).fillna(0)
    mwh_col = df["Nameplate Energy Capacity (MWh)"] if "Nameplate Energy Capacity (MWh)" in df.columns else None
    df["mwh"] = num(mwh_col).fillna(0) if mwh_col is not None else 0.0
    df["status_raw"] = df["Status"].astype(str)
    df["status"] = df["status_raw"].str.replace(r"^\([A-Z]+\)\s*", "", regex=True).str.strip()
    ycol = "Operating Year" if status_kind == "operating" else "Planned Operation Year"
    df["year"] = num(df.get(ycol))
    df["kind"] = status_kind
    keep = {"Entity Name":"developer","Plant ID":"plant_id","Plant Name":"name",
            "Plant State":"state","County":"county","Balancing Authority Code":"ba",
            "Sector":"sector","Latitude":"lat","Longitude":"lon"}
    df = df.rename(columns=keep)
    for c in ("developer","plant_id","name","state","county","ba","sector"):
        df[c] = df[c].astype(str).replace({"nan": None})
    return df[["plant_id","name","developer","state","county","ba","sector","mw","mwh",
               "status","year","kind","lat","lon"]]

BA_NAMES = {"CISO":"CAISO","ERCO":"ERCOT","PJM":"PJM","MISO":"MISO","NYIS":"NYISO",
            "ISNE":"ISO-NE","SWPP":"SPP","NEVP":"NV Energy","PACE":"PacifiCorp E",
            "PACW":"PacifiCorp W","BPAT":"BPA","SOCO":"Southern","DUK":"Duke",
            "FPCL":"FPL","TVA":"TVA","AZPS":"APS","SRP":"SRP","PSCO":"PSCo",
            "PNM":"PNM","TEPC":"TEP","IPCO":"Idaho Power","PGE":"PGE",
            "PSEI":"Puget Sound","AVA":"Avista","EPE":"El Paso","WACM":"WAPA RMR",
            "WALC":"WAPA DSW","IID":"IID","LDWP":"LADWP","BANC":"BANC","TIDC":"TID",
            "GRID":"Gridforce","SPA":"SPP (MO)","AECI":"AECI","LGEE":"LG&E/KU",
            "CPLW":"CPLW","EEI":"Eastern KY"}

def build_battery():
    print("Downloading EIA-860M ...")
    blob, url, month_label = latest_eia860m()
    print(f"  using {month_label} ({len(blob)/1e6:.1f} MB)")
    parts = []
    for sheet, kind in (("Operating","operating"), ("Planned","pipeline"),
                        ("Operating_PR","operating"), ("Planned_PR","pipeline")):
        try:
            parts.append(battery_frame(blob, sheet, kind))
        except Exception as e:
            print(f"  sheet {sheet}: {e}", file=sys.stderr)
    df = pd.concat(parts, ignore_index=True)
    # plant-level aggregation
    g = (df.groupby(["plant_id","name","state","ba","kind","status"], dropna=False)
           .agg(developer=("developer","first"), county=("county","first"),
                sector=("sector","first"), mw=("mw","sum"), mwh=("mwh","sum"),
                units=("mw","size"), year=("year","max"), lat=("lat","first"), lon=("lon","first"))
           .reset_index())
    op = g[g.kind=="operating"]
    pl = g[g.kind=="pipeline"]
    totals = {
        "operating_mw": round(op.mw.sum(),1), "operating_mwh": round(op.mwh.sum(),1),
        "operating_plants": int(len(op)), "operating_units": int(op.units.sum()),
        "pipeline_mw": round(pl.mw.sum(),1), "pipeline_plants": int(len(pl)),
        "states": int(g[g.mw>0].state.nunique()),
    }
    by_state = []
    for st, sub in g.groupby("state"):
        by_state.append({"state": st,
            "mw": round(sub[sub.kind=="operating"].mw.sum(),1),
            "mwh": round(sub[sub.kind=="operating"].mwh.sum(),1),
            "pipeline_mw": round(sub[sub.kind=="pipeline"].mw.sum(),1),
            "plants": int(len(sub[sub.kind=="operating"]))})
    by_state.sort(key=lambda r: -r["mw"])
    by_ba = []
    for ba, sub in g.groupby("ba"):
        if not ba or ba == "None": continue
        by_ba.append({"ba": BA_NAMES.get(ba, ba), "code": ba,
            "mw": round(sub[sub.kind=="operating"].mw.sum(),1),
            "pipeline_mw": round(sub[sub.kind=="pipeline"].mw.sum(),1),
            "plants": int(len(sub[sub.kind=="operating"]))})
    by_ba.sort(key=lambda r: -r["mw"])
    by_year_map = {}
    for _, r in op[op.year.notna() & (op.year>=2000) & (op.year<=2030)].iterrows():
        y = int(r.year)
        by_year_map[y] = round(by_year_map.get(y,0) + r.mw, 1)
    by_year, cum = [], 0.0
    for y in sorted(by_year_map):
        cum += by_year_map[y]
        by_year.append({"year": y, "mw_added": by_year_map[y], "cumulative_mw": round(cum,1)})
    projects = []
    for _, r in g.sort_values("mw", ascending=False).iterrows():
        projects.append({
            "name": r["name"], "developer": r["developer"], "state": r["state"],
            "county": r["county"], "ba": BA_NAMES.get(r["ba"], r["ba"]),
            "mw": round(r.mw,1), "mwh": round(r.mwh,1) if r.mwh else None,
            "units": int(r.units), "status": r["status"], "kind": r["kind"],
            "year": int(r.year) if pd.notna(r.year) else None,
            "lat": r.lat if pd.notna(r.lat) else None, "lon": r.lon if pd.notna(r.lon) else None})
    out = {"source": {"name": "EIA-860M Monthly Electric Generator Inventory",
                      "file_month": month_label, "url": url,
                      "publisher": "U.S. Energy Information Administration"},
           "totals": totals, "by_state": by_state, "by_ba": by_ba,
           "by_year": by_year, "projects": projects}
    with open(f"{OUT}/battery.json","w") as f: json.dump(clean(out), f, separators=(",",":"), allow_nan=False)
    print(f"  battery.json: {len(projects)} projects, {totals['operating_mw']:.0f} MW operating")
    return month_label


def clean(o):
    import math
    if isinstance(o, float) and math.isnan(o): return None
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    return o

BOILER = re.compile(r"\s+")
def summarize(desc, author, dockets):
    d = BOILER.sub(" ", (desc or "")).strip()
    d = re.sub(r"^Filing of\s+", "", d)
    if len(d) > 260: d = d[:257].rsplit(" ",1)[0] + "…"
    return d

def build_ferc(days=60):
    print("Querying FERC eLibrary ...")
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    body = {"searchText": '"data center"', "searchFullText": True, "searchDescription": True,
            "dateSearches": [{"dateType": "filed_date",
                              "startDate": start.strftime("%m/%d/%Y"),
                              "endDate": end.strftime("%m/%d/%Y")}],
            "availability": None, "affiliations": [], "categories": [], "libraries": [],
            "accessionNumber": None, "eFiling": False, "docketSearches": [],
            "resultsPerPage": 100, "curPage": 1, "classTypes": [], "sortBy": "",
            "groupBy": "NONE", "idolResultID": "", "allDates": False}
    raw = fetch(FERC_URL, data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"}, timeout=90)
    res = json.loads(raw)
    hits = res.get("searchHits") or []
    # Hot dockets we cover with articles: fetch every filing so coverage does not
    # depend on the relevance ordering of the "data center" full-text search.
    HOT_DOCKETS = ["ER26-1323", "ER26-2249", "ER26-3265", "ER26-3380", "ER26-3515", "ER26-3525", "ER26-3552", "ER26-3591", "ER26-3650", "ER26-3685", "EL26-67", "EL26-68", "EL26-69", "EL26-70", "EL26-71", "EL26-72"]
    for dk in HOT_DOCKETS:
        try:
            dbody = dict(body)
            dbody["searchText"] = ""
            dbody["docketSearches"] = [{"docketNumber": dk, "subDocket": "*"}]
            dbody["dateSearches"] = [{"dateType": "filed_date",
                                      "startDate": (end - timedelta(days=365)).strftime("%m/%d/%Y"),
                                      "endDate": end.strftime("%m/%d/%Y")}]
            dres = json.loads(fetch(FERC_URL, data=json.dumps(dbody).encode(),
                                    headers={"Content-Type": "application/json"}, timeout=90))
            dhits = dres.get("searchHits") or []
            total = int(dres.get("totalHits") or len(dhits))
            for page in range(2, (total + dbody["resultsPerPage"] - 1) // dbody["resultsPerPage"] + 1):
                pbody = dict(dbody); pbody["curPage"] = page
                pres = json.loads(fetch(FERC_URL, data=json.dumps(pbody).encode(),
                                        headers={"Content-Type": "application/json"}, timeout=90))
                dhits.extend(pres.get("searchHits") or [])
            have = {(h.get("acesssionNumber") or "").strip() for h in hits}
            added = [h for h in dhits if (h.get("acesssionNumber") or "").strip() not in have]
            hits += added
            print(f"  docket {dk}: {len(dhits)} filings (merged new: {len(added)})")
        except Exception as e:
            print(f"  docket {dk} fetch failed: {e}", file=sys.stderr)
    items = []
    for h in hits:
        author = next((a["affiliation"] for a in (h.get("affiliations") or [])
                       if a.get("afType") == "AUTHOR"), None)
        cls = (h.get("classTypes") or [{}])[0]
        tr = (h.get("transmittals") or [{}])[0]
        items.append({
            "file_id": tr.get("fileId"), "file_name": tr.get("fileName"),
            "file_size": tr.get("fileSize"), "file_desc": tr.get("fileDesc"),
            "summary": summarize(h.get("description"), author, h.get("docketNumbers")),
            "description": BOILER.sub(" ", (h.get("description") or "")).strip(),
            "filed": h.get("filedDate"), "issued": h.get("issuedDate"),
            "dockets": h.get("docketNumbers") or [],
            "accession": h.get("acesssionNumber"),
            "class": cls.get("documentClass"), "type": cls.get("documentType"),
            "category": h.get("category"), "author": author,
            "url": FERC_DOCINFO.format(h.get("acesssionNumber") or "")})
    def k(it):
        try: return datetime.strptime(it["filed"], "%m/%d/%Y")
        except Exception: return datetime.min
    items.sort(key=k, reverse=True)
    KEEP = 30
    import os
    fdir = f"{OUT}/../docs/filings" if not os.path.isdir("docs") else "docs/filings"
    os.makedirs(fdir, exist_ok=True)
    keep_accs = set()
    articles_dir = os.path.join(OUT, "articles")
    pinned = set()
    if os.path.isdir(articles_dir):
        pinned = {f[:-5] for f in os.listdir(articles_dir) if f.endswith(".json")}
    keep_accs |= pinned
    # Pinned filings that fell out of this run's search results are re-inserted
    # from the previous ferc.json so their article pages never 404.
    prev_path = os.path.join(OUT, "ferc.json")
    if os.path.exists(prev_path):
        try:
            prev = json.load(open(prev_path))
            have = {(it.get("accession") or "").strip() for it in items}
            for it in prev.get("items", []):
                acc = (it.get("accession") or "").strip()
                if acc in pinned and acc not in have:
                    items.append(it)
        except Exception as e:
            print(f"  prev ferc.json merge failed: {e}", file=sys.stderr)
    # Mirror the recent global slice plus every filing in product-critical dockets.
    mirror_items = []
    seen_mirror = set()
    for it in items[:KEEP] + [x for x in items if (x.get("accession") or "").strip() in pinned] + [x for x in items if any((d or "").rsplit("-",1)[0] == dk for d in (x.get("dockets") or []) for dk in HOT_DOCKETS)]:
        acc0 = (it.get("accession") or "").strip()
        if not acc0 or acc0 in seen_mirror: continue
        seen_mirror.add(acc0); mirror_items.append(it)
    for it in mirror_items:
        acc = (it.get("accession") or "").strip()
        fid = it.get("file_id")
        if not acc or not fid: continue
        # P8 returns only the selected transmittal. Do not spend a request on
        # intervention text or DOCX attachments that cannot render in PDF.js.
        if not (it.get("file_name") or "").lower().endswith(".pdf"): continue
        keep_accs.add(acc)
        dest = f"{fdir}/{acc}.pdfdata"
        if os.path.exists(dest) and os.path.getsize(dest) > 10000:
            it["doc_local"] = f"filings/{acc}.pdf"; continue
        if (it.get("file_size") or 0) > 15_000_000:
            print(f"  skip large PDF {acc} ({it['file_size']/1e6:.0f} MB)", file=sys.stderr); continue
        try:
            pdf = fetch("https://elibrary.ferc.gov/eLibrarywebapi/api/File/DownloadP8File",
                        data=json.dumps({"fileidLst":[fid]}).encode(),
                        headers={"Content-Type":"application/json"}, timeout=120)
            if pdf[:5] == b"%PDF-":
                with open(dest,"wb") as fh: fh.write(pdf)
                it["doc_local"] = f"filings/{acc}.pdf"
            else:
                print(f"  non-PDF response for {acc}", file=sys.stderr)
        except Exception as e:
            print(f"  pdf {acc}: {e}", file=sys.stderr)
    # Mirrors are append-only. A rolling search window is not proof that an
    # older core filing should disappear from the static evidence store.
    out = {"source": {"name": "FERC eLibrary General Search", "keyword": "data center",
                      "window_days": days, "url": "https://elibrary.ferc.gov/eLibrary/search"},
           "total_hits": res.get("totalHits"), "items": items}
    with open(f"{OUT}/ferc.json","w") as f: json.dump(clean(out), f, separators=(",",":"), allow_nan=False)
    print(f"  ferc.json: {len(items)} filings (window total {res.get('totalHits')})")

if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)
    try:
        month = build_battery()
    except Exception as e:
        # A source-side denial must not prevent independent FERC refreshes or
        # erase the last verified monthly inventory.
        print(f"  EIA refresh degraded; preserving prior battery.json: {e}", file=sys.stderr)
        try:
            month = json.load(open(f"{OUT}/meta.json")).get("eia_file_month") or "last verified snapshot"
        except Exception:
            month = "last verified snapshot"
    build_ferc()
    import subprocess
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "build_docket_views.py")], check=True)
    meta = {"generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "eia_file_month": month,
            "sources": ["https://www.eia.gov/electricity/data/eia860m/",
                        "https://elibrary.ferc.gov/eLibrary/search"]}
    with open(f"{OUT}/meta.json","w") as f: json.dump(meta, f, indent=1)
    print("done.")
