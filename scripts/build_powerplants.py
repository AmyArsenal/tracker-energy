#!/usr/bin/env python3
"""Build a compact, plant-level GeoJSON from the public EIA-860M archive.
EIA direct downloads can reject automated fetches; Catalyst Cooperative preserves
unaltered monthly workbooks on Zenodo. This builder records both upstream sources.
"""
import io,json,zipfile,urllib.request
from collections import defaultdict
import pandas as pd
ZENODO='https://zenodo.org/api/records/20364867/files/eia860m-2026.zip/content'
OUT='docs/map-data/us-power-plants.geojson'
FUEL={'MWH':'battery','SUN':'solar','NG':'gas','WND':'wind','NUC':'nuclear','BIT':'coal','SUB':'coal','LIG':'coal','WC':'coal','WAT':'hydro'}
LABEL={'battery':'Battery','solar':'Solar','gas':'Natural gas','wind':'Wind','nuclear':'Nuclear','coal':'Coal','hydro':'Hydro'}
UC_PREFIX=('(U)','(V)','(TS)')
def status(raw,kind):
    raw=str(raw or '')
    if kind=='operating': return 'operating'
    return 'construction' if raw.startswith(UC_PREFIX) else 'planned'
def main():
    req=urllib.request.Request(ZENODO,headers={'User-Agent':'tracker.energy public-data build'})
    blob=urllib.request.urlopen(req,timeout=240).read()
    z=zipfile.ZipFile(io.BytesIO(blob)); names=sorted(n for n in z.namelist() if n.endswith('.xlsx'))
    newest=names[-1]; workbook=z.read(newest)
    rows=[]
    for sheet,kind in [('Operating','operating'),('Planned','planned')]:
        d=pd.read_excel(io.BytesIO(workbook),sheet_name=sheet,skiprows=2)
        d=d[d['Energy Source Code'].isin(FUEL)]
        for _,r in d.iterrows():
            if pd.isna(r.get('Latitude')) or pd.isna(r.get('Longitude')): continue
            mw=pd.to_numeric(r.get('Nameplate Capacity (MW)'),errors='coerce')
            if pd.isna(mw) or mw<=0: continue
            rows.append(dict(plant_id=str(r['Plant ID']),name=str(r['Plant Name']),developer=str(r['Entity Name']),state=str(r['Plant State']),county=str(r['County']),ba=str(r.get('Balancing Authority Code') or ''),lat=float(r['Latitude']),lon=float(r['Longitude']),fuel=FUEL[r['Energy Source Code']],mw=float(mw),status=status(r.get('Status'),kind),status_raw=str(r.get('Status') or ''),year=int(r['Operating Year'] if kind=='operating' and pd.notna(r.get('Operating Year')) else r['Planned Operation Year']) if pd.notna(r.get('Operating Year') if kind=='operating' else r.get('Planned Operation Year')) else None))
    g={}
    for r in rows:
        k=(r['plant_id'],r['fuel'],r['status'])
        if k not in g: g[k]=r.copy()
        else:
            g[k]['mw']+=r['mw']
            if not g[k]['year'] and r['year']: g[k]['year']=r['year']
    feats=[]
    for r in g.values():
        p={k:r[k] for k in ('plant_id','name','developer','state','county','ba','fuel','status','status_raw','year')}
        p['fuel_label']=LABEL[r['fuel']];p['mw']=round(r['mw'],1)
        feats.append({'type':'Feature','geometry':{'type':'Point','coordinates':[round(r['lon'],5),round(r['lat'],5)]},'properties':p})
    feats.sort(key=lambda f:(f['properties']['fuel'],f['properties']['status'],-f['properties']['mw']))
    out={'type':'FeatureCollection','metadata':{'source':'EIA-860M Preliminary Monthly Electric Generator Inventory','workbook':newest,'eia_url':'https://www.eia.gov/electricity/data/eia860m/','archive_url':ZENODO,'archive_publisher':'Catalyst Cooperative / PUDL on Zenodo','scope':'Contiguous US + AK/HI records; map viewport defaults to contiguous US','built_utc':pd.Timestamp.utcnow().isoformat(),'records':len(feats)},'features':feats}
    open(OUT,'w').write(json.dumps(out,separators=(',',':')))
    print(OUT,len(feats),len(json.dumps(out)))
if __name__=='__main__': main()
