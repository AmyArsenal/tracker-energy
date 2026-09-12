#!/usr/bin/env python3
"""ISO stakeholder meeting tracker - nightly refresh.
Sources: CAISO /resources/calendar.json, ERCOT /calendar HTML. -> docs/data/iso.json"""
import json, re, os, sys, urllib.request, datetime, html as htmlmod

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "iso.json")
UA = {"User-Agent": "Mozilla/5.0 (tracker.energy research bot)"}
TOPICS = [
    ("large load / data centers", re.compile(r"large load|data cent|co-?locat|large flexible|high impact load", re.I)),
    ("interconnection", re.compile(r"interconnect|generator interconnection|queue|GIAP|cluster study", re.I)),
    ("planning / transmission", re.compile(r"planning|transmission|RPG|regional planning|network upgrade|RTEP", re.I)),
    ("capacity / resource adequacy", re.compile(r"capacity|resource adequacy|RA |accreditation|reliability must.run", re.I)),
    ("markets", re.compile(r"market|auction|pricing|settlement|credit", re.I)),
    ("reliability / operations", re.compile(r"reliab|operations|outage|blackstart|EMS|SCADA|training", re.I)),
    ("governance", re.compile(r"board of governors|board of directors|governing body|annual meeting of members|budget", re.I)),
]

def tags(text):
    return [t for t, rx in TOPICS if rx.search(text or "")] or ["general"]

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=60).read()

def caiso(days=60):
    start = datetime.date.today().isoformat()
    end = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
    raw = json.loads(fetch(f"https://www.caiso.com/resources/calendar.json?start={start}&end={end}"))
    out = []
    for e in raw:
        if e.get("hidden") or e.get("isoArchived"): continue
        txt = " ".join([e.get("title") or "", e.get("description") or "", " ".join(e.get("tags") or []),
                        " ".join(t.get("name","") if isinstance(t,dict) else str(t) for t in (e.get("calendarTopics") or []))])
        out.append({
            "iso": "CAISO", "name": htmlmod.unescape(e.get("title","")).strip(),
            "start": e.get("start"), "end": e.get("end"),
            "location": (e.get("location") or "").strip() or None,
            "url": e.get("url"),
            "topics": tags(txt),
        })
    return out

MONTHS = {m: i+1 for i, m in enumerate(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"])}

def ercot():
    raw = fetch("https://www.ercot.com/calendar").decode("utf-8", "ignore")
    out = []
    # split on day headers
    parts = re.split(r'<div class="subtitle1[^>]*>([^<]+)</div>', raw)
    # parts[0] preamble, then alternating (date, body)
    for i in range(1, len(parts) - 1, 2):
        m = re.match(r"\w+, (\w+) (\d+), (\d+)", parts[i].strip())
        if not m: continue
        day = f"{m.group(3)}-{MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d}"
        body = parts[i+1]
        for mm in re.finditer(
            r'<a href="(https://www\.ercot\.com/calendar/[^"]+)" title="([^"]*)">\s*(.*?)\s*</a>.*?'
            r'(?:<span>([^<]*)</span>)?.*?<span class="startTime">([^<]*)</span>', body, re.S):
            url, group, name, loc, t = mm.groups()
            name = htmlmod.unescape(re.sub(r"\s+", " ", name)).strip()
            group = htmlmod.unescape(group).strip()
            out.append({
                "iso": "ERCOT", "name": name, "group": group or None,
                "start": f"{day}T{t.strip()}", "end": None,
                "tz": "US/Central",
                "location": (loc or "").strip() or None,
                "url": url, "topics": tags(f"{name} {group}"),
            })
    return out

def main():
    events = []
    for name, fn in [("CAISO", caiso), ("ERCOT", ercot)]:
        try:
            got = fn()
            events += got
            print(f"  {name}: {len(got)} meetings")
        except Exception as e:
            print(f"  {name}: FAILED - {e}", file=sys.stderr)
    events.sort(key=lambda e: e.get("start") or "")
    data = {
        "source": "ISO public meeting calendars (CAISO calendar.json, ERCOT calendar)",
        "refreshed_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "coverage": {"live": ["CAISO", "ERCOT"], "coming": ["PJM", "MISO", "SPP", "NYISO", "ISO-NE"]},
        "events": events,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, "w"), separators=(",", ":"))
    print(f"  iso.json: {len(events)} meetings")

if __name__ == "__main__":
    main()
