#!/usr/bin/env python3
"""Create a checksummed manifest for reproducible published data artifacts."""
import hashlib,json,pathlib,datetime
root=pathlib.Path(__file__).resolve().parents[1]
files=[]
for base in ('docs/data','docs/map-data'):
 for p in sorted((root/base).rglob('*')):
  if p.is_file():
   b=p.read_bytes(); files.append({'path':str(p.relative_to(root)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
out={'built_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files}
p=root/'canonical/manifest.json';p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(out,separators=(',',':')))
print(p,len(files))
