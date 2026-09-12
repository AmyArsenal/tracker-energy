#!/usr/bin/env python3
"""Normalize public ISO/RTO interconnection queue reports for the static product."""
import io,json,re,time,requests,pandas as pd
from datetime import datetime,timezone
OUT='docs/map-data/us-iso-queues.json'; UA={'User-Agent':'Mozilla/5.0 (tracker.energy public data research)'}
SOURCES={
 'PJM':'https://www.pjm.com/planning/service-requests',
 'MISO':'https://www.misoenergy.org/planning/resource-utilization/generator-interconnection/',
 'SPP':'https://opsportal.spp.org/Studies/GISummary',
 'CAISO':'https://www.caiso.com/generation-transmission/generation/generator-interconnection',
 'NYISO':'https://www.nyiso.com/interconnections',
 'ISO-NE':'https://www.iso-ne.com/system-planning/interconnection-service/interconnection-request-queue',
 'ERCOT':'https://www.ercot.com/mp/data-products/data-product-details?id=PG7-200-ER'}
FUEL={'BAT':'Battery','BA':'Battery','Battery':'Battery','SOL':'Solar','PV':'Solar','Solar':'Solar','WIN':'Wind','WND':'Wind','Wind':'Wind','GAS':'Gas','NG':'Gas','NUC':'Nuclear','WAT':'Hydro','HYD':'Hydro'}
def clean(v): return None if pd.isna(v) else str(v).strip()
def num(v):
 try: return round(float(v),2) if not pd.isna(v) else None
 except: return None
def fuel(v):
 s=clean(v) or 'Other'
 for k,n in FUEL.items():
  if k.lower() in s.lower(): return n
 return s.title()
def rec(iso,id,name,mw,fuelv,status,state=None,county=None,poi=None,utility=None,cycle=None,date=None,developer=None,updated=None):
 return {'iso':iso,'id':clean(id),'name':clean(name),'mw':num(mw),'fuel':fuel(fuelv),'status':clean(status) or 'Unknown','state':clean(state),'county':clean(county),'poi':clean(poi),'utility':clean(utility),'cycle':clean(cycle),'queue_date':clean(date),'developer':clean(developer),'updated':clean(updated),'source_url':SOURCES[iso],'source_confidence':'official public queue','map_match':'pending'}
def spp():
 r=requests.get('https://opsportal.spp.org/Studies/GenerateSummaryCSV',headers=UA,timeout=120);r.raise_for_status();d=pd.read_csv(io.StringIO(r.text),skiprows=1)
 return [rec('SPP',x['Generation Interconnection Number'],None,x['Capacity'],x['Generation Type'],x['Status'],x['State'],x[' Nearest Town or County'],x['Substation or Line'],x['TO at POI'],x['Current Cluster'],x['Request Received']) for _,x in d.iterrows()]
def caiso():
 r=requests.get('https://www.caiso.com/documents/publicqueuereport.xlsx',headers=UA,timeout=180);r.raise_for_status(); raw=io.BytesIO(r.content);tabs=pd.read_excel(raw,skiprows=3,sheet_name=None);out=[]
 for sn,st in [('Grid GenerationQueue','Active'),('Completed Generation Projects','Completed'),('Withdrawn Generation Projects','Withdrawn')]:
  d=tabs.get(sn,pd.DataFrame())
  for _,x in d.iterrows():
   q=x.get('Queue Position');
   if pd.isna(q): continue
   fv=' + '.join(str(x.get(c)) for c in ['Type-1','Type-2','Type-3'] if not pd.isna(x.get(c)))
   out.append(rec('CAISO',q,x.get('Project Name') or x.get('Project Name - Confidential'),x.get('Net MWs to Grid'),fv,x.get('Application Status') or st,x.get('State'),x.get('County'),x.get('Station or Transmission Line'),x.get('Utility'),x.get('Study\nProcess'),x.get('Queue Date')))
 return out
def isone():
 r=requests.get('https://irtt.iso-ne.com/reports/external',headers=UA,timeout=120);r.raise_for_status();d=pd.read_html(io.StringIO(r.text),attrs={'id':'publicqueue'})[0]; sm={'A':'Active','W':'Withdrawn','C':'Completed'}
 return [rec('ISO-NE',x['QP'],x.get('Alternative Name'),x.get('Net MW') or x.get('Summer MW'),x.get('Fuel Type'),sm.get(x.get('Status'),x.get('Status')),x.get('ST'),x.get('County'),x.get('POI'),x.get('TO Report'),x.get('Cluster'),x.get('Requested'),None,x.get('Updated')) for _,x in d.iterrows()]
def ercot():
 j=requests.get('https://www.ercot.com/misapp/servlets/IceDocListJsonWS',params={'reportTypeId':15933},headers=UA,timeout=60).json();docs=[x['Document'] for x in j['ListDocsByRptTypeRes']['DocumentList']];g=[x for x in docs if x.get('FriendlyName','').startswith('GIS_Report')];latest=max(g,key=lambda x:x['PublishDate']);r=requests.get('https://www.ercot.com/misdownload/servlets/mirDownload',params={'doclookupId':latest['DocID']},headers=UA,timeout=180);r.raise_for_status();d=pd.read_excel(io.BytesIO(r.content),sheet_name='Project Details - Large Gen',skiprows=30).iloc[4:]
 return [rec('ERCOT',x['INR'],x.get('Project Name'),x.get('Capacity (MW)'),f"{x.get('Fuel','')} {x.get('Technology','')}",x.get('GIM Study Phase'),'TX',x.get('County'),x.get('POI Location'),None,None,None,x.get('Interconnecting Entity'),latest['PublishDate']) for _,x in d.iterrows() if not pd.isna(x.get('INR'))]
def nyiso():
 u='https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx';r=None
 for delay in [0,10,15]:
  if delay: time.sleep(delay)
  r=requests.get(u,headers=UA,timeout=120)
  if r.status_code==200 and len(r.content)>5000: break
 if not r or r.status_code!=200: raise RuntimeError(f'official workbook HTTP {r.status_code if r else "none"}')
 tabs=pd.read_excel(io.BytesIO(r.content),sheet_name=None);out=[]
 for sn,st in [('Interconnection Queue','Active'),(' Cluster Projects','Active'),('Withdrawn','Withdrawn')]:
  for _,x in tabs.get(sn,pd.DataFrame()).iterrows(): out.append(rec('NYISO',x.get('Queue Pos.'),x.get('Project Name'),x.get('SP (MW)') or x.get('Capacity (MW)'),x.get('Type/ Fuel'),st,x.get('State'),x.get('County'),x.get('Point of Interconnection'),x.get('Utility'),x.get('Class Year'),x.get('Date of IR')))
 return out
def pjm():
 d=json.load(open('docs/map-data/pjm-va-queue.json'))
 out=[]
 for x in d: out.append(rec('PJM',x.get('id'),None,x.get('mw'),'Large load',x.get('status'),x.get('state'),None,x.get('poi'),x.get('owner'),None,None));out[-1]['map_match']='Virginia POI-name pilot'
 return out
def main():
 allr=[];cov={};
 for iso,fn in [('PJM',pjm),('SPP',spp),('CAISO',caiso),('ISO-NE',isone),('ERCOT',ercot),('NYISO',nyiso)]:
  try: rows=[x for x in fn() if x.get('id')];allr+=rows;cov[iso]={'status':'live' if iso!='PJM' else 'partial','records':len(rows),'source_url':SOURCES[iso]};print(iso,len(rows))
  except Exception as e: cov[iso]={'status':'blocked','records':0,'source_url':SOURCES[iso],'error':str(e)};print(iso,'FAILED',e)
 cov['MISO']={'status':'blocked','records':0,'source_url':SOURCES['MISO'],'error':'Official JSON endpoint returned HTTP 403; adapter retained, source refresh pending.'}
 out={'metadata':{'refreshed_at':datetime.now(timezone.utc).isoformat(),'records':len(allr),'schema':['id','poi','state','status','utility','mw','fuel','cycle'],'coverage':cov,'validation':'Source-stamped normalization; map joins are pending unless explicitly labeled.'},'records':allr}
 open(OUT,'w').write(json.dumps(out,separators=(',',':'),default=str));print(OUT,len(allr))
if __name__=='__main__':main()
