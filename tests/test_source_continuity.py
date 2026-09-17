import importlib.util,pathlib,unittest,tempfile,json,ast
p=pathlib.Path(__file__).parents[1]/'scripts/source_continuity.py';s=importlib.util.spec_from_file_location('sc',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ContinuityTest(unittest.TestCase):
 def test_ferc_dedupes_and_merges_dockets(self):
  rows=[{'accession':'a','dockets':['ER1-1-000'],'file_name':'x'},{'accession':'a','dockets':['ER2-2-000'],'doc_local':'filings/a.pdf'}]
  got=m.merge_ferc_rows(rows);self.assertEqual(len(got),1);self.assertEqual(got[0]['dockets'],['ER1-1-000','ER2-2-000']);self.assertTrue(got[0]['doc_local'])
 def test_ferc_retains_only_tracked_missing(self):
  prev=[{'accession':'a','dockets':['ER1-1-000'],'last_seen_date':'2026-09-14'},{'accession':'b','dockets':['CP1-1-000']}]
  got=m.retain_ferc([],prev,{'ER1-1'},'2026-09-15');self.assertEqual([x['accession'] for x in got],['a']);self.assertEqual(got[0]['source_presence'],'retained_missing');self.assertEqual(got[0]['last_seen_date'],'2026-09-14')
 def test_puc_retains_missing_and_marks_freshness(self):
  cur=[{'state':'VA','docket':'PUR-2'}];prev=[{'state':'VA','docket':'PUR-1','status':'Pending','last_seen_date':'2026-09-14'}]
  got=m.retain_puc(cur,prev,'2026-09-15');self.assertEqual(len(got),2);self.assertEqual(got[0]['source_presence'],'current');self.assertEqual(got[1]['source_presence'],'retained_missing');self.assertEqual(got[1]['status'],'Pending')
 def test_reconciliation_is_immutable_and_deduped(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'events.json';rows=[{'accession':'a','source_presence':'retained_missing','missing_since':'2026-09-15','last_seen_date':'2026-09-14'}]
   self.assertEqual(m.write_reconciliation(p,'ferc',rows,'2026-09-15'),1);self.assertEqual(m.write_reconciliation(p,'ferc',rows,'2026-09-16'),0)
   d=json.loads(p.read_text());self.assertEqual(len(d['events']),1);self.assertEqual(d['events'][0]['event_type'],'source.record_missing_from_bounded_discovery')
 def test_update_data_does_not_shadow_os_inside_build_ferc(self):
  tree=ast.parse((pathlib.Path(__file__).parents[1]/'scripts/update_data.py').read_text())
  fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='build_ferc')
  local_imports=[n for n in ast.walk(fn) if isinstance(n,(ast.Import,ast.ImportFrom)) for a in n.names if a.name=='os']
  self.assertEqual(local_imports,[],"function-local os import makes earlier os references UnboundLocalError")
if __name__=='__main__':unittest.main()
