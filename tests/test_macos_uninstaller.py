# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import fcntl
import importlib.util
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('uninstaller',Path(__file__).resolve().parents[1]/'scripts/uninstall-macos.py')
uninstaller=importlib.util.module_from_spec(spec);spec.loader.exec_module(uninstaller)


class MacUninstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.app=self.root/'Applications/Desktop.app';self.app.mkdir(parents=True)
        (self.app/'binary').write_text('application')
        self.support=self.root/'support';self.trash=self.root/'Trash'
        self.manifest=self.support/'Chromium/NativeMessagingHosts/com.augmentor.agent.json'
        self.manifest.parent.mkdir(parents=True)
        self.value={'path':str(self.app/'Contents/MacOS/augmentor-browser-host')}
        self.manifest.write_text(json.dumps(self.value))
        self.patches=[patch.object(uninstaller.installer,'validate'),patch.object(uninstaller.browser,'manifest',return_value=self.value),
                      patch.object(Path,'home',return_value=self.root),patch.dict(os.environ,{'XDG_RUNTIME_DIR':str(self.root)})]
        for item in self.patches:item.start()

    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        self.temp.cleanup()

    def test_uninstall_retains_app_in_trash_and_preserves_user_data(self):
        user_data=self.root/'conversations.json';user_data.write_text('private data')
        other=self.support/'Google/Chrome/NativeMessagingHosts/com.augmentor.agent.json'
        other.parent.mkdir(parents=True);other.write_text('{"path":"other-installation"}')
        result=uninstaller.uninstall(self.app,self.trash,self.support)
        self.assertFalse(self.app.exists());self.assertFalse(self.manifest.exists())
        self.assertEqual(user_data.read_text(),'private data')
        self.assertTrue(other.exists());self.assertIn(str(other),result['retainedRegistrations'])
        receipt=json.loads(Path(result['receipt']).read_text())
        for entry in receipt['moves']:self.assertTrue(Path(entry['retained']).exists())
        self.assertFalse(receipt['userDataRemoved'])

    def test_active_task_prevents_any_removal(self):
        descriptor=os.open(self.root/'installation.lock',os.O_CREAT|os.O_RDWR,0o600)
        try:
            fcntl.flock(descriptor,fcntl.LOCK_SH|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):uninstaller.uninstall(self.app,self.trash,self.support)
            self.assertTrue(self.app.exists());self.assertTrue(self.manifest.exists())
            receipts=list(self.trash.glob('*/receipt.json'))
            self.assertEqual(len(receipts),1)
            self.assertEqual(list(receipts[0].parent.iterdir()),receipts)
        finally:os.close(descriptor)

    def test_failed_app_move_rolls_back_registration(self):
        rename=Path.rename
        def fail(path,destination):
            if path==self.app:raise OSError('Injected move failure')
            return rename(path,destination)
        with patch.object(Path,'rename',fail),self.assertRaisesRegex(OSError,'Injected'):
            uninstaller.uninstall(self.app,self.trash,self.support)
        self.assertTrue(self.app.exists());self.assertEqual(json.loads(self.manifest.read_text()),self.value)

    def test_active_task_refusal_resumes_previous_shortcut_service(self):
        login=self.root/'Library/LaunchAgents'/f'{uninstaller.shortcut.LABEL}.plist'
        login.parent.mkdir(parents=True);login.write_bytes(plistlib.dumps(uninstaller.shortcut.definition(self.app)))
        descriptor=os.open(self.root/'installation.lock',os.O_CREAT|os.O_RDWR,0o600)
        try:
            fcntl.flock(descriptor,fcntl.LOCK_SH|fcntl.LOCK_NB)
            with patch.object(uninstaller.shortcut,'manage',return_value={'loaded':True}) as manage,patch.object(uninstaller.shortcut,'validate'):
                with self.assertRaises(BlockingIOError):uninstaller.uninstall(self.app,self.trash,self.support)
            self.assertEqual([call.args[1] for call in manage.call_args_list],['status','stop','start'])
            self.assertTrue(login.exists());self.assertTrue(self.app.exists())
        finally:os.close(descriptor)

    def test_symlink_app_is_refused(self):
        link=self.root/'Link.app';link.symlink_to(self.app,target_is_directory=True)
        with self.assertRaises(ValueError):uninstaller.uninstall(link,self.trash,self.support)
        self.assertTrue(self.app.exists())

    def test_restore_refuses_new_app_before_moving_any_registration(self):
        result=uninstaller.uninstall(self.app,self.trash,self.support)
        self.app.mkdir();(self.app/'user-file').write_text('new installation')
        with self.assertRaisesRegex(ValueError,'changed'):
            uninstaller.restore(Path(result['receipt']),self.support)
        self.assertEqual((self.app/'user-file').read_text(),'new installation')
        self.assertFalse(self.manifest.exists())

    def test_completed_restore_can_retry_while_app_is_running(self):
        result=uninstaller.uninstall(self.app,self.trash,self.support)
        receipt=Path(result['receipt'])
        uninstaller.restore(receipt,self.support)
        descriptor=os.open(self.root/'installation.lock',os.O_RDWR)
        try:
            fcntl.flock(descriptor,fcntl.LOCK_SH|fcntl.LOCK_NB)
            uninstaller.restore(receipt,self.support)
            self.assertEqual((self.app/'binary').read_text(),'application')
            self.assertTrue(self.manifest.exists())
        finally:os.close(descriptor)

    def test_restore_still_requires_exclusive_access_to_move_files(self):
        result=uninstaller.uninstall(self.app,self.trash,self.support)
        descriptor=os.open(self.root/'installation.lock',os.O_RDWR)
        try:
            fcntl.flock(descriptor,fcntl.LOCK_SH|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                uninstaller.restore(Path(result['receipt']),self.support)
            self.assertFalse(self.app.exists());self.assertFalse(self.manifest.exists())
        finally:os.close(descriptor)

    def test_restore_after_process_exit_at_each_move_boundary(self):
        for boundary in ('manifest','app'):
            with self.subTest(boundary=boundary):
                code='''import importlib.util,json,os,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("uninstaller",sys.argv[1])
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
root=Path(sys.argv[2]);boundary=sys.argv[3]
Path.home=classmethod(lambda cls:root)
os.environ["XDG_RUNTIME_DIR"]=str(root)
m.installer.validate=lambda *a,**kw:None
app=root/"Applications/Desktop.app"
manifest=root/"support/Chromium/NativeMessagingHosts/com.augmentor.agent.json"
value=json.loads(manifest.read_text());m.browser.manifest=lambda app:value
rename=Path.rename
def interrupted(self,target):
    result=rename(self,target)
    if self==(manifest if boundary=="manifest" else app):os._exit(9)
    return result
Path.rename=interrupted
m.uninstall(app,root/"Trash",root/"support")
'''
                before=set(self.trash.glob('*/receipt.json')) if self.trash.exists() else set()
                result=subprocess.run([sys.executable,'-c',code,uninstaller.__file__,str(self.root),boundary])
                self.assertEqual(result.returncode,9)
                receipt=(set(self.trash.glob('*/receipt.json'))-before).pop()
                uninstaller.restore(receipt,self.support)
                self.assertEqual((self.app/'binary').read_text(),'application')
                self.assertEqual(json.loads(self.manifest.read_text()),self.value)
                uninstaller.restore(receipt,self.support)

    def test_retry_after_process_exit_during_restore(self):
        for boundary in ('app','manifest'):
            with self.subTest(boundary=boundary):
                result=uninstaller.uninstall(self.app,self.trash,self.support)
                receipt=Path(result['receipt'])
                code='''import importlib.util,os,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("uninstaller",sys.argv[1])
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
root=Path(sys.argv[2]);receipt=Path(sys.argv[3]);boundary=sys.argv[4]
Path.home=classmethod(lambda cls:root)
os.environ["XDG_RUNTIME_DIR"]=str(root)
m.installer.validate=lambda *a,**kw:None
target=root/("Applications/Desktop.app" if boundary=="app" else "support/Chromium/NativeMessagingHosts/com.augmentor.agent.json")
rename=Path.rename
def interrupted(self,destination):
    result=rename(self,destination)
    if destination==target:os._exit(19)
    return result
Path.rename=interrupted
m.restore(receipt,root/"support")
'''
                exited=subprocess.run([sys.executable,'-c',code,uninstaller.__file__,str(self.root),str(receipt),boundary])
                self.assertEqual(exited.returncode,19)
                uninstaller.restore(receipt,self.support)
                self.assertEqual((self.app/'binary').read_text(),'application')
                self.assertEqual(json.loads(self.manifest.read_text()),self.value)
                self.assertTrue(receipt.exists())


if __name__=='__main__':unittest.main()
