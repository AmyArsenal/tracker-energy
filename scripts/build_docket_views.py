#!/usr/bin/env python3
"""Build procedural docket views from the current normalized FERC feed."""
import json, os, re
ROOT=os.path.dirname(os.path.dirname(__file__))
FERC=os.path.join(ROOT,'docs','data','ferc.json'); OUT=os.path.join(ROOT,'docs','data','dockets')
DOCKETS={
 'ER26-1323':'SPP Conditional High Impact Large Load service',
 'ER26-2249':'SPP generator-interconnection revisions with large-load participation',
 'ER26-3265':'ATC large-load project commitment agreements',
 'ER26-3380':'PJM reliability backstop procurement',
 'ER26-3515':'PJM Interim Resource Adequacy Service and Large Load Registry',
 'ER26-3525':'PJM Schedule 12 baseline-upgrade cost responsibility revisions',
 'ER26-3552':'MISO Zero Injection Generator Interconnection Agreement',
 'ER26-3591':'SPP CHILL policy planned-outage revisions',
 'ER26-3650':'MISO interconnection reliability requirements for large loads',
 'ER26-3685':'SPP Conditional High Impact Large Load policy',
 'EL26-67':'PJM large-load show-cause proceeding',
 'EL26-68':'SPP large-load show-cause proceeding',
 'EL26-69':'NYISO large-load show-cause proceeding',
 'EL26-70':'MISO large-load show-cause proceeding',
 'EL26-71':'CAISO large-load show-cause proceeding',
 'EL26-72':'ISO-NE large-load show-cause proceeding'}
PHASES=[
 {'id':'application','label':'Application','description':'The filing that opens the proceeding.'},
 {'id':'notices','label':'Notice and schedule','description':'Commission notices and deadline changes.'},
 {'id':'interventions','label':'Party formation','description':'Who entered the docket. Intervention alone is not a merits position.'},
 {'id':'protests','label':'Protests and comments','description':'Positions on the filing.'},
 {'id':'answers','label':'Answers and replies','description':'Responses to protests and other pleadings.'},
 {'id':'order','label':'Commission order','description':'The final disposition and conditions.'},]
def phase(x):
 c=x.get('class') or ''; t=x.get('type') or ''
 if c=='Application/Petition/Request': return 'application'
 if c=='Intervention': return 'interventions'
 if c=='Comments/Protest': return 'protests'
 if c in ('Answer','Response') or 'Answer' in t or 'Response' in t: return 'answers'
 if c=='Order' or 'Order' in t: return 'order'
 return 'notices'
def role(x):
 a=(x.get('author') or '').lower(); p=phase(x)
 if p=='application': return 'applicant'
 if 'secretary' in a or 'ferc' in a: return 'commission'
 if p=='protests': return 'protestor'
 return 'intervenor'
def summary(x):
 a=x.get('accession'); who=x.get('author') or 'This party'; c=x.get('class')
 fixed={
 '20260814-5186':'PJM asks FERC to accept revised Schedule 12, Appendix A cost responsibility for July 2026 RTEP baseline upgrades, effective 12 November.',
 '20260814-3081':'FERC publishes the filing in its combined notice.',
 '20260817-3042':'FERC extends the comment period for PJM’s filing.',
 '20260908-5083':'Towering Concerns asks FERC to reject or defer the tariff filing.'}
 if a in fixed:return fixed[a]
 if c=='Intervention':return f'{who} enters the docket as a party without stating a merits position.'
 return re.sub(r'\s+',' ',x.get('summary') or x.get('description') or '').strip()
def main():
 data=json.load(open(FERC)); os.makedirs(OUT,exist_ok=True)
 for dk,caption in DOCKETS.items():
  items=[x for x in data['items'] if any(d.replace('-000','')==dk for d in x.get('dockets',[]))]
  items.sort(key=lambda x:(x.get('filed') or '',x.get('accession') or ''))
  applications=[x.get('accession') for x in items if phase(x)=='application']
  base=applications[0] if applications else None
  rows=[]
  for x in items:
   acc=x.get('accession'); p=phase(x)
   rows.append({'accession':acc,'date':x.get('filed'),'party':x.get('author') or 'Unknown filer','role':role(x),'phase':p,'filing_type':x.get('type') or x.get('class'),'summary':summary(x),'responds_to':base if p in ('protests','answers') and base else None,'url':x.get('url'),'has_document':os.path.exists(os.path.join(ROOT,'docs','filings',f'{acc}.pdfdata'))})
  has_order=any(r['phase']=='order' for r in rows)
  out={'docket':dk,'caption':caption,'status':'Commission order issued' if has_order else 'Awaiting Commission action','updated':data.get('generated_at') or '', 'source':f'https://elibrary.ferc.gov/eLibrary/dockets?docket_number={dk}-000','phases':PHASES,'rows':rows}
  json.dump(out,open(os.path.join(OUT,f'{dk}.json'),'w'),indent=1)
  print(f'{dk}: {len(rows)} procedural events')
if __name__=='__main__':main()
