import importlib.util,json,pathlib,tempfile,unittest
R=pathlib.Path(__file__).parents[1];s=importlib.util.spec_from_file_location('rs',R/'scripts/refresh_sources.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class RefreshIsolationTest(unittest.TestCase):
 def test_failure_restores_last_good(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);p=root/'out.json';p.write_text('{"items":[{"id":1}]}');old=m.ROOT;m.ROOT=root
   try:
    c={'id':'x','cmd':['python3','-c','open("out.json","w").write("bad");raise SystemExit(2)'],'outputs':['out.json'],'checks':{'out.json':('items',1)}}
    r=m.run_connector(c,root/'b',10);self.assertEqual(r['status'],'degraded');self.assertEqual(json.loads(p.read_text())['items'][0]['id'],1)
   finally:m.ROOT=old
 def test_invalid_success_restores(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);p=root/'out.json';p.write_text('{"items":[1]}');old=m.ROOT;m.ROOT=root
   try:
    c={'id':'x','cmd':['python3','-c','open("out.json","w").write("{}")'],'outputs':['out.json'],'checks':{'out.json':('items',1)}}
    r=m.run_connector(c,root/'b',10);self.assertEqual(r['status'],'degraded');self.assertEqual(json.loads(p.read_text()),{'items':[1]})
   finally:m.ROOT=old
 def test_no_baseline_is_fatal(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);old=m.ROOT;m.ROOT=root
   try:
    c={'id':'x','cmd':['python3','-c','raise SystemExit(2)'],'outputs':['missing.json'],'checks':{}}
    self.assertEqual(m.run_connector(c,root/'b',10)['status'],'failed')
   finally:m.ROOT=old
if __name__=='__main__':unittest.main()
