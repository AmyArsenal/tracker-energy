#!/usr/bin/env python3
"""Pull and apply a checksum-verified tracker.energy feature bundle.

The control-plane endpoint returns JSON:
  {"version":"...","bundle_url":"https://...signed...","sha256":"..."}
The bundle is a .tar.gz overlay with repository-relative paths. It must not
contain .git, secrets, absolute paths, traversal, devices, or symlinks.
"""
from __future__ import annotations
import hashlib,json,os,pathlib,shutil,sys,tarfile,tempfile,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
STATE=ROOT/'canonical/feature-channel.json'
URL=os.environ.get('FEATURE_MANIFEST_URL','').strip()
TOKEN=os.environ.get('FEATURE_BUNDLE_TOKEN','').strip()
def fetch(url:str)->bytes:
    headers={'User-Agent':'tracker.energy-feature-pull/1'}
    if TOKEN: headers['Authorization']=f'Bearer {TOKEN}'
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=120) as r:return r.read()
def safe_member(m:tarfile.TarInfo)->bool:
    p=pathlib.PurePosixPath(m.name)
    return bool(m.name) and not p.is_absolute() and '..' not in p.parts and '.git' not in p.parts and not (m.issym() or m.islnk() or m.isdev())
def main():
    if not URL:
        print('Feature channel not configured; skipping.')
        return
    manifest=json.loads(fetch(URL)); version=str(manifest['version']); expected=str(manifest['sha256']).lower(); bundle_url=str(manifest['bundle_url'])
    if len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected):raise RuntimeError('Invalid SHA-256 in manifest')
    current={}
    if STATE.exists(): current=json.loads(STATE.read_text())
    if current.get('version')==version and current.get('sha256')==expected:
        print(f'Feature channel already at {version}; skipping.');return
    blob=fetch(bundle_url); actual=hashlib.sha256(blob).hexdigest()
    if actual!=expected:raise RuntimeError(f'Feature bundle checksum mismatch: expected {expected}, got {actual}')
    with tempfile.TemporaryDirectory() as td:
        arc=pathlib.Path(td)/'feature.tar.gz'; arc.write_bytes(blob)
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
