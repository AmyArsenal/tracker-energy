"""Canonical document store for tracker.energy.

Pipeline-side SQLite. One transactional file is the source of truth for every
document we ingest, across all sources (FERC, PUCs, ISOs, ...). The static
site's JSON feeds are *derived views* of this store, never the reverse.

Design rules (per product steering, 2026-09-10):
- Accuracy over volume: every row carries provenance (source system, source
  URL, fetched_at) and a confidence marker; validation gates run before publish.
- Replaceable boundary: all access goes through the functions here. The schema
  (dedupe keys, provenance, taxonomy) is engine-neutral and migrates to
  Postgres unchanged if the serving layer ever moves server-side.
- Controlled taxonomy: tags come from a fixed vocabulary (taxonomy.py), applied
  deterministically and auditable, never free-form.
"""
import json, os, sqlite3, sys
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "canonical", "tracker.db")

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS sources (
  source_id     TEXT PRIMARY KEY,      -- 'ferc', 'va-scc', 'caiso', 'ercot', ...
  name          TEXT NOT NULL,
  kind          TEXT NOT NULL,          -- 'federal'|'state-puc'|'iso'
  jurisdiction  TEXT NOT NULL,          -- 'US'|'VA'|'CAISO'|...
  base_url      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dockets (
  docket_id     TEXT PRIMARY KEY,      -- 'ferc:ER26-3515' | 'va-scc:PUR-2026-00018'
  source_id     TEXT NOT NULL REFERENCES sources(source_id),
  number        TEXT NOT NULL,          -- 'ER26-3515'
  caption       TEXT,
  status        TEXT,                   -- as the source states it, verbatim
  opened_date   TEXT,                   -- ISO YYYY-MM-DD when known
  url           TEXT NOT NULL,          -- canonical public URL of the docket
  UNIQUE(source_id, number)
);
CREATE TABLE IF NOT EXISTS documents (
  doc_id        TEXT PRIMARY KEY,      -- 'ferc:20260903-5199' | 'va-scc:PUR-2026-00018:<filingId>'
  source_id     TEXT NOT NULL REFERENCES sources(source_id),
  docket_id     TEXT REFERENCES dockets(docket_id),
  filed_date    TEXT,                   -- ISO YYYY-MM-DD, normalized
  title         TEXT NOT NULL,          -- filing description / document title
  doc_class     TEXT,                   -- source's own class: 'Intervention', 'Pleading/Motion', ...
  doc_type      TEXT,                   -- our controlled type (taxonomy.py)
  party         TEXT,                   -- filing party / author, verbatim
  url           TEXT NOT NULL,          -- authoritative source URL
  local_path    TEXT,                   -- hosted copy path if we mirror it
  fetched_at    TEXT NOT NULL,          -- ISO timestamp of ingest
  content       TEXT,                   -- extracted full text when available
  content_status TEXT NOT NULL DEFAULT 'none', -- 'none'|'metadata-only'|'full-text'
  confidence    TEXT NOT NULL DEFAULT 'high',  -- 'high'|'medium'|'low' + note via validation_log
  UNIQUE(source_id, doc_id)
);
CREATE TABLE IF NOT EXISTS tags (
  tag_id        TEXT PRIMARY KEY        -- controlled vocabulary, e.g. 'topic:large-load'
);
CREATE TABLE IF NOT EXISTS document_tags (
  doc_id        TEXT NOT NULL REFERENCES documents(doc_id),
  tag_id        TEXT NOT NULL REFERENCES tags(tag_id),
  rule          TEXT NOT NULL,          -- which tagging rule fired (auditability)
  PRIMARY KEY (doc_id, tag_id)
);
CREATE TABLE IF NOT EXISTS fetch_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id     TEXT NOT NULL,
  ran_at        TEXT NOT NULL,
  status        TEXT NOT NULL,          -- 'ok'|'degraded'|'failed'
  detail        TEXT
);
CREATE TABLE IF NOT EXISTS validation_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  ran_at        TEXT NOT NULL,
  doc_id        TEXT,
  level         TEXT NOT NULL,          -- 'error'|'warn'|'info'
  message       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_docs_filed ON documents(filed_date DESC);
CREATE INDEX IF NOT EXISTS idx_docs_docket ON documents(docket_id);
"""

def connect(path=None):
    db = sqlite3.connect(path or DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db

def iso_date(mmddyyyy):
    """'09/03/2026' -> '2026-09-03'; pass through ISO; else None."""
    if not mmddyyyy: return None
    s = mmddyyyy.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try: return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError: pass
    return None

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def upsert_source(db, source_id, name, kind, jurisdiction, base_url):
    db.execute("""INSERT INTO sources VALUES (?,?,?,?,?)
                  ON CONFLICT(source_id) DO UPDATE SET
                    name=excluded.name, kind=excluded.kind,
                    jurisdiction=excluded.jurisdiction, base_url=excluded.base_url""",
               (source_id, name, kind, jurisdiction, base_url))

def upsert_docket(db, source_id, number, caption, status, opened_date, url):
    did = f"{source_id}:{number}"
    db.execute("""INSERT INTO dockets VALUES (?,?,?,?,?,?,?)
                  ON CONFLICT(docket_id) DO UPDATE SET
                    caption=COALESCE(excluded.caption, dockets.caption),
                    status=COALESCE(excluded.status, dockets.status),
                    opened_date=COALESCE(excluded.opened_date, dockets.opened_date),
                    url=excluded.url""",
               (did, source_id, number, caption, status, iso_date(opened_date), url))
    return did

def upsert_document(db, source_id, doc_key, *, docket_id=None, filed_date=None,
                    title, doc_class=None, doc_type=None, party=None,
                    url, local_path=None, content=None,
                    content_status='none', confidence='high'):
    doc_id = f"{source_id}:{doc_key}"
    db.execute("""INSERT INTO documents
                    (doc_id, source_id, docket_id, filed_date, title, doc_class,
                     doc_type, party, url, local_path, fetched_at, content,
                     content_status, confidence)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                  ON CONFLICT(doc_id) DO UPDATE SET
                    docket_id=COALESCE(excluded.docket_id, documents.docket_id),
                    filed_date=COALESCE(excluded.filed_date, documents.filed_date),
                    title=excluded.title,
                    doc_class=COALESCE(excluded.doc_class, documents.doc_class),
                    doc_type=COALESCE(excluded.doc_type, documents.doc_type),
                    party=COALESCE(excluded.party, documents.party),
                    url=excluded.url,
                    local_path=COALESCE(excluded.local_path, documents.local_path),
                    fetched_at=excluded.fetched_at,
                    content=COALESCE(excluded.content, documents.content),
                    content_status=excluded.content_status,
                    confidence=excluded.confidence""",
               (doc_id, source_id, docket_id, iso_date(filed_date), title,
                doc_class, doc_type, party, url, local_path, now_iso(), content,
                content_status, confidence))
    return doc_id

def log_fetch(db, source_id, status, detail=None):
    db.execute("INSERT INTO fetch_log (source_id, ran_at, status, detail) VALUES (?,?,?,?)",
               (source_id, now_iso(), status, detail))

def log_validation(db, level, message, doc_id=None):
    db.execute("INSERT INTO validation_log (ran_at, doc_id, level, message) VALUES (?,?,?,?)",
               (now_iso(), doc_id, level, message))

def validate(db):
    """Pre-publish gates. Returns (errors, warns). Errors block publish."""
    errors, warns = [], []
    for r in db.execute("""SELECT doc_id, title, filed_date, url FROM documents
                           WHERE filed_date IS NULL"""):
        warns.append(f"no filed_date: {r['doc_id']} ({r['title'][:60]})")
    for r in db.execute("""SELECT doc_id FROM documents GROUP BY doc_id
                           HAVING COUNT(*)>1"""):
        errors.append(f"duplicate doc_id: {r['doc_id']}")
    for r in db.execute("""SELECT d.doc_id, d.filed_date FROM documents d
                           WHERE d.filed_date > date('now','+1 day')
                             AND d.doc_id NOT IN (SELECT doc_id FROM document_tags
                                                  WHERE tag_id='type:meeting')"""):
        warns.append(f"future filed_date: {r['doc_id']} {r['filed_date']}")
    for r in db.execute("""SELECT d.doc_id FROM documents d
                           LEFT JOIN document_tags t ON t.doc_id=d.doc_id
                           WHERE t.doc_id IS NULL"""):
        warns.append(f"untagged: {r['doc_id']}")
    for lvl, msg in [("error", m) for m in errors] + [("warn", m) for m in warns]:
        log_validation(db, lvl, msg)
    return errors, warns
