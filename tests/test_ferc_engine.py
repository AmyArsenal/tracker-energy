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
if __name__=='__main__':unittest.main()
