#!/usr/bin/env python3
"""Apply a checksum-verified feature overlay from tracker.energy's GitHub control issue.

FEATURE_MANIFEST_URL may return either a direct manifest object or GitHub's issue-
comments array. For an issue channel, only comments authored by the repository
owner and marked OWNER by GitHub are eligible. The newest valid v1 comment wins.
"""
from __future__ import annotations
import base64,binascii,hashlib,json,os,pathlib,re,shutil,tarfile,tempfile,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
STATE=ROOT/'canonical/feature-channel.json'
URL=os.environ.get('FEATURE_MANIFEST_URL','').strip()
TOKEN=os.environ.get('FEATURE_BUNDLE_TOKEN','').strip()
OWNER=os.environ.get('FEATURE_CHANNEL_OWNER','AmyArsenal').strip()
MARKER='<!-- tracker-feature-channel:v1 -->'
MAX_BUNDLE_BYTES=40*1024*1024

def fetch(url:str)->bytes:
    headers={'User-Agent':'tracker.energy-feature-pull/1','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    if TOKEN: headers['Authorization']=f'Bearer {TOKEN}'
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=120) as r:return r.read()

def comment_manifest(body:str)->dict|None:
    if MARKER not in body:return None
    tail=body.split(MARKER,1)[1].strip()
    m=re.search(r'```(?:json)?\s*(\{.*?\})\s*```',tail,re.S)
    raw=m.group(1) if m else tail
    try:return json.loads(raw)
    except json.JSONDecodeError:return None

def load_manifest(raw:bytes)->dict:
    payload=json.loads(raw)
    if isinstance(payload,dict):return payload
    if not isinstance(payload,list):raise RuntimeError('Feature channel must return a manifest object or GitHub comments array')
    for comment in reversed(payload):
        user=(comment.get('user') or {}).get('login','')
        if user.casefold()!=OWNER.casefold() or comment.get('author_association')!='OWNER':continue
        manifest=comment_manifest(comment.get('body') or '')
        if manifest:return manifest
    raise RuntimeError(f'No valid owner-authored feature manifest found for {OWNER}')

def manifest_blob(manifest:dict)->bytes:
    if 'bundle_base64' in manifest:
        try:blob=base64.b64decode(str(manifest['bundle_base64']),validate=True)
        except (binascii.Error,ValueError) as e:raise RuntimeError('Invalid base64 feature bundle') from e
    else:blob=fetch(str(manifest['bundle_url']))
    if not blob or len(blob)>MAX_BUNDLE_BYTES:raise RuntimeError('Feature bundle is empty or exceeds 40 MiB')
    return blob

def safe_member(m:tarfile.TarInfo)->bool:
    p=pathlib.PurePosixPath(m.name)
    return bool(m.name) and not p.is_absolute() and '..' not in p.parts and '.git' not in p.parts and not (m.issym() or m.islnk() or m.isdev())

def main():
    if not URL:
        print('Feature channel not configured; skipping.');return
    manifest=load_manifest(fetch(URL));version=str(manifest['version']);expected=str(manifest['sha256']).lower()
    if len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected):raise RuntimeError('Invalid SHA-256 in manifest')
    current=json.loads(STATE.read_text()) if STATE.exists() else {}
    if current.get('version')==version and current.get('sha256')==expected:
        print(f'Feature channel already at {version}; skipping.');return
    blob=manifest_blob(manifest);actual=hashlib.sha256(blob).hexdigest()
    if actual!=expected:raise RuntimeError(f'Feature bundle checksum mismatch: expected {expected}, got {actual}')
    with tempfile.TemporaryDirectory() as td:
        arc=pathlib.Path(td)/'feature.tar.gz';arc.write_bytes(blob)
        stage=pathlib.Path(td)/'stage';stage.mkdir()
        with tarfile.open(arc,'r:gz') as tf:
            members=tf.getmembers()
            if not members or any(not safe_member(m) for m in members):raise RuntimeError('Unsafe feature bundle member')
            tf.extractall(stage,members=members,filter='data')
        for src in stage.rglob('*'):
            if src.is_file():
                dst=ROOT/src.relative_to(stage);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps({'version':version,'sha256':expected,'manifest_url':URL},separators=(',',':'))+'\n')
    print(f'Applied feature bundle {version} ({actual})')
if __name__=='__main__':main()
