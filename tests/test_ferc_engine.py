import importlib.util,json,pathlib,sqlite3,tempfile,unittest
spec=importlib.util.spec_from_file_location('fe',pathlib.Path(__file__).parents[1]/'scripts/ferc_engine.py');fe=importlib.util.module_from_spec(spec);spec.loader.exec_module(fe)
class EngineTest(unittest.TestCase):
 def test_fixture_ingest_is_idempotent_and_keeps_all_components(self):
  with tempfile.TemporaryDirectory() as td:
   db=fe.dbopen(pathlib.Path(td)/'x.db'); fixture=str(pathlib.Path(__file__).parent/'fixtures/ferc-search-{day}-page-{page}.json')
   fe.run_search(db,'2026-09-11','2026-09-11',fixture=fixture)
   self.assertEqual(fe.report(db)['documents'],2);self.assertEqual(fe.report(db)['components'],2)
   fe.run_search(db,'2026-09-11','2026-09-11',fixture=fixture)
   self.assertEqual(fe.report(db)['documents'],2);self.assertEqual(fe.report(db)['components'],2)
   r=db.execute("select accession,document_class from ferc_documents where accession='20260911-5304'").fetchone();self.assertEqual(tuple(r),('20260911-5304','Report/Form'))
 def test_search_body_has_no_corpus_filter(self):
  b=fe.body('2026-09-11',3);self.assertEqual(b['searchText'],'');self.assertEqual(b['classTypes'],[]);self.assertEqual(b['docketSearches'],[]);self.assertEqual(b['curPage'],3)
 def test_incremental_overlap_and_exact_evidence(self):
  with tempfile.TemporaryDirectory() as td:
   db=fe.dbopen(pathlib.Path(td)/'x.db');fe.set_state(db,'last_complete_filed_date','2026-09-10');db.commit()
   self.assertEqual(fe.incremental_dates(db,'2026-09-12',2),('2026-09-08','2026-09-12'))
   db.execute("INSERT INTO ferc_documents VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",('a',None,'d','Submittal','09/11/2026',None,None,'Pleading','Answer',None,None,'[]','[]','[]','u','rh','n','n'))
   db.execute("INSERT INTO ferc_components(component_id,accession,source_order,source_sha256,extraction_version,download_status,extraction_status) VALUES(?,?,?,?,?,?,?)",('c','a',0,'abc','v1','downloaded','full-text'))
   db.execute("INSERT INTO pages VALUES(?,?,?,?,?,?,?,?)",('c',1,100,100,'outside the scope',3,'digital_text',1.0))
   toks=[('c',1,0,'outside',.1,.1,.2,.2,0,7),('c',1,1,'the',.21,.1,.25,.2,8,11),('c',1,2,'scope',.26,.1,.32,.2,12,17)]
   db.executemany("INSERT INTO tokens VALUES(?,?,?,?,?,?,?,?,?,?)",toks)
   db.execute("INSERT INTO passages VALUES(?,?,?,?,?,?,?,?,?)",('p','c',1,1,0,2,'outside the scope','h','digital_text'));db.commit()
   eid=fe.create_evidence(db,'c',1,'outside the scope');self.assertTrue(eid.startswith('ev:'))
   boxes=json.loads(db.execute('select boxes_json from evidence').fetchone()[0]);self.assertEqual(len(boxes),1)
if __name__=='__main__':unittest.main()
