"""PJM stakeholder-document pipeline (weekly, per scraping guardrail).

Ingests PJM's official per-committee RSS feeds (sanctioned automated channel;
robots.txt disallows only /Calendar Events/ and admin paths) plus a polite
link-parse of the CIFP-RBP landing page (the large-load fast-path group, which
has no RSS feed). Emits docs/data/pjm.json; build_canonical.py ingests it into
the canonical store. Downloads agenda/minutes PDFs for topic-relevant meetings,
size-gated, hosted as .pdfdata (surge 404s .pdf on free tier).
"""
import json, os, re, sys, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(__file__))
from taxonomy import classify

DOCS = os.path.join(os.path.dirname(__file__), "..", "docs")
DATA = os.path.join(DOCS, "data")
FDIR = os.path.join(DOCS, "filings")

FEEDS = {
  # abbr: (feed path, committee display name)
  "mc":  ("committees/mc",  "Members Committee"),
  "mrc": ("committees/mrc", "Markets and Reliability Committee"),
  "mic": ("committees/mic", "Market Implementation Committee"),
  "pc":  ("committees/pc",  "Planning Committee"),
  "oc":  ("committees/oc",  "Operating Committee"),
  "raas":("subcommittees/raas", "Resource Adequacy Analysis Subcommittee"),
}
CIFP_URL = "https://www.pjm.com/committees-and-groups/cifp-rbp"
CIFP_NAME = "Critical Issue Fast Path - Reliability Backstop Procurement"
RELEVANT_TOPICS = {"topic:large-load", "topic:interconnection", "topic:storage",
                   "topic:capacity", "topic:transmission"}
MAX_PDF = 15_000_000
UA = {"User-Agent": "Mozilla/5.0 (compatible; tracker.energy research bot; weekly)"}

def fetch(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", errors="ignore")

def meeting_date(link, pubdate):
    m = re.search(r"/(\d{8})/", link or "")
    if m:
        d = m.group(1)
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    try:
        return parsedate_to_datetime(pubdate).strftime("%Y-%m-%d")
    except Exception:
        return None

def doc_label(title):
    t = (title or "").lower()
    for k in ("agenda", "minutes", "presentation", "materials", "recording",
              "webex", "notice", "minutes draft"):
        if k in t: return k.replace("webex", "recording")
    return "document"

def parse_feed(abbr, path, cname):
    url = f"https://www.pjm.com/committees-and-groups/{path}.aspx?Committees=All&rss=1"
    xml = fetch(url)
    root = ET.fromstring(xml.encode())
    docs = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = it.findtext("pubDate") or ""
        desc = (it.findtext("description") or "").strip()
        if not link: continue
        docs.append({
            "committee": abbr, "committee_name": cname,
            "title": f"{cname} - {title}" if cname.lower() not in title.lower() else title,
            "label": doc_label(title),
            "url": link, "posted": pub,
            "date": meeting_date(link, pub),
            "desc": desc,
        })
    return docs

def parse_cifp():
    html = fetch(CIFP_URL)
    docs = []
    seen = set()
    for m in re.finditer(r'href="(/-/media/DotCom/committees-groups/cifp-rbp/[^"]+\.pdf)"', html, re.I):
        path = m.group(1)
        if path in seen: continue
        seen.add(path)
        slug = path.rsplit("/", 1)[-1]
        label = re.sub(r"[-_]+", " ", slug[:-4]).strip()
        docs.append({
            "committee": "cifp-rbp", "committee_name": CIFP_NAME,
            "title": f"{CIFP_NAME} - {label}",
            "label": doc_label(label),
            "url": "https://www.pjm.com" + path, "posted": None,
            "date": meeting_date(path, None) or (re.search(r"(\d{8})", slug) and
                (lambda d: f"{d[:4]}-{d[4:6]}-{d[6:8]}")(re.search(r"(\d{8})", slug).group(1))),
            "desc": None,
        })
    return docs

if __name__ == "__main__":
    all_docs, errors = [], []
    for abbr, (path, cname) in FEEDS.items():
        try:
            docs = parse_feed(abbr, path, cname)
            all_docs += docs
            print(f"  {abbr}: {len(docs)} items")
        except Exception as e:
            errors.append(f"{abbr}: {e}")
            print(f"  {abbr}: FAILED {e}", file=sys.stderr)
    try:
        cifp = parse_cifp()
        all_docs += cifp
        print(f"  cifp-rbp: {len(cifp)} documents")
    except Exception as e:
        errors.append(f"cifp-rbp: {e}")
        print(f"  cifp-rbp: FAILED {e}", file=sys.stderr)

    # dedupe by URL
    seen, docs = set(), []
    for d in all_docs:
        if d["url"] in seen: continue
        seen.add(d["url"]); docs.append(d)

    # keep the most recent ~250 by date for the shard; PDFs only for
    # topic-relevant meetings (accuracy focus: large load / interconnection etc.)
    docs.sort(key=lambda d: d.get("date") or "", reverse=True)
    docs = docs[:250]
    os.makedirs(FDIR, exist_ok=True)
    kept = 0
    for d in docs:
        tags = classify(f"{d['title']} {d.get('desc') or ''}", None)
        d["topics"] = [t[6:] for t, _ in tags if t.startswith("topic:")]
        topic_ids = {t for t, _ in tags if t.startswith("topic:")}
        if d["label"] in ("agenda", "minutes", "minutes draft") and topic_ids & RELEVANT_TOPICS:
            m = re.search(r"/([^/]+\.pdf)$", d["url"], re.I)
            if m:
                dest = os.path.join(FDIR, f"pjm-{d['committee']}-{m.group(1)}data")
                if not (os.path.exists(dest) and os.path.getsize(dest) > 5000):
                    try:
                        pdf = fetch(d["url"], binary=True)
                        if pdf[:5] == b"%PDF-" and len(pdf) <= MAX_PDF:
                            open(dest, "wb").write(pdf)
                        else:
                            continue
                    except Exception:
                        continue
                d["doc_local"] = f"filings/pjm-{d['committee']}-{m.group(1)}data"
                kept += 1
    out = {
        "source": "PJM official per-committee RSS feeds + CIFP-RBP postings page",
        "refreshed_at": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "committees": {a: c for a, (p, c) in FEEDS.items()} | {"cifp-rbp": CIFP_NAME},
        "errors": errors,
        "documents": docs,
    }
    os.makedirs(DATA, exist_ok=True)
    json.dump(out, open(os.path.join(DATA, "pjm.json"), "w"), separators=(",", ":"))
    print(f"pjm.json: {len(docs)} documents, {kept} PDFs hosted, errors={errors}")
