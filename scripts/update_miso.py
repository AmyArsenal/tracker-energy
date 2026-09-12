#!/usr/bin/env python3
"""MISO official stakeholder calendar ingestion.

The official month endpoint is Cloudflare-gated for ordinary HTTP clients. This
script makes one polite request per month; on a block it preserves the last
verified browser-captured calendar instead of replacing it with empty data.
"""
import datetime, html, json, os, re, sys, urllib.request
ROOT=os.path.join(os.path.dirname(__file__),'..'); DATA=os.path.join(ROOT,'docs','data')
RAW=os.path.join(DATA,'miso_raw.json'); OUT=os.path.join(DATA,'miso.json')
CAL='https://www.misoenergy.org/engage/tools/calendar/'
API='https://www.misoenergy.org/api/events/geteventsformonth?month={}&year={}'
UA={'User-Agent':'Mozilla/5.0 (compatible; tracker.energy; weekly MISO calendar refresh)'}
TOPICS=[
 ('large load / data centers',r'large load|data cent|co-?locat|zero.?injection|ZGIA'),
 ('interconnection',r'interconnect|generator interconnection|queue|GIA|GIAP|IPWG'),
 ('planning / transmission',r'planning|transmission|MTEP|EPR|regional expansion'),
 ('capacity / resource adequacy',r'capacity|resource adequacy|accreditation|RASC'),
 ('markets',r'market|auction|pricing|settlement|MSC'),
 ('reliability / operations',r'reliab|operations|outage|compliance'),
 ('governance',r'board|governance|stakeholder|advisory committee'),]
def topic_tags(text):
 return [n for n,p in TOPICS if re.search(p,text or '',re.I)] or ['general']
def fetch_month(month,year):
 req=urllib.request.Request(API.format(month,year),headers=UA)
 with urllib.request.urlopen(req,timeout=45) as r: return json.load(r).get('events',[])
def normalize(raw):
 out=[]
 for e in raw:
  if e.get('isDeleted') or e.get('eventCanceled'): continue
  name=html.unescape(e.get('name') or e.get('pageName') or '').strip()
  if not name: continue
  ents=e.get('entityReferenceList') or []
  group=', '.join(x.get('text','') for x in ents if x.get('text')) or None
  start=e.get('startDate') or e.get('meetingDate')
  if not start or start.startswith('0001-'): continue
  slug=e.get('urlSegment')
  url=f'https://www.misoenergy.org/events/{start[:4]}/{slug}/' if slug else CAL
  out.append({'iso':'MISO','name':name,'start':start,'end':e.get('endDate'),
   'tz':'US/Central','location':e.get('hostLocation'),'url':url,'group':group,
   'topics':topic_tags(f'{name} {group or ""}')})
 out.sort(key=lambda e:e['start'])
 return out
if __name__=='__main__':
 today=datetime.date.today(); raw=[]; errors=[]
 for add in range(4):
  d=(today.replace(day=1)+datetime.timedelta(days=32*add)).replace(day=1)
  try: raw += fetch_month(d.month,d.year)
  except Exception as e: errors.append(f'{d:%Y-%m}: {e}')
 if raw:
  seen={};
  for e in raw: seen[e.get('contentGuid') or e.get('contentLink') or e.get('name')]=e
  raw=list(seen.values()); json.dump({'source':'MISO official calendar API','source_url':CAL,
   'refreshed_at':datetime.datetime.utcnow().isoformat(timespec='seconds')+'Z','events':raw},open(RAW,'w'),separators=(',',':'))
 elif os.path.exists(RAW): raw=json.load(open(RAW)).get('events',[])
 else: raise SystemExit('MISO calendar unavailable and no verified prior snapshot')
 events=normalize(raw)
 json.dump({'source':'MISO official calendar API','source_url':CAL,
  'refreshed_at':datetime.datetime.utcnow().isoformat(timespec='seconds')+'Z',
  'errors':errors,'events':events},open(OUT,'w'),separators=(',',':'))
 print(f'miso.json: {len(events)} meetings; errors={errors}')
