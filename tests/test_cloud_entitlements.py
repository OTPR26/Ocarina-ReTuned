import importlib.util
import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('cloud_entitlements',Path(__file__).parents[1]/'tools/native/apple/prepare_cloud_entitlements.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Entitlements(unittest.TestCase):
    def profile(self):
        return {'Entitlements':{'application-identifier':'TESTTEAM.io.github.otpr26.ocarinaretuned','com.apple.developer.icloud-container-identifiers':['iCloud.org.example.retuned'],'com.apple.developer.icloud-services':'*','com.apple.developer.icloud-container-environment':['Development','Production']}}
    def prepare(self,profile,environment='Development'):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'entitlements.plist'
            with patch.object(module.subprocess,'check_output',return_value=plistlib.dumps(profile)):
                module.prepare(Path('profile'),'iCloud.org.example.retuned',target,environment)
            return plistlib.loads(target.read_bytes())
    def test_explicit_profile_narrows_capabilities(self):
        result=self.prepare(self.profile())
        self.assertEqual(result['com.apple.developer.icloud-services'],['CloudKit'])
        self.assertEqual(result['com.apple.developer.icloud-container-environment'],'Development')
    def test_wildcard_app_rejected(self):
        profile=self.profile();profile['Entitlements']['application-identifier']='TESTTEAM.*'
        with self.assertRaises(ValueError):self.prepare(profile)
    def test_wrong_container_rejected(self):
        profile=self.profile();profile['Entitlements']['com.apple.developer.icloud-container-identifiers']=['iCloud.other']
        with self.assertRaises(ValueError):self.prepare(profile)
    def test_wrong_environment_rejected(self):
        profile=self.profile();profile['Entitlements']['com.apple.developer.icloud-container-environment']='Development'
        with self.assertRaises(ValueError):self.prepare(profile,'Production')
