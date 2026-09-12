#!/usr/bin/env python3
"""Deterministic acceptance checks for the MISO ZGIA document-engine demo."""
import hashlib, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
d = json.loads((ROOT/'docs/data/zg-demo.json').read_text())
assert d['accession']=='20260818-5152' and d['docket']=='ER26-3552-000'
assert d['classification']['category'] in {'Tariff filing','Order','Notice','Complaint','Application','Other'}
assert d['classification']['substance'] in {'Substantive','Procedural','Unknown'}
assert set(d['classification']['topics']) <= {'Interconnection','Rates / tariffs','Large load','Transmission','Markets','Reliability','Other'}
evidence={e['evidence_id']:e for e in d['evidence']}
assert len(evidence)==len(d['evidence'])==5
for e in evidence.values():
    assert e['source_sha256']==d['source']['sha256']
    assert 1 <= e['page_start'] <= e['page_end'] <= d['source']['pages']
    assert e['quote'].strip() and e['boxes']
claims=[d['summary']['headline'],d['summary']['verdict']]
for key in ('what_changed','who_is_affected','what_next'): claims += d['summary'][key]
for c in claims:
    assert c['claim'].strip() and c['evidence_ids']
    assert all(x in evidence for x in c['evidence_ids'])
summary_text=' '.join(c['claim'] for c in claims).lower()
for unsupported in ('ferc accepted','ferc approved','commission accepted','commission approved'):
    assert unsupported not in summary_text
pdf=ROOT/'docs/filings/20260818-5152.pdfdata'
assert pdf.stat().st_size==d['source']['bytes']
assert hashlib.sha256(pdf.read_bytes()).hexdigest()==d['source']['sha256']
for p in {e['page_start'] for e in evidence.values()}:
    assert (ROOT/f'docs/data/zg-demo-pages/p{p}.jpg').stat().st_size>10_000
print(f"PASS: {len(claims)} cited claims, {len(evidence)} evidence objects, checksum and page assets verified")
