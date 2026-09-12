import base64,hashlib,importlib.util,json,pathlib,tarfile,tempfile,unittest
P=pathlib.Path(__file__).resolve().parents[1]/'scripts/pull_feature_channel.py'
spec=importlib.util.spec_from_file_location('pull_feature_channel',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class FeatureChannelTest(unittest.TestCase):
 def test_latest_owner_manifest_wins_and_untrusted_is_ignored(self):
  good={'version':'2','sha256':'a'*64,'bundle_base64':'eA=='}
  comments=[
   {'user':{'login':'AmyArsenal'},'author_association':'OWNER','body':m.MARKER+'\n```json\n'+json.dumps(good)+'\n```'},
   {'user':{'login':'attacker'},'author_association':'NONE','body':m.MARKER+'\n'+json.dumps({'version':'9','sha256':'b'*64,'bundle_base64':'eA=='})}]
  self.assertEqual(m.load_manifest(json.dumps(comments).encode())['version'],'2')
 def test_inline_bundle_decodes_and_checksum_is_stable(self):
  raw=b'feature bytes';man={'bundle_base64':base64.b64encode(raw).decode()}
  self.assertEqual(m.manifest_blob(man),raw)
  self.assertEqual(hashlib.sha256(m.manifest_blob(man)).hexdigest(),hashlib.sha256(raw).hexdigest())
 def test_non_owner_channel_rejected(self):
  raw=json.dumps([{'user':{'login':'AmyArsenal'},'author_association':'MEMBER','body':m.MARKER+'\n{}'}]).encode()
  with self.assertRaises(RuntimeError):m.load_manifest(raw)
if __name__=='__main__':unittest.main()
