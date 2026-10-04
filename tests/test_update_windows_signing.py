# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Publisher policy refusal plus separately gated real Windows trust inspection."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from updates import windows_signing


class SigningPolicyTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);(self.root/'release/windows').mkdir(parents=True)
        self.file=self.root/'release/windows/signing.json'
        self.value={'schema':'augmentor-windows-signing/1','enabled':True,'publicKeySHA256':['a'*64]}
        self.report={'schema':'augmentor-windows-publisher/1','trusted':True,'timestamped':True,'publicKeySHA256':'a'*64}
        self.save()

    def save(self):self.file.write_text(json.dumps(self.value))

    def test_missing_disabled_empty_duplicate_or_malformed_policy_never_inspects_target(self):
        self.file.unlink()
        with patch.object(windows_signing,'inspect') as inspector:
            with self.assertRaises(OSError):windows_signing.verify(self.root,self.root/'never-executed.exe')
            for changed in ({'enabled':False},{'enabled':'true'},{'publicKeySHA256':[]},
                    {'publicKeySHA256':['a'*64,'a'*64]},{'publicKeySHA256':['bad']},{'unknown':True}):
                with self.subTest(changed=changed):
                    self.file.write_text(json.dumps(self.value|changed))
                    with self.assertRaises(ValueError):windows_signing.verify(self.root,self.root/'never-executed.exe')
            inspector.assert_not_called()

    def test_exact_publisher_pin_and_unchanged_source_policy_are_required(self):
        with patch.object(windows_signing,'inspect',return_value=self.report):
            self.assertTrue(windows_signing.verify(self.root,self.root/'inert.exe'))
        with patch.object(windows_signing,'inspect',return_value=self.report|{'publicKeySHA256':'b'*64}):
            with self.assertRaisesRegex(ValueError,'another publisher'):windows_signing.verify(self.root,self.root/'inert.exe')
        def changed(*_):
            self.value['publicKeySHA256'].append('b'*64);self.save();return self.report
        with patch.object(windows_signing,'inspect',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'changed'):windows_signing.verify(self.root,self.root/'inert.exe')

    def test_fixed_bundled_verifier_strips_module_injection_and_validates_bounded_report(self):
        (self.root/'powershell').mkdir();(self.root/'powershell/pwsh.exe').write_bytes(b'Inert fixed helper.')
        (self.root/'scripts').mkdir();(self.root/'scripts/verify-windows-publisher.ps1').write_bytes(b'Inert fixture.')
        result=subprocess.CompletedProcess([],0,json.dumps(self.report).encode(),b'')
        target=self.root/'literal [target]; never executed.exe'
        with patch.object(windows_signing.sys,'platform','win32'),patch.dict(os.environ,{'PSModulePath':'foreign','PYTHONPATH':'foreign'}),patch.object(windows_signing.subprocess,'run',return_value=result) as runner:
            self.assertEqual(windows_signing.inspect(self.root,target),self.report)
            args=runner.call_args.args[0]
            self.assertEqual(args[0],str(self.root/'powershell/pwsh.exe'))
            self.assertEqual(args[-2:],['-LiteralPath',str(target)])
            self.assertNotIn('-Command',args)
            self.assertEqual(runner.call_args.kwargs['env']['PSModulePath'],str(self.root/'powershell/Modules'))
            self.assertNotIn('PYTHONPATH',runner.call_args.kwargs['env'])
            self.assertEqual(runner.call_args.kwargs['timeout'],30)
            for output in (self.report|{'trusted':'true'},self.report|{'timestamped':False},self.report|{'extra':True}):
                runner.return_value=subprocess.CompletedProcess([],0,json.dumps(output).encode(),b'')
                with self.assertRaises(ValueError):windows_signing.inspect(self.root,target)
            runner.return_value=subprocess.CompletedProcess([],1,b'',b'Never echo private verifier diagnostics.')
            with self.assertRaisesRegex(ValueError,'could not verify'):windows_signing.inspect(self.root,target)
            runner.return_value=subprocess.CompletedProcess([],0,b' '*4097,b'')
            with self.assertRaises(ValueError):windows_signing.inspect(self.root,target)


NATIVE=os.environ.get('AUGMENTOR_WINDOWS_SIGNING_PROOF_ROOT')
@unittest.skipUnless(sys.platform=='win32' and NATIVE,'Requires the dedicated pinned Windows trust inspection payload.')
class NativePublisherTests(unittest.TestCase):
    def test_actual_timestamped_node_publisher_wrong_key_and_damaged_file_without_execution(self):
        root=Path(NATIVE).resolve();target=root/'node/node.exe'
        before=hashlib.sha256(target.read_bytes()).hexdigest()
        report=windows_signing.inspect(root,target)
        self.assertTrue(report['trusted']);self.assertTrue(report['timestamped'])
        # Qualification-only pins from the independently observed stock Node
        # signer. No Augmentor policy/certificate/store is installed or changed.
        value={'schema':'augmentor-windows-signing/1','enabled':True,'publicKeySHA256':[report['publicKeySHA256']]}
        with patch.object(windows_signing,'policy',return_value=value):
            self.assertTrue(windows_signing.verify(root,target))
        with patch.object(windows_signing,'policy',return_value=value|{'publicKeySHA256':['0'*64]}):
            with self.assertRaisesRegex(ValueError,'another publisher'):windows_signing.verify(root,target)
        with tempfile.TemporaryDirectory() as directory:
            damaged=Path(directory)/'damaged-node.exe';shutil.copyfile(target,damaged)
            with damaged.open('r+b') as stream:
                stream.seek(300);original=stream.read(1);stream.seek(300);stream.write(bytes([original[0]^1]))
            with self.assertRaises(ValueError):windows_signing.inspect(root,damaged)
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),before)


if __name__=='__main__':unittest.main()
