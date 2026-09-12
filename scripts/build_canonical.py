"""Build the canonical document store from the current source feeds.

Ingests the existing derived JSONs (ferc.json, puc.json, iso.json) into the
SQLite canonical store with dedupe, provenance, taxonomy tags, and validation.
The derived JSONs stay the site's serving format for now; this store becomes
the source of truth they are generated from in the next phase.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import canonical
from taxonomy import classify, TAGS

DOCS = os.path.join(os.path.dirname(__file__), "..", "docs")
DATA = os.path.join(DOCS, "data")

def seed_tags(db):
    for tag_id in TAGS:
        db.execute("INSERT OR IGNORE INTO tags VALUES (?)", (tag_id,))

def apply_tags(db, doc_id, tags):
    db.execute("DELETE FROM document_tags WHERE doc_id=?", (doc_id,))
    for tag_id, rule in tags:
        db.execute("INSERT OR IGNORE INTO document_tags VALUES (?,?,?)", (doc_id, tag_id, rule))

def ingest_ferc(db):
    d = json.load(open(os.path.join(DATA, "ferc.json")))
    canonical.upsert_source(db, "ferc", "FERC eLibrary", "federal", "US",
                            "https://elibrary.ferc.gov/eLibrary/search")
    n = 0
    for it in d.get("items", []):
        acc = (it.get("accession") or "").strip()
        if not acc: continue
        docket_id = None
        dk = (it.get("dockets") or [None])[0]
        if dk:
            docket_id = canonical.upsert_docket(
                db, "ferc", dk, None, None, None,
                f"https://elibrary.ferc.gov/eLibrary/dockets?docket_number={dk}")
        doc_id = canonical.upsert_document(
            db, "ferc", acc, docket_id=docket_id,
            filed_date=it.get("filed"),
            title=it.get("summary") or it.get("description") or acc,
            doc_class=it.get("class"), party=it.get("author"),
            url=it.get("url") or f"https://elibrary.ferc.gov/eLibrary/docinfo?accession_number={acc}",
            local_path=it.get("doc_local"),
            content=it.get("description"),
            content_status="metadata-only",
            confidence="high" if it.get("doc_local") else "medium")
        tags = classify(f"{it.get('summary','')} {it.get('description','')}", it.get("class"))
        if any(t == "type:other" for t, _ in tags) and it.get("type"):
            tags = [(t, r) for t, r in tags if t != "type:other"] + classify(it["type"])
            seen = set(); tags = [x for x in tags if not (x[0] in seen or seen.add(x[0]))]
        # Known FERC large-load proceedings: explicit docket membership is
        # stronger than whether one filing repeats the phrase in its title.
        large_load_dockets = {"ER26-1323", "ER26-2249", "ER26-3265", "ER26-3380", "ER26-3515", "ER26-3525", "ER26-3552", "ER26-3591", "ER26-3650", "ER26-3685", "EL26-67", "EL26-68", "EL26-69", "EL26-70", "EL26-71", "EL26-72"}
        if any((d or '').rsplit('-', 1)[0] in large_load_dockets for d in it.get('dockets', [])) and not any(t == "topic:large-load" for t, _ in tags):
            tags.append(("topic:large-load", "topic:docket:large-load"))
        # Cross-tag official FERC activity that belongs to the MISO product lens.
        # The docket IDs are the current ZGIA and large-load reliability dockets;
        # text matching catches future MISO filings without misclassifying generic GIAs.
        hay = f"{it.get('summary','')} {it.get('description','')} {it.get('author','')}"
        miso_dockets = {"ER26-3552", "ER26-3650"}
        if any((d or '').split('-000')[0] in miso_dockets for d in it.get('dockets', [])) or \
           __import__('re').search(r'\b(MISO|Midcontinent Independent System Operator)\b', hay, __import__('re').I):
            tags.append(("entity:miso", "entity:docket-or-name:miso"))
        apply_tags(db, doc_id, tags)
        n += 1
    canonical.log_fetch(db, "ferc", "ok", f"{n} items ingested from ferc.json")
    return n

def ingest_puc(db):
    p = json.load(open(os.path.join(DATA, "puc.json")))
    canonical.upsert_source(db, "va-scc", "Virginia State Corporation Commission",
                            "state-puc", "VA", "https://www.scc.virginia.gov/docketsearch")
    n = 0
    for dk in p.get("dockets", []):
        if dk.get("state") != "VA": continue
        num = dk.get("docket")
        if not num: continue
        docket_id = canonical.upsert_docket(
            db, "va-scc", num, dk.get("title"), dk.get("status"),
            dk.get("established"),
            f"https://www.scc.virginia.gov/docketsearch#/caseDetails/{num}")
        doc_id = canonical.upsert_document(
            db, "va-scc", f"{num}:docket", docket_id=docket_id,
            filed_date=dk.get("established"),
            title=dk.get("title") or num,
            party=None,
            url=f"https://www.scc.virginia.gov/docketsearch#/caseDetails/{num}",
            content=None, content_status="metadata-only", confidence="medium")
        hay = f"{dk.get('title','')} {' '.join(dk.get('matched',[]))} {' '.join(dk.get('doc_types',[]))}"
        apply_tags(db, doc_id, classify(hay, None))
        n += 1
    degraded = p.get("coverage", {}).get("degraded", [])
    canonical.log_fetch(db, "va-scc", "ok", f"{n} dockets ingested")
    if degraded:
        canonical.log_fetch(db, "ga-psc", "degraded",
                            "; ".join(p.get("notes", [])) or "degraded per coverage")
    return n

def ingest_pjm(db):
    p = os.path.join(DATA, "pjm.json")
    if not os.path.exists(p): return 0
    d = json.load(open(p))
    canonical.upsert_source(db, "pjm", "PJM Interconnection", "iso", "PJM",
                            "https://www.pjm.com/committees-and-groups")
    n = 0
    for doc in d.get("documents", []):
        ab = doc.get("committee") or "pjm"
        docket_id = canonical.upsert_docket(
            db, "pjm", ab.upper(), doc.get("committee_name"), None, None,
            f"https://www.pjm.com/committees-and-groups/{'committees/' + ab if ab in ('mc','mrc','mic','pc','oc') else 'subcommittees/' + ab if ab == 'raas' else ab}")
        key = doc["url"].rstrip("/").rsplit("/", 1)[-1][:80]
        doc_id = canonical.upsert_document(
            db, "pjm", f"{ab}:{key}", docket_id=docket_id,
            filed_date=doc.get("date"),
            title=doc.get("title") or key, doc_class=doc.get("label"),
            party=doc.get("committee_name"),
            url=doc["url"], local_path=doc.get("doc_local"),
            content=doc.get("desc"), content_status="metadata-only",
            confidence="medium")
        tags = classify(f"{doc.get('title','')} {doc.get('desc') or ''}", doc.get("label"))
        tags = [(t, r) for t, r in tags if not t.startswith("type:")]
        tags.insert(0, ("type:meeting", "source-kind:pjm-committee-docs"))
        apply_tags(db, doc_id, tags)
        n += 1
    canonical.log_fetch(db, "pjm", "ok" if not d.get("errors") else "degraded",
                        f"{n} documents ingested; errors={d.get('errors')}")
    return n

def inherit_docket_topics(db):
    """Pass 2: docs tagged only topic:general inherit the non-general topics of
    their docket (docket membership is authoritative context; rule recorded as
    inherit:docket for auditability)."""
    n = 0
    # Committee containers (pjm) are too broad to inherit from - only real
    # regulatory dockets carry topic context.
    for r in db.execute("""SELECT DISTINCT d.docket_id FROM documents d
                           WHERE d.docket_id IS NOT NULL
                             AND d.source_id IN ('ferc','va-scc')"""):
        dk = r["docket_id"]
        docket_topics = [t["tag_id"] for t in db.execute(
            """SELECT DISTINCT tag_id FROM document_tags dt
               JOIN documents d2 ON d2.doc_id = dt.doc_id
               WHERE d2.docket_id=? AND tag_id LIKE 'topic:%'
                 AND tag_id != 'topic:general'""", (dk,))]
        if not docket_topics: continue
        for d in db.execute(
            """SELECT d.doc_id FROM documents d
               WHERE d.docket_id=? AND NOT EXISTS (
                 SELECT 1 FROM document_tags t WHERE t.doc_id=d.doc_id
                   AND t.tag_id LIKE 'topic:%' AND t.tag_id != 'topic:general')""",
            (dk,)):
            for t in docket_topics:
                db.execute("INSERT OR IGNORE INTO document_tags VALUES (?,?,?)",
                           (d["doc_id"], t, "inherit:docket"))
            db.execute("DELETE FROM document_tags WHERE doc_id=? AND tag_id='topic:general' AND rule='fallback:no-topic-signal'", (d["doc_id"],))
            n += 1
    return n

def ingest_miso(db):
    p = os.path.join(DATA, "miso.json")
    if not os.path.exists(p): return 0
    d = json.load(open(p))
    canonical.upsert_source(db, "miso", "Midcontinent Independent System Operator", "iso", "MISO",
                            d.get("source_url") or "https://www.misoenergy.org/engage/tools/calendar/")
    n = 0
    for ev in d.get("events", []):
        if not ev.get("url"): continue
        key = (ev.get("url") or ev.get("name","")).rstrip("/").rsplit("/",1)[-1][:100]
        doc_id = canonical.upsert_document(db, "miso", key,
            filed_date=(ev.get("start") or "")[:10], title=ev.get("name") or key,
            party=ev.get("group"), url=ev["url"], content_status="metadata-only", confidence="high")
        tags = classify(f"{ev.get('name','')} {ev.get('group','')}", None)
        tags = [(t,r) for t,r in tags if not t.startswith("type:")]
        tags.insert(0,("type:meeting","source-kind:miso-calendar"))
        tags.append(("entity:miso","source-entity:miso"))
        apply_tags(db,doc_id,tags); n += 1
    canonical.log_fetch(db,"miso","degraded" if d.get("errors") else "ok",
                        f"{n} meetings; errors={d.get('errors')}")
    return n

def ingest_iso(db):
    d = json.load(open(os.path.join(DATA, "iso.json")))
    canonical.upsert_source(db, "caiso", "California ISO", "iso", "CAISO", "https://www.caiso.com/")
    canonical.upsert_source(db, "ercot", "ERCOT", "iso", "ERCOT", "https://www.ercot.com/")
    n = 0
    for ev in d.get("events", []):
        iso = (ev.get("iso") or "").lower()
        if iso not in ("caiso", "ercot") or not ev.get("url"): continue
        key = ev["url"].rstrip("/").rsplit("/", 1)[-1][:80]
        doc_id = canonical.upsert_document(
            db, iso, key, filed_date=(ev.get("start") or "")[:10],
            title=ev.get("name") or key, party=ev.get("group"),
            url=ev["url"], content_status="metadata-only", confidence="medium")
        tags = classify(f"{ev.get('name','')} {ev.get('group','')}", None)
        tags = [(t, r) for t, r in tags if not t.startswith("type:")]
        tags.insert(0, ("type:meeting", "source-kind:iso-calendar"))
        apply_tags(db, doc_id, tags)
        n += 1
    canonical.log_fetch(db, "caiso+ercot", "ok", f"{n} meetings ingested")
    return n

if __name__ == "__main__":
    db = canonical.connect()
    seed_tags(db)
    counts = {"ferc": ingest_ferc(db), "puc": ingest_puc(db), "iso": ingest_iso(db),
              "pjm": ingest_pjm(db), "miso": ingest_miso(db)}
    inh = inherit_docket_topics(db)
    print(f"docket-inheritance applied to {inh} docs")
    errors, warns = canonical.validate(db)
    db.commit()
    total = db.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]
    tagged = db.execute("SELECT COUNT(DISTINCT doc_id) c FROM document_tags").fetchone()["c"]
    print(f"ingested: {counts}  store total: {total} docs ({tagged} tagged)")
    print(f"validation: {len(errors)} errors, {len(warns)} warns")
    for m in errors[:10]: print("  ERROR:", m)
    bytag = db.execute("""SELECT t.tag_id, COUNT(*) c FROM document_tags t
                          GROUP BY t.tag_id ORDER BY c DESC""").fetchall()
    for r in bytag: print(f"  {r['tag_id']:26s} {r['c']}")
