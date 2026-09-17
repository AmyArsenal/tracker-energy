#!/usr/bin/env python3
"""Continuity helpers for bounded discovery feeds.

A source query is evidence that a record was seen, never proof that a previously
seen record was withdrawn. These functions retain scoped records with explicit
freshness and deduplicate FERC accessions deterministically.
"""
from __future__ import annotations
import copy,datetime as dt,hashlib,json,pathlib

def day(value=None): return value or dt.datetime.now(dt.timezone.utc).date().isoformat()
def docket_root(v): return (v or '').rsplit('-',1)[0]
def merge_ferc_rows(rows):
 out={};order=[]
 for raw in rows:
  acc=(raw.get('accession') or '').strip()
  if not acc:continue
  if acc not in out:out[acc]=copy.deepcopy(raw);order.append(acc);continue
  cur=out[acc]
  cur['dockets']=sorted(set((cur.get('dockets') or [])+(raw.get('dockets') or [])))
  # Keep the richer component and any successful local mirror.
  for k in ['doc_local','file_id','file_name','file_size','file_desc','description','summary','author','class','type','category','url','filed','issued']:
   if not cur.get(k) and raw.get(k) is not None:cur[k]=raw[k]
 return [out[x] for x in order]
def retain_ferc(current,previous,tracked_dockets,as_of=None):
 today=day(as_of);cur=merge_ferc_rows(current);seen={x['accession'] for x in cur}
 for x in cur:x['source_presence']='current';x['last_seen_date']=today;x.pop('missing_since',None)
 retained=[]
 for raw in merge_ferc_rows(previous):
  acc=raw['accession'];tracked=any(docket_root(d) in tracked_dockets for d in raw.get('dockets') or [])
  if acc in seen or not tracked:continue
  x=copy.deepcopy(raw);x['source_presence']='retained_missing';x['missing_since']=x.get('missing_since') or today;x['last_seen_date']=x.get('last_seen_date');retained.append(x)
 return cur+retained
def retain_puc(current,previous,as_of=None):
 today=day(as_of);cur=copy.deepcopy(current);seen={(x.get('state'),x.get('docket')) for x in cur}
 for x in cur:x['source_presence']='current';x['last_seen_date']=today;x.pop('missing_since',None)
 retained=[]
 for raw in previous:
  key=(raw.get('state'),raw.get('docket'))
  if key in seen or not all(key):continue
  x=copy.deepcopy(raw);x['source_presence']='retained_missing';x['missing_since']=x.get('missing_since') or today;x['last_seen_date']=x.get('last_seen_date');retained.append(x)
 return cur+retained

def write_reconciliation(path,source,records,as_of=None):
 """Append immutable first-observed missing events; repeated misses dedupe."""
 today=day(as_of);p=pathlib.Path(path)
 try:data=json.loads(p.read_text()) if p.exists() else {"schema_version":"1.0","events":[]}
 except Exception:data={"schema_version":"1.0","events":[]}
 have={x.get("event_id") for x in data["events"]};added=0
 for x in records:
  if x.get("source_presence")!="retained_missing":continue
  key=(x.get("accession") or x.get("docket") or "").strip()
  first=x.get("missing_since") or today
  eid="reconciliation:"+hashlib.sha256(f"{source}|{key}|{first}".encode()).hexdigest()
  if not key or eid in have:continue
  data["events"].append({"event_id":eid,"event_type":"source.record_missing_from_bounded_discovery","source":source,"record_id":key,"first_missing_date":first,"last_seen_date":x.get("last_seen_date"),"source_presence":"retained_missing","interpretation":"Absence from this bounded query is not evidence of withdrawal, closure, or deletion.","confidence":{"band":"high","basis":"deterministic source reconciliation"}});have.add(eid);added+=1
 data["generated_at"]=dt.datetime.now(dt.timezone.utc).isoformat();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n");return added
