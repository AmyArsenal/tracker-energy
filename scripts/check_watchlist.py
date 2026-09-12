"""Watchlist diff for agentic alerts. Run nightly after build_canonical.py.

Prints one line per new document (filed/posted yesterday or today) that lands
in a watched docket or carries a watched topic. Empty output = stay silent.
Deduplicates against the last-seen marker in canonical/.watchlist_seen.json.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import canonical

ROOT = os.path.join(os.path.dirname(__file__), "..")
SEEN = os.path.join(ROOT, "canonical", ".watchlist_seen.json")

if __name__ == "__main__":
    wl = json.load(open(os.path.join(ROOT, "watchlist.json")))
    try: seen = set(json.load(open(SEEN)))
    except Exception: seen = set()
    db = canonical.connect()
    rows = db.execute("""
        SELECT d.doc_id, d.title, d.filed_date, d.source_id, d.url,
               dk.number AS docket,
               (SELECT group_concat(tag_id) FROM document_tags t
                 WHERE t.doc_id=d.doc_id AND t.tag_id LIKE 'topic:%') AS topics
        FROM documents d LEFT JOIN dockets dk ON dk.docket_id=d.docket_id
        WHERE d.filed_date >= date('now','-1 day')
    """).fetchall()
    hits, new_seen = [], set(seen)
    for r in rows:
        if r["doc_id"] in seen: continue
        new_seen.add(r["doc_id"])
        topics = [t[6:] for t in (r["topics"] or "").split(",") if t]
        in_docket = r["docket"] and any(w in r["docket"] for w in wl.get("dockets", []))
        in_topic = any(t in wl.get("topics", []) for t in topics)
        if in_docket or in_topic:
            why = f"docket {r['docket']}" if in_docket else "topic " + "/".join(t for t in topics if t in wl.get("topics", []))
            hits.append(f"[{r['source_id']}] {r['title'][:110]} ({why}, {r['filed_date']}) {r['url']}")
    json.dump(sorted(new_seen), open(SEEN, "w"))
    for h in hits[:15]: print(h)
    if len(hits) > 15: print(f"...and {len(hits)-15} more")
