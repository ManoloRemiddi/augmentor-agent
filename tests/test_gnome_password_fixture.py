# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Synthetic account restoration refuses concurrent state and unknown retries."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('owned_password_fixture',
    Path(__file__).resolve().parents[1]/'release/gnome-password-fixture.py')
proof = importlib.util.module_from_spec(spec); spec.loader.exec_module(proof)


@unittest.skipUnless(sys.platform.startswith('linux'), 'Owned account fixtures use Linux paths and file guards.')
class PasswordFixtureTests(unittest.TestCase):
    before = b'root:*:20000:0:99999:7:::\naugmentor-proof:$6$original:20001:0:99999:7:::\nother:!:20002:0:99999:7:::\n'

    def test_account_change_preserves_all_other_rows_and_age_fields(self):
        result = proof.changed_account(self.before, '$6$synthetic', '20003')
        self.assertEqual(result, self.before.replace(b'$6$original:20001', b'$6$synthetic:20003'))
        for raw in (self.before.replace(b'augmentor-proof:', b'foreign:'),
                    self.before+self.before.splitlines(keepends=True)[1],
                    self.before.replace(b'augmentor-proof:$6$original:20001:0:99999:7:::', b'augmentor-proof:short')):
            with self.subTest(raw=raw),self.assertRaises(ValueError):proof.account_rows(raw)

    def test_concurrent_shadow_change_refuses_every_restore_command(self):
        after = proof.changed_account(self.before, '$6$synthetic', '20003')
        intermediate = proof.changed_account(self.before, '$6$original', '20003')
        files = {'before.shadow':self.before, 'after.shadow':after, 'intermediate.shadow':intermediate,
                 'shadow':after.replace(b'other:!', b'other:$6$changed')}
        with patch.object(proof, 'SHADOW', Path('shadow')),\
                patch.object(proof, 'private_read', side_effect=lambda path:files[path.name]),\
                patch.object(proof, 'dispatch_once') as dispatch:
            with self.assertRaisesRegex(ValueError, 'Concurrent or uncertain'):
                proof.restore(Path('fixture'), {'phase':'installed'})
            dispatch.assert_not_called()

    def test_observed_password_restore_finishes_only_distinct_age_operation(self):
        after = proof.changed_account(self.before, '$6$synthetic', '20003')
        intermediate = proof.changed_account(self.before, '$6$original', '20003')
        files = {'before.shadow':self.before, 'after.shadow':after, 'intermediate.shadow':intermediate, 'shadow':intermediate}
        calls = []
        def dispatch(root, record, phase, command, text):
            calls.append((phase,command,text));record['phase']=phase;files['shadow']=self.before
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'synthetic-password').write_text('synthetic')
            record={'phase':'restore-password-pending','originalDay':'20001'}
            with patch.object(proof, 'SHADOW', Path('shadow')),\
                    patch.object(proof, 'private_read', side_effect=lambda path:files[path.name]),\
                    patch.object(proof, 'dispatch_once', side_effect=dispatch):proof.restore(root,record)
            self.assertEqual(calls,[('restore-age-pending',['/usr/bin/chage','-d','20001','augmentor-proof'],None)])
            self.assertEqual(record['phase'],'restored');self.assertFalse((root/'synthetic-password').exists())

    def test_unknown_age_operation_is_never_repeated(self):
        files={'before.shadow':self.before,
               'after.shadow':proof.changed_account(self.before,'$6$synthetic','20003'),
               'intermediate.shadow':proof.changed_account(self.before,'$6$original','20003')}
        files['shadow']=files['intermediate.shadow']
        with patch.object(proof,'SHADOW',Path('shadow')),\
                patch.object(proof,'private_read',side_effect=lambda path:files[path.name]),\
                patch.object(proof,'dispatch_once') as dispatch:
            with self.assertRaisesRegex(ValueError,'uncertain password state'):
                proof.restore(Path('fixture'),{'phase':'restore-age-pending','originalDay':'20001'})
            dispatch.assert_not_called()

    def test_invalid_request_refuses_before_hash_derivation_or_account_dispatch(self):
        with patch.object(proof, 'private_read', return_value=self.before),\
                patch.object(proof.subprocess, 'run') as run:
            for request in (None, {}, {'expectedOriginalPasswordHash':'$6$foreign'},
                            {'expectedOriginalPasswordHash':'$6$original','syntheticPassword':'invalid'}):
                with self.subTest(request=request), self.assertRaises(ValueError):proof.preparation_plan(request)
            run.assert_not_called()

    def test_changed_account_between_plan_and_dispatch_refuses_without_writes(self):
        plan=(self.before, b'after', b'intermediate', 'synthetic', '20001', '$6$new')
        with patch.object(proof, 'private_read', return_value=self.before+b'foreign:!:0:0:0:0:::\n'),\
                patch.object(proof, 'private_write') as write, patch.object(proof, 'dispatch_once') as dispatch:
            with self.assertRaisesRegex(ValueError, 'changed after preparation'):
                proof.prepare(Path('fixture'), {'phase':'created'}, plan)
            write.assert_not_called(); dispatch.assert_not_called()

    def test_real_child_timeout_retains_pending_receipt_and_one_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);script=root/'child.py';count=root/'count'
            script.write_text('import pathlib,time\npathlib.Path('+repr(str(count))+').write_text("one")\ntime.sleep(2)\n')
            actual=subprocess.run
            def bounded(command,**kwargs):
                kwargs['timeout']=.5;return actual([sys.executable,str(script)],**kwargs)
            record={'phase':'created','dispatches':[]}
            with patch.object(proof.subprocess,'run',side_effect=bounded) as run,\
                    self.assertRaises(subprocess.TimeoutExpired):
                proof.dispatch_once(root,record,'prepare-pending',['synthetic-command'],'synthetic stdin')
            self.assertEqual(run.call_count,1);self.assertEqual(count.read_text(),'one')
            retained=json.loads((root/'run.json').read_text())
            self.assertEqual(retained['phase'],'prepare-pending');self.assertEqual(retained['dispatches'],['prepare-pending'])


if __name__=='__main__':unittest.main()
