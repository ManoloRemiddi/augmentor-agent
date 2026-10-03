# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
import stat
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
import urllib.error
import urllib.request
from unittest.mock import Mock

spec=importlib.util.spec_from_file_location('managed_baseline',Path(__file__).resolve().parents[1]/'release/prove-published-linux-managed-baseline.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ManagedBaselineTests(unittest.TestCase):
    def test_baseline_input_sha_and_private_metadata_are_required_before_decode(self):
        path=Mock();path.parent=Path('/synthetic');path.read_text.return_value='{"known": true}'
        helper=SimpleNamespace(private_parents=Mock());sha=Mock(return_value='reviewed')
        good=SimpleNamespace(st_mode=stat.S_IFREG|0o600,st_uid=1000,st_nlink=1,st_size=15)
        path.lstat.return_value=good
        self.assertEqual(module.retained_json(path,'reviewed',helper,sha),{'known':True})
        for changes in ({'st_uid':1001},{'st_mode':stat.S_IFLNK|0o600},{'st_mode':stat.S_IFREG|0o644},{'st_nlink':2}):
            path.lstat.return_value=SimpleNamespace(**{**vars(good),**changes});path.read_text.reset_mock()
            with self.subTest(changes=changes),self.assertRaises(ValueError):module.retained_json(path,'reviewed',helper,sha)
            path.read_text.assert_not_called()
        path.lstat.return_value=good;sha.return_value='changed';path.read_text.reset_mock()
        with self.assertRaises(ValueError):module.retained_json(path,'reviewed',helper,sha)
        path.read_text.assert_not_called()

    def test_native_identity_after_lease_requires_exact_source_version_target(self):
        good={'version':'0.2.12','source':{'commit':'reviewed','dirty':False},'target':'debian13-amd64'}
        module.native_identity(good,'reviewed')
        for changed in ({'version':'0.2.13'},{'source':{'commit':'other','dirty':False}},{'source':{'commit':'reviewed','dirty':True}},{'target':'ubuntu24.04-amd64'}):
            with self.subTest(changed=changed),self.assertRaises(ValueError):module.native_identity({**good,**changed},'reviewed')

    def test_unexpected_model_post_is_recorded_and_rejected(self):
        requests=[];server=module.reject_model_server(requests,0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            req=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+'/v1/chat/completions',data=b'{}')
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(req,timeout=2)
            self.assertEqual(error.exception.code,503);self.assertEqual(requests,['/v1/chat/completions'])
        finally:server.shutdown();server.server_close();thread.join(timeout=2)

    def test_only_intended_selection_change_allowed(self):
        before={'.local/share/augmentor/desktop.json':'legacy','provider':'saved','installation':'original'}
        module.settings_unchanged_except_selection(before,{**before,'.local/share/augmentor/desktop.json':'managed'})
        for after in ({**before,'provider':'changed'},{**before,'installation':'changed'}, {'provider':'saved'}):
            with self.subTest(after=after),self.assertRaises(ValueError):module.settings_unchanged_except_selection(before,after)

    def test_dispatch_intent_is_durable_before_exact_normal_command(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root);saved=[];record={'pendingDeployment':None}
            base=SimpleNamespace(HOME=folder,atomic=lambda path,value:saved.append(json.loads(json.dumps(value))))
            def invoke(argv,**kwargs):
                self.assertEqual(saved[-1]['pendingDeployment'],{'label':'stage','argv':['normal-update','stage']})
                self.assertEqual(argv,['normal-update','stage']);return SimpleNamespace(returncode=0)
            module.transaction(base,folder,record,'stage',['normal-update','stage'],{},invoke)
            self.assertIsNone(record['pendingDeployment']);self.assertEqual(record['completedDeployments'],[{'label':'stage','exitCode':0}])

    def test_unknown_command_remains_pending_and_cannot_replay(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root);record={'pendingDeployment':None};base=SimpleNamespace(HOME=folder,atomic=Mock())
            invoke=Mock(side_effect=TimeoutError('unknown command outcome'))
            with self.assertRaises(TimeoutError):module.transaction(base,folder,record,'activate',['normal-update','activate'],{},invoke)
            self.assertEqual(record['pendingDeployment']['label'],'activate')
            with self.assertRaises(ValueError):module.transaction(base,folder,record,'activate',['normal-update','activate'],{},invoke)
            invoke.assert_called_once()

    def test_known_nonzero_refuses_dependent_phase(self):
        with tempfile.TemporaryDirectory() as root:
            record={'pendingDeployment':None};folder=Path(root);base=SimpleNamespace(HOME=folder,atomic=Mock())
            invoke=Mock(return_value=SimpleNamespace(returncode=1))
            with self.assertRaises(ValueError):module.transaction(base,folder,record,'stage',['normal-update','stage'],{},invoke)
            self.assertIsNone(record['pendingDeployment']);self.assertEqual(record['completedDeployments'],[{'label':'stage','exitCode':1}])
            invoke.assert_called_once()


if __name__=='__main__':unittest.main()
