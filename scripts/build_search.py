"""Emit the static search shard (docs/data/search.json) from the canonical store.

One compact JSON the discovery page loads once: every document with its
facets and searchable text. Facets are precomputed from the controlled
taxonomy, so filtering is exact-match, not string guessing. At corpus scale
beyond ~25-50k docs this builder switches to pushing a server-side search
index instead (same records, different sink) - see architecture note.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import canonical
from taxonomy import TAGS

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "search.json")

if __name__ == "__main__":
    db = canonical.connect()
    rows = db.execute("""
        SELECT d.doc_id, d.source_id, s.name AS source_name, s.kind, s.jurisdiction,
               d.docket_id, dk.number AS docket_number, dk.caption,
               d.filed_date, d.title, d.doc_class, d.party, d.url, d.local_path,
               d.content, d.confidence, d.fetched_at
        FROM documents d
        JOIN sources s ON s.source_id = d.source_id
        LEFT JOIN dockets dk ON dk.docket_id = d.docket_id
    """).fetchall()
    tags = {}
    for r in db.execute("SELECT doc_id, tag_id FROM document_tags"):
        tags.setdefault(r["doc_id"], []).append(r["tag_id"])
    docs = []
    for r in rows:
        t = tags.get(r["doc_id"], [])
        docs.append({
            "id": r["doc_id"],
            "src": r["source_id"], "src_name": r["source_name"],
            "kind": r["kind"], "jur": r["jurisdiction"],
            "docket": r["docket_number"], "caption": r["caption"],
            "date": r["filed_date"], "title": r["title"],
            "class": r["doc_class"], "party": r["party"],
            "url": r["url"], "local": r["local_path"],
            "types": [x[5:] for x in t if x.startswith("type:")],
            "topics": [x[6:] for x in t if x.startswith("topic:")],
            "entities": [x[7:] for x in t if x.startswith("entity:")],
            "conf": r["confidence"],
            "rules": [x["rule"] for x in db.execute("SELECT rule FROM document_tags WHERE doc_id=?", (r["doc_id"],))],
            "text": " ".join(filter(None, [r["title"], r["caption"], r["party"],
                                           r["doc_class"], " ".join(x[7:] for x in t if x.startswith("entity:")),
                                           (r["content"] or "")[:4000]])).lower(),
        })
    facet_vocab = {"types": {k[5:]: v for k, v in TAGS.items() if k.startswith("type:")},
                   "topics": {k[6:]: v for k, v in TAGS.items() if k.startswith("topic:")}}
    json.dump({"built_at": canonical.now_iso(), "count": len(docs),
               "facets": facet_vocab, "docs": docs},
              open(OUT, "w"), separators=(",", ":"))
    # The Watch is the product-core lens, not a newest-everything feed.
    # Search keeps the complete corpus. Landing is intentionally sparse and is
    # split into consequential completed records and upcoming calendar events.
    CORE = {"large-load", "interconnection", "rates", "markets", "capacity",
            "reliability", "transmission", "storage"}
    def watch_eligible(d):
        topics = set(d["topics"])
        if not (topics & CORE): return False
        if "siting" in topics and not (topics & {"large-load", "interconnection"}): return False
        if "environmental" in topics and not (topics & (CORE - {"transmission"})): return False
        return True

    def plain_line(d):
        """Deterministic, source-grounded landing copy. Never infer a position.
        Specific party/action templates come first; unknown shapes return None
        and therefore rank below records that can be translated cleanly.
        """
        import re
        title = re.sub(r"<[^>]+>", " ", d.get("title") or "")
        title = re.sub(r"\s+", " ", title).strip()
        party = re.sub(r"\s+", " ", d.get("party") or "").strip()
        docket = (d.get("docket") or "").replace("-000", "")
        types = set(d.get("types") or [])
        topics = set(d.get("topics") or [])
        who = party or ({"ferc":"A filer", "va-scc":"A Virginia utility"}.get(d.get("src")) or d.get("src_name") or "This record")
        # Keep names human-sized without changing identity.
        who = re.sub(r",?\s+(LLC|L\.L\.C\.|Inc\.|Corporation|Company)$", "", who, flags=re.I)
        subject = None
        low = title.lower()
        if "zero injection" in low or docket == "ER26-3552":
            subject = "MISO's zero-injection interconnection proposal"
        elif "interim resource adequacy" in low or docket == "ER26-3515":
            subject = "PJM's data-center resource-adequacy fast track"
        elif docket == "ER26-3650" or ("large load" in low and "reliability" in low):
            subject = "MISO's reliability rules for connecting large loads"
        elif "large load ride through" in low:
            subject = "how large loads stay connected during grid disturbances"
        elif "large load" in low or "data center" in low:
            subject = "large-load grid connections"
        elif "interconnection" in low:
            subject = "grid interconnection rules"
        elif "transmission" in low:
            subject = "transmission planning"
        elif "storage" in low or "battery" in low:
            subject = "storage on the grid"
        elif "capacity" in low or "resource adequacy" in low:
            subject = "how the grid secures enough capacity"
        elif "reliability" in low or "frequency response" in low:
            subject = "grid reliability rules"
        elif "market" in low:
            subject = "wholesale-market rules"
        elif "tariff" in low or "rate" in low:
            subject = "the rates and rules for grid service"
        if "meeting" in types:
            group = party or re.sub(r"\s+-\s+.*$", "", title)
            if not subject: return None
            return f"{group} will take up {subject}."
        if not subject: return None
        if "order" in types and d.get("src") == "ferc": action = "FERC acts on"
        elif "protest" in types:
            action = f"{who} asks FERC to reject or change" if "reject" in low else f"{who} challenges"
        elif "comment" in types:
            if "in support" in low: action = f"{who} supports"
            elif "answer" in low: action = f"{who} responds on"
            else: action = f"{who} comments on"
        elif "application" in types or (d.get("src") == "va-scc" and "application" in low): action = f"{who} asks Virginia regulators to approve"
        elif "tariff" in types: action = f"{who} proposes changes to"
        elif "agreement" in types: action = f"{who} files an agreement covering"
        elif "report" in types: action = f"{who} reports on"
        else: return None
        return f"{action} {subject}."

    dated = [d for d in docs if d["date"]]
    eligible = [d for d in dated if watch_eligible(d)]
    from datetime import date, timedelta
    today = date.today().isoformat()
    substantive = {"order", "protest", "comment", "application", "tariff", "agreement", "report"}
    weight = {"order":0, "protest":1, "comment":2, "application":3,
              "tariff":4, "agreement":5, "report":6}
    filed_pool = []
    calendar_pool = []
    recent_cut = (date.today() - timedelta(days=21)).isoformat()
    for d in eligible:
        types = set(d["types"])
        d["plain"] = plain_line(d)
        if "meeting" in types:
            if d["date"] > today and d["plain"]: calendar_pool.append(d)
        elif d["date"] <= today and d["date"] >= recent_cut and types & substantive:
            # Bare interventions, notices and unclassifiable records never lead.
            filed_pool.append(d)
    # Known large-load dockets and staff-read articles are more important than
    # generic adjacent records; chronology breaks ties rather than overruling relevance.
    hot_dockets = {"ER26-3515", "ER26-3552", "ER26-3650", "ER26-3265"}
    article_ids = {"ferc:" + os.path.basename(x)[:-5] for x in __import__('glob').glob(
        os.path.join(os.path.dirname(OUT), "articles", "*.json"))}
    def importance(d):
        dk = (d.get("docket") or "").replace("-000", "")
        return (0 if dk in hot_dockets or d["id"] in article_ids else 1,
                0 if d["plain"] else 1,
                min((weight[t] for t in d["types"] if t in weight), default=99),
                -int(d["date"].replace("-", "")))
    filed_pool.sort(key=importance)
    calendar_pool.sort(key=lambda d: (d["date"], 0 if "large-load" in d["topics"] else 1,
                                      0 if "interconnection" in d["topics"] else 1))
    def balanced(pool, limit, venue_cap=4, dedupe_calendar=False):
        out, counts, seen = [], {}, set()
        for d in pool:
            if dedupe_calendar:
                sig = (d["src"], d.get("party") or d["title"], d["date"])
            else:
                sig = (d["src"], (d.get("party") or "").lower(),
                       (d.get("docket") or "").replace("-000", ""))
            if sig in seen: continue
            if counts.get(d["src"], 0) >= venue_cap: continue
            out.append(d); seen.add(sig); counts[d["src"]] = counts.get(d["src"], 0) + 1
            if len(out) == limit: break
        return out
    filed = balanced(filed_pool, 5, 4)
    calendar = balanced(calendar_pool, 3, 2, True)
    def item(d):
        return {"id":d["id"], "src":d["src"], "src_name":d["src_name"],
                "date":d["date"], "title":d["title"], "plain":d["plain"],
                "docket":d["docket"], "url":d["url"]}
    cut = (date.today() - timedelta(days=7)).isoformat()
    WOUT = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "watch.json")
    json.dump({"built_at": canonical.now_iso(),
               "stats": {"docs": len(docs), "venues": len({d["src"] for d in docs}),
                         "new_7d": sum(1 for d in eligible if d["date"] >= cut),
                         "eligible": len(eligible)},
               "filed": [item(d) for d in filed],
               "calendar": [item(d) for d in calendar]}, open(WOUT, "w"), indent=1)
    kb = os.path.getsize(OUT) // 1024
    print(f"search.json: {len(docs)} docs, {kb} KB")
    print(f"watch.json: {len(dated)} dated -> {len(eligible)} core-eligible; "
          f"{len(filed)} filed + {len(calendar)} calendar displayed")
