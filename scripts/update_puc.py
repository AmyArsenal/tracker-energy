#!/usr/bin/env python3
"""PUC tracker - nightly refresh. v1: VA SCC (live), GA PSC (when its search backend is up).
TX/OH blocked at WAF for server-side fetch - coming via browser-scrape path (weekly, pending plan approval)."""
import json, os, re, sys, urllib.request, urllib.parse, datetime

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "puc.json")
UA = {"User-Agent": "Mozilla/5.0 (tracker.energy research bot)"}
DAYS = 45
KEYWORDS = ["data center", "large load", "interconnection"]

TOPICS = [
    ("large load / data centers", re.compile(r"data cent|large load|co-?locat", re.I)),
    ("interconnection", re.compile(r"interconnect|queue|transmission service", re.I)),
    ("rates / tariffs", re.compile(r"rate|tariff|rider|cost recovery", re.I)),
    ("certificates / siting", re.compile(r"certificat|siting|CPCN", re.I)),
]

def tags(text):
    return [t for t, rx in TOPICS if rx.search(text or "")] or ["general"]

def get(url, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={**UA, "Referer": "https://www.scc.virginia.gov/docketsearch"})
    return urllib.request.urlopen(req, timeout=60).read()

def virginia():
    """VA SCC DocketSearch keyword API -> aggregate documents by docket."""
    end = datetime.date.today()
    start = end - datetime.timedelta(days=DAYS)
    dockets = {}
    for kw in KEYWORDS:
        params = {"keyword": kw, "keyword2": "", "keywordPrefix": "1", "rowStart": "1",
                  "value": "5", "numberRecords": "100", "sort": "20", "sortDir": "1",
                  "caseNum": "", "caseName": "", "docNum": "", "docName": "",
                  "fromDate": start.strftime("%m/%d/%Y"), "toDate": end.strftime("%m/%d/%Y"),
                  "caption": "", "caseType": "", "section": ""}
        raw = get("https://www.scc.virginia.gov/docketsearch/home/filterpdfsearch", params)
        data = json.loads(raw)
        recs = data.get("Records") or []
        for r in recs:
            m = (r.get("Matter_ID") or "").strip()
            if not m or not m.startswith("PUR"):  # utility division only
                continue
            d = dockets.setdefault(m, {"state": "VA", "docket": m, "docs": [], "kw": set(),
                                       "url": f"https://www.scc.virginia.gov/docketsearch#/caseDetails/{m}"})
            d["kw"].add(kw)
            d["docs"].append({"type": r.get("DocType"), "name": (r.get("DocName") or "")[:200],
                              "docnum": r.get("DocNum")})
    import time
    details = {}
    for m in dockets:
        details[m] = va_case_details(m)
        time.sleep(0.3)
    out = []
    for m, d in dockets.items():
        names = " ".join(x["name"] or "" for x in d["docs"]) + " " + " ".join(d["kw"])
        # docket title: first doc name's leading party, trimmed
        det = details.get(m) or {}
        title = re.sub(r"\s+", " ", (det.get("caption") or d["docs"][0]["name"] or "")).strip()[:160]
        out.append({"state": "VA", "docket": m, "title": title,
                    "status": det.get("status"), "established": det.get("established"),
                    "recent_docs": len(d["docs"]),
                    "doc_types": sorted({x["type"] for x in d["docs"] if x["type"]})[:4],
                    "matched": sorted(d["kw"]),
                    "topics": tags(names), "url": d["url"]})
    out.sort(key=lambda x: -x["recent_docs"])
    return out

def georgia():
    """GA PSC facts-service - backend returns nulls during its (current) outage; degrade gracefully."""
    try:
        params = {"q": "data center", "limit": "25", "type": "Docket OR Document",
                  "industry": "Electric", "status": "Any", "date": "Any",
                  "fromDate": "", "toDate": "", "isPublic": "true",
                  "sortColumn": "", "sortDirection": "", "pageNumber": "1", "pageSize": "25"}
        raw = get("https://psc.ga.gov/search/facts-service/", params)
        data = json.loads(raw)
        items = data.get("resultsItems") or []
        out = []
        for r in items:
            out.append({"state": "GA", "docket": str(r.get("id")), "title": (r.get("title") or "")[:140],
                        "recent_docs": None, "doc_types": [], "matched": ["data center"],
                        "topics": tags(r.get("title") or ""), 
                        "url": f"https://psc.ga.gov/search/facts-docket/?docketId={r.get('id')}"})
        return out, None if items else "GA search backend returned no data (site-side outage observed 10 Sep 2026)"
    except Exception as e:
        return [], f"GA fetch failed: {e}"

def va_case_details(case_number):
    """Real caption/status for a VA docket via the SCC breeze API."""
    try:
        params = {"$filter": f"Case_Number eq '{case_number}'",
                  "$select": "Case_Number,Case_Name,Caption,Status,Case_Established_Date,Final_Order_Date,Closed_Date"}
        raw = get("https://www.scc.virginia.gov/docketsearchapi/breeze/casedetails/getdetail", params)
        rows = json.loads(raw)
        if rows:
            r = rows[0]
            return {"caption": r.get("Caption"), "status": r.get("Status"),
                    "established": r.get("Case_Established_Date")}
    except Exception:
        pass
    return {}

def main():
    dockets, notes = [], []
    va = virginia()
    dockets += va
    print(f"  VA: {len(va)} dockets")
    ga, note = georgia()
    dockets += ga
    print(f"  GA: {len(ga)} dockets {note or ''}")
    if note: notes.append(note)
    data = {
        "source": "State PUC docket search (VA SCC DocketSearch API; GA PSC facts-service)",
        "window_days": DAYS,
        "refreshed_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "coverage": {"live": [s for s in ["VA","GA"] if any(d["state"]==s for d in dockets)],
                     "degraded": (["GA"] if note else []),
                     "coming": ["TX", "OH"]},
        "notes": notes,
        "dockets": dockets,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, "w"), separators=(",", ":"))
    print(f"  puc.json: {len(dockets)} dockets")

if __name__ == "__main__":
    main()
