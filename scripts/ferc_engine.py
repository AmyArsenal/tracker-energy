#!/usr/bin/env python3
"""Incremental FERC eLibrary ingestion and page-position extraction.

This is the document-engine path, separate from the legacy static-feed adapter.
It can run against a bounded date slice before it is promoted to the nightly job.
Original components are content-addressed by SHA-256; SQLite stores state and
provenance, not opaque source blobs.
"""
from __future__ import annotations
import argparse, dataclasses, datetime as dt, hashlib, html, json, pathlib, re
import sqlite3, subprocess, time, urllib.error, urllib.request, uuid

SEARCH_URL="https://elibrary.ferc.gov/eLibrarywebapi/api/Search/AdvancedSearch"
DOWNLOAD_URL="https://elibrary.ferc.gov/eLibrarywebapi/api/File/DownloadP8File"
DOCINFO="https://elibrary.ferc.gov/eLibrary/docinfo?accession_number={}"
UA={"User-Agent":"tracker.energy-ferc-engine/1 (public data refresh; contact: site owner)"}

SCHEMA="""
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS ingest_runs(
 run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT,
 start_date TEXT NOT NULL, end_date TEXT NOT NULL, status TEXT NOT NULL,
 expected_hits INTEGER DEFAULT 0, pages_fetched INTEGER DEFAULT 0,
 accessions_seen INTEGER DEFAULT 0, components_seen INTEGER DEFAULT 0,
 components_downloaded INTEGER DEFAULT 0, components_extracted INTEGER DEFAULT 0,
 errors INTEGER DEFAULT 0, detail TEXT);
CREATE TABLE IF NOT EXISTS engine_state(key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ingest_pages(
 run_id TEXT NOT NULL REFERENCES ingest_runs(run_id), filed_date TEXT NOT NULL,
 page INTEGER NOT NULL, expected_hits INTEGER NOT NULL, hits_seen INTEGER NOT NULL,
 response_sha256 TEXT NOT NULL, fetched_at TEXT NOT NULL,
 PRIMARY KEY(run_id,filed_date,page));
CREATE TABLE IF NOT EXISTS ferc_documents(
 accession TEXT PRIMARY KEY, document_id TEXT, description TEXT, category TEXT,
 filed_date TEXT, issued_date TEXT, posted_date TEXT, document_class TEXT,
 document_type TEXT, availability TEXT, family_value TEXT, libraries_json TEXT NOT NULL,
 dockets_json TEXT NOT NULL, affiliations_json TEXT NOT NULL, official_url TEXT NOT NULL,
 raw_sha256 TEXT NOT NULL, first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ferc_components(
 component_id TEXT PRIMARY KEY, accession TEXT NOT NULL REFERENCES ferc_documents(accession),
 source_order INTEGER NOT NULL, file_type TEXT, file_format TEXT, filename TEXT,
 description TEXT, reported_bytes INTEGER, download_status TEXT NOT NULL DEFAULT 'pending',
 source_sha256 TEXT, object_path TEXT, downloaded_at TEXT, extraction_status TEXT NOT NULL DEFAULT 'pending',
 extraction_version TEXT, UNIQUE(accession,source_order));
CREATE TABLE IF NOT EXISTS pages(
 component_id TEXT NOT NULL REFERENCES ferc_components(component_id), page INTEGER NOT NULL,
 width REAL NOT NULL, height REAL NOT NULL, text TEXT NOT NULL, token_count INTEGER NOT NULL,
 extraction_method TEXT NOT NULL, extraction_confidence REAL NOT NULL,
 PRIMARY KEY(component_id,page));
CREATE TABLE IF NOT EXISTS tokens(
 component_id TEXT NOT NULL, page INTEGER NOT NULL, token_index INTEGER NOT NULL,
 text TEXT NOT NULL, x0 REAL NOT NULL, y0 REAL NOT NULL, x1 REAL NOT NULL, y1 REAL NOT NULL,
 char_start INTEGER NOT NULL, char_end INTEGER NOT NULL,
 PRIMARY KEY(component_id,page,token_index),
 FOREIGN KEY(component_id,page) REFERENCES pages(component_id,page));
CREATE TABLE IF NOT EXISTS passages(
 passage_id TEXT PRIMARY KEY, component_id TEXT NOT NULL, page_start INTEGER NOT NULL,
 page_end INTEGER NOT NULL, token_start INTEGER NOT NULL, token_end INTEGER NOT NULL,
 text TEXT NOT NULL, text_sha256 TEXT NOT NULL, extraction_method TEXT NOT NULL,
 FOREIGN KEY(component_id) REFERENCES ferc_components(component_id));
CREATE VIRTUAL TABLE IF NOT EXISTS passage_fts USING fts5(passage_id UNINDEXED, text, tokenize='unicode61');
CREATE TABLE IF NOT EXISTS evidence(
 evidence_id TEXT PRIMARY KEY, passage_id TEXT NOT NULL REFERENCES passages(passage_id),
 component_id TEXT NOT NULL, source_sha256 TEXT NOT NULL, extraction_version TEXT NOT NULL,
 kind TEXT NOT NULL, page_start INTEGER NOT NULL, page_end INTEGER NOT NULL,
 token_start INTEGER NOT NULL, token_end INTEGER NOT NULL, quote TEXT NOT NULL,
 boxes_json TEXT NOT NULL, method TEXT NOT NULL, confidence REAL NOT NULL,
 created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS engine_events(
 id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, at TEXT NOT NULL,
 level TEXT NOT NULL, subject TEXT, message TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_components_accession ON ferc_components(accession);
CREATE INDEX IF NOT EXISTS idx_docs_filed ON ferc_documents(filed_date,accession);
CREATE INDEX IF NOT EXISTS idx_passages_component ON passages(component_id,page_start);
"""

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(b:bytes): return hashlib.sha256(b).hexdigest()
def dbopen(path):
 p=pathlib.Path(path); p.parent.mkdir(parents=True,exist_ok=True)
 db=sqlite3.connect(p); db.row_factory=sqlite3.Row; db.executescript(SCHEMA); return db

def body(day:str,page:int,page_size:int=100):
 d=dt.date.fromisoformat(day).strftime('%m/%d/%Y')
 return {"searchText":"","searchFullText":True,"searchDescription":True,
  "dateSearches":[{"dateType":"filed_date","startDate":d,"endDate":d}],
  "availability":None,"affiliations":[],"categories":[],"libraries":[],
  "accessionNumber":None,"eFiling":False,"docketSearches":[],
  "resultsPerPage":page_size,"curPage":page,"classTypes":[],"sortBy":"",
  "groupBy":"NONE","idolResultID":"","allDates":False}

def request(url,payload,timeout=120,retries=3):
 data=json.dumps(payload,separators=(',',':')).encode()
 for attempt in range(retries):
  try:
   req=urllib.request.Request(url,data=data,headers={**UA,"Content-Type":"application/json"})
   with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()
  except (urllib.error.URLError,TimeoutError,ConnectionError):
   if attempt+1==retries: raise
   time.sleep(2**attempt)

def hitrow(h):
 c=(h.get('classTypes') or [{}])[0]
 return ((h.get('acesssionNumber') or '').strip(),h.get('documentId'),h.get('description'),h.get('category'),
 h.get('filedDate'),h.get('issuedDate'),h.get('postedDate'),c.get('documentClass'),c.get('documentType'),
 h.get('availCode'),h.get('familyValue'),json.dumps(h.get('libraries') or [],separators=(',',':')),
 json.dumps(h.get('docketNumbers') or [],separators=(',',':')),json.dumps(h.get('affiliations') or [],separators=(',',':')))

def ingest_hit(db,h,observed_at):
 vals=hitrow(h); acc=vals[0]
 if not acc:return 0
 raw_hash=sha(json.dumps(h,sort_keys=True,separators=(',',':')).encode())
 db.execute("""INSERT INTO ferc_documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
 ON CONFLICT(accession) DO UPDATE SET document_id=excluded.document_id,description=excluded.description,
 category=excluded.category,filed_date=excluded.filed_date,issued_date=excluded.issued_date,
 posted_date=excluded.posted_date,document_class=excluded.document_class,document_type=excluded.document_type,
 availability=excluded.availability,family_value=excluded.family_value,libraries_json=excluded.libraries_json,
 dockets_json=excluded.dockets_json,affiliations_json=excluded.affiliations_json,
 official_url=excluded.official_url,raw_sha256=excluded.raw_sha256,last_seen_at=excluded.last_seen_at""",
 vals+(DOCINFO.format(acc),raw_hash,observed_at,observed_at))
 for i,t in enumerate(h.get('transmittals') or []):
  cid=(t.get('fileId') or '').strip() or f'{acc}:component:{i}'
  db.execute("""INSERT INTO ferc_components(component_id,accession,source_order,file_type,file_format,filename,description,reported_bytes)
  VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(component_id) DO UPDATE SET accession=excluded.accession,
  source_order=excluded.source_order,file_type=excluded.file_type,file_format=excluded.file_format,
  filename=excluded.filename,description=excluded.description,reported_bytes=excluded.reported_bytes""",
  (cid,acc,i,t.get('fileType'),t.get('fileFormat'),t.get('fileName'),t.get('fileDesc'),t.get('fileSize')))
 return len(h.get('transmittals') or [])

def run_search(db,start_date,end_date,page_size=100,fixture=None):
 run_id=str(uuid.uuid4()); started=now()
 db.execute("INSERT INTO ingest_runs(run_id,started_at,start_date,end_date,status) VALUES(?,?,?,?,?)",(run_id,started,start_date,end_date,'running'));db.commit()
 total_pages=expected=seen=comps=errors=0
 d0=dt.date.fromisoformat(start_date); d1=dt.date.fromisoformat(end_date)
 try:
  day=d0
  while day<=d1:
   p=1; day_expected=None; day_seen=0
   while True:
    if fixture:
     blob=pathlib.Path(fixture.format(day=day.isoformat(),page=p)).read_bytes()
    else: blob=request(SEARCH_URL,body(day.isoformat(),p,page_size))
    res=json.loads(blob); hits=res.get('searchHits') or []
    if res.get('success') is False: raise RuntimeError(res.get('errorMessage') or 'eLibrary search failed')
    if day_expected is None: day_expected=int(res.get('totalHits') or 0);expected+=day_expected
    for h in hits: comps+=ingest_hit(db,h,now())
    seen+=len(hits);day_seen+=len(hits);total_pages+=1
    db.execute("INSERT INTO ingest_pages VALUES(?,?,?,?,?,?,?)",(run_id,day.isoformat(),p,day_expected,len(hits),sha(blob),now()));db.commit()
    if day_seen>=day_expected: break
    if not hits: raise RuntimeError(f'{day}: empty page {p} before expected total {day_expected}')
    p+=1
   if day_seen!=day_expected: raise RuntimeError(f'{day}: reconciled {day_seen}, expected {day_expected}')
   day+=dt.timedelta(days=1)
  db.execute("""UPDATE ingest_runs SET finished_at=?,status='ok',expected_hits=?,pages_fetched=?,accessions_seen=?,components_seen=? WHERE run_id=?""",(now(),expected,total_pages,seen,comps,run_id));db.commit()
 except Exception as e:
  errors+=1;db.execute("UPDATE ingest_runs SET finished_at=?,status='failed',expected_hits=?,pages_fetched=?,accessions_seen=?,components_seen=?,errors=?,detail=? WHERE run_id=?",(now(),expected,total_pages,seen,comps,errors,str(e),run_id));db.commit();raise
 set_state(db,'last_complete_filed_date',end_date);db.commit()
 return run_id

def download_pending(db,store,limit=0,max_bytes=15_000_000):
 root=pathlib.Path(store);root.mkdir(parents=True,exist_ok=True); done=0
 q="SELECT * FROM ferc_components WHERE download_status IN ('pending','retry') ORDER BY accession,source_order"
 for r in db.execute(q):
  if limit and done>=limit:break
  if r['reported_bytes'] and r['reported_bytes']>max_bytes:
   db.execute("UPDATE ferc_components SET download_status='oversize' WHERE component_id=?",(r['component_id'],));continue
  try:
   blob=request(DOWNLOAD_URL,{"fileidLst":[r['component_id']]})
   digest=sha(blob); dest=root/digest[:2]/digest;dest.parent.mkdir(exist_ok=True);dest.write_bytes(blob)
   status='downloaded' if blob.startswith(b'%PDF-') else 'downloaded-non-pdf'
   db.execute("UPDATE ferc_components SET download_status=?,source_sha256=?,object_path=?,downloaded_at=? WHERE component_id=?",(status,digest,str(dest),now(),r['component_id']));done+=1;db.commit()
  except Exception as e:
   db.execute("UPDATE ferc_components SET download_status='retry' WHERE component_id=?",(r['component_id'],));db.execute("INSERT INTO engine_events(at,level,subject,message) VALUES(?,?,?,?)",(now(),'error',r['component_id'],str(e)));db.commit()
 return done

def parse_bbox(pdf:pathlib.Path):
 cp=subprocess.run(['pdfinfo',str(pdf)],capture_output=True,text=True,check=True)
 pages=int(re.search(r'^Pages:\s+(\d+)',cp.stdout,re.M).group(1))
 out=subprocess.run(['pdftotext','-bbox-layout',str(pdf),'-'],capture_output=True,text=True,check=True).stdout
 rawpages=re.findall(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>',out,re.S)
 if len(rawpages)!=pages: raise RuntimeError(f'page parse mismatch: pdfinfo={pages}, bbox={len(rawpages)}')
 result=[]
 for pn,(width,height,part) in enumerate(rawpages,1):
  w=float(width);h=float(height); toks=[]; text=''
  for i,m in enumerate(re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>',part)):
   word=html.unescape(m.group(5)); start=len(text);text+=(' ' if text else '')+word;start+=1 if start else 0
   toks.append((i,word,float(m.group(1))/w,float(m.group(2))/h,float(m.group(3))/w,float(m.group(4))/h,start,len(text)))
  result.append((pn,w,h,text,toks))
 return result

def extract_pending(db,limit=0):
 version=subprocess.run(['pdftotext','-v'],capture_output=True,text=True).stderr.splitlines()[0];done=0
 for r in db.execute("SELECT * FROM ferc_components WHERE download_status='downloaded' AND extraction_status IN ('pending','retry') ORDER BY accession,source_order"):
  if limit and done>=limit:break
  try:
   pages=parse_bbox(pathlib.Path(r['object_path']))
   for pn,w,h,text,toks in pages:
    db.execute("INSERT OR REPLACE INTO pages VALUES(?,?,?,?,?,?,?,?)",(r['component_id'],pn,w,h,text,len(toks),'digital_text',1.0))
    db.executemany("INSERT OR REPLACE INTO tokens VALUES(?,?,?,?,?,?,?,?,?,?)",[(r['component_id'],pn)+t for t in toks])
    # Page passages are the first safe unit. Paragraph segmentation follows after layout fixtures.
    if text:
     th=sha(text.encode()); pid='psg:'+sha(f"{r['source_sha256']}:{pn}:{th}".encode())
     db.execute("INSERT OR REPLACE INTO passages VALUES(?,?,?,?,?,?,?,?,?)",(pid,r['component_id'],pn,pn,0,len(toks)-1,text,th,'digital_text'))
     db.execute("DELETE FROM passage_fts WHERE passage_id=?",(pid,));db.execute("INSERT INTO passage_fts VALUES(?,?)",(pid,text))
   db.execute("UPDATE ferc_components SET extraction_status='full-text',extraction_version=? WHERE component_id=?",(version,r['component_id']));done+=1;db.commit()
  except Exception as e:
   db.execute("UPDATE ferc_components SET extraction_status='retry' WHERE component_id=?",(r['component_id'],));db.execute("INSERT INTO engine_events(at,level,subject,message) VALUES(?,?,?,?)",(now(),'error',r['component_id'],str(e)));db.commit()
 return done

def normword(s): return re.sub(r'[^a-z0-9]+','',s.lower())

def create_evidence(db,component_id,page,quote):
 rows=db.execute("SELECT * FROM tokens WHERE component_id=? AND page=? ORDER BY token_index",(component_id,page)).fetchall()
 want=[normword(x) for x in quote.split() if normword(x)]
 got=[normword(r['text']) for r in rows]
 found=None
 for i in range(len(got)-len(want)+1):
  if got[i:i+len(want)]==want: found=(i,i+len(want)-1);break
 if found is None: raise ValueError('exact normalized quote not found on page')
 a,b=found; chosen=rows[a:b+1]
 # Group adjacent words on the same visual line into minimal highlight rectangles.
 groups=[]
 for r in chosen:
  if not groups or abs(groups[-1][1]-r['y0'])>0.006:
   groups.append([r['x0'],r['y0'],r['x1'],r['y1']])
  else:
   groups[-1][0]=min(groups[-1][0],r['x0']);groups[-1][1]=min(groups[-1][1],r['y0']);groups[-1][2]=max(groups[-1][2],r['x1']);groups[-1][3]=max(groups[-1][3],r['y1'])
 comp=db.execute("SELECT source_sha256,extraction_version FROM ferc_components WHERE component_id=?",(component_id,)).fetchone()
 if not comp or not comp['source_sha256']: raise ValueError('component is not checksum-backed')
 key=f"{comp['source_sha256']}:{page}:{a}:{b}:{quote}";eid='ev:'+sha(key.encode())
 pid=db.execute("SELECT passage_id FROM passages WHERE component_id=? AND page_start<=? AND page_end>=? ORDER BY length(text) LIMIT 1",(component_id,page,page)).fetchone()
 if not pid: raise ValueError('no passage for page')
 db.execute("""INSERT OR REPLACE INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
 (eid,pid[0],component_id,comp['source_sha256'],comp['extraction_version'] or 'unknown','pdf_bbox',page,page,a,b,quote,json.dumps(groups,separators=(',',':')),'digital_text',1.0,now()))
 db.commit();return eid

def set_state(db,key,value):
 db.execute("INSERT INTO engine_state VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(key,value,now()))

def incremental_dates(db,through,overlap_days=2):
 end=dt.date.fromisoformat(through)
 row=db.execute("SELECT value FROM engine_state WHERE key='last_complete_filed_date'").fetchone()
 start=(dt.date.fromisoformat(row[0])-dt.timedelta(days=overlap_days)) if row else end
 return start.isoformat(),end.isoformat()

def report(db):
 return {k:db.execute(q).fetchone()[0] for k,q in {
  'documents':'select count(*) from ferc_documents','components':'select count(*) from ferc_components',
  'downloaded':"select count(*) from ferc_components where download_status like 'downloaded%'",
  'extracted':"select count(*) from ferc_components where extraction_status='full-text'",
  'pages':'select count(*) from pages','tokens':'select count(*) from tokens','passages':'select count(*) from passages'}.items()}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--db',default='canonical/ferc-engine.db');sp=ap.add_subparsers(dest='cmd',required=True)
 s=sp.add_parser('search');s.add_argument('--start-date',required=True);s.add_argument('--end-date',required=True);s.add_argument('--page-size',type=int,default=100);s.add_argument('--fixture')
 d=sp.add_parser('download');d.add_argument('--store',default='raw/ferc/objects');d.add_argument('--limit',type=int,default=0);d.add_argument('--max-bytes',type=int,default=15_000_000)
 e=sp.add_parser('extract');e.add_argument('--limit',type=int,default=0)
 sp.add_parser('report')
 a=ap.parse_args();db=dbopen(a.db)
 if a.cmd=='search':print(run_search(db,a.start_date,a.end_date,a.page_size,a.fixture))
 elif a.cmd=='download':print(json.dumps({'downloaded':download_pending(db,a.store,a.limit,a.max_bytes),**report(db)}))
 elif a.cmd=='extract':print(json.dumps({'extracted_now':extract_pending(db,a.limit),**report(db)}))
 else:print(json.dumps(report(db),indent=2))
if __name__=='__main__':main()
