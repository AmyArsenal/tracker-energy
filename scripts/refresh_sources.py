#!/usr/bin/env python3
"""Refresh connectors independently and retain last-good published outputs.

A transient connector failure must not block unrelated sources, canonical builds,
or Pages. Before each connector runs, declared public outputs are copied to a
temporary checkpoint. On failure they are restored byte-for-byte and the source
is marked degraded. The command exits nonzero only when a failed connector has
no complete prior output to restore or when an output fails structural checks.
"""
from __future__ import annotations
import argparse,datetime as dt,json,pathlib,shutil,subprocess,sys,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
CONNECTORS=[
 {'id':'ferc','cmd':['python3','scripts/update_data.py'],'outputs':['docs/data/ferc.json','docs/data/battery.json','docs/data/meta.json','docs/data/articles','docs/filings'],'checks':{'docs/data/ferc.json':('items',1)}},
 {'id':'pjm','cmd':['python3','scripts/update_pjm.py'],'outputs':['docs/data/pjm.json','docs/filings'],'checks':{'docs/data/pjm.json':('documents',1)}},
 {'id':'miso','cmd':['python3','scripts/update_miso.py'],'outputs':['docs/data/miso.json','docs/data/miso_raw.json'],'checks':{'docs/data/miso.json':('events',1)}},
 {'id':'iso','cmd':['python3','scripts/update_iso.py'],'outputs':['docs/data/iso.json'],'checks':{'docs/data/iso.json':('events',1)}},
 {'id':'puc','cmd':['python3','scripts/update_puc.py'],'outputs':['docs/data/puc.json'],'checks':{'docs/data/puc.json':('dockets',1)}},
 {'id':'powerplants','cmd':['python3','scripts/build_powerplants.py'],'outputs':['docs/map-data/us-power-plants.geojson'],'checks':{'docs/map-data/us-power-plants.geojson':('features',1)}},
 {'id':'queues','cmd':['python3','scripts/build_iso_queues.py'],'outputs':['docs/map-data/us-iso-queues.json'],'checks':{'docs/map-data/us-iso-queues.json':('records',1)}},
]
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def validate(path,spec):
 d=json.loads(path.read_text());key,minimum=spec
 # queue output nests rows under records; GeoJSON and standard feeds use the same shape.
 value=d.get(key) if isinstance(d,dict) else None
 if not isinstance(value,list) or len(value)<minimum:raise ValueError(f'{path}: expected {key} list with at least {minimum} row(s)')
 return len(value)
def snapshot(src,dst):
 if src.is_dir():shutil.copytree(src,dst)
 else:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def restore(src,dst):
 if dst.is_dir():
  if src.exists():shutil.rmtree(src)
  shutil.copytree(dst,src)
 else:
  src.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,src)
def run_connector(c,backup_root,timeout):
 started=now();backs={};missing=[]
 for rel in c['outputs']:
  src=ROOT/rel
  if src.exists():
   dst=backup_root/rel;snapshot(src,dst);backs[rel]=dst
  else:missing.append(rel)
 try:
  r=subprocess.run(c['cmd'],cwd=ROOT,text=True,capture_output=True,timeout=timeout)
  if r.returncode:raise RuntimeError(f'exit {r.returncode}: {(r.stderr or r.stdout)[-1200:]}')
  counts={rel:validate(ROOT/rel,spec) for rel,spec in c.get('checks',{}).items()}
  return {'source':c['id'],'status':'ok','started_at':started,'completed_at':now(),'counts':counts,'stdout_tail':r.stdout[-600:]}
 except Exception as e:
  for rel,dst in backs.items():restore(ROOT/rel,dst)
  # Remove partial outputs that did not exist in the checkpoint.
  for rel in missing:
   partial=ROOT/rel
   if partial.is_dir():shutil.rmtree(partial)
   elif partial.exists():partial.unlink()
  # Only primary validated outputs are required for a usable last-good source.
  required=list(c.get('checks',{})) or c['outputs']
  unrestorable=[rel for rel in required if rel not in backs]
  return {'source':c['id'],'status':'failed' if unrestorable else 'degraded','started_at':started,'completed_at':now(),'error':str(e),'restored_last_good':sorted(backs),'missing_last_good':unrestorable}

def main():
 p=argparse.ArgumentParser();p.add_argument('--only',action='append',choices=[c['id'] for c in CONNECTORS]);p.add_argument('--timeout-seconds',type=int,default=300);p.add_argument('--health-out',default='docs/data/source-health.json');a=p.parse_args();chosen=[c for c in CONNECTORS if not a.only or c['id'] in a.only]
 with tempfile.TemporaryDirectory() as td:results=[run_connector(c,pathlib.Path(td),a.timeout_seconds) for c in chosen]
 report={'schema_version':'1.0','generated_at':now(),'overall_status':'failed' if any(x['status']=='failed' for x in results) else ('degraded' if any(x['status']=='degraded' for x in results) else 'ok'),'sources':results}
 out=ROOT/a.health_out;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps({'overall_status':report['overall_status'],'sources':[{k:x.get(k) for k in ['source','status','counts','error','restored_last_good','missing_last_good']} for x in results]}))
 if report['overall_status']=='failed':return 1
 return 0
if __name__=='__main__':sys.exit(main())
