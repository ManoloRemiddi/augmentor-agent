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
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('mac_installer', Path(__file__).resolve().parents[1]/'scripts/install-macos.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class MacInstallerTests(unittest.TestCase):
    def test_default_prefers_existing_installation_and_refuses_ambiguous_duplicates(self):
        name='Augmentor Agent Desktop.app';home=Path('/fixture-user')
        with patch.object(Path,'home',return_value=home),patch.object(Path,'is_symlink',return_value=False),patch.object(installer.os,'access',return_value=True):
            for existing in (Path('/Applications')/name,home/'Applications'/name):
                with patch.object(Path,'exists',lambda p:p==existing):
                    self.assertEqual(installer.default_destination(name),existing)
            with patch.object(Path,'exists',return_value=True),self.assertRaisesRegex(ValueError,'More than one'):
                installer.default_destination(name)
            with patch.object(Path,'exists',return_value=False):
                self.assertEqual(installer.default_destination(name),Path('/Applications')/name)
                with patch.object(installer.os,'access',return_value=False):
                    self.assertEqual(installer.default_destination(name),home/'Applications'/name)

    def test_destination_parent_rejects_symlinks_and_public_write_access(self):
        with tempfile.TemporaryDirectory() as directory:
            parent=Path(directory);installer.validate_parent(parent)
            link=parent/'link';link.symlink_to(parent,target_is_directory=True)
            with self.assertRaises(ValueError):installer.validate_parent(link)
            parent.chmod(0o777)
            with self.assertRaises(ValueError):installer.validate_parent(parent)

    def test_companion_identity_requires_matching_release_component(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Path(directory)/'Companion.app';root=app/'Contents/Resources/app';root.mkdir(parents=True)
            (app/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'com.augmentor.Agent.Companion'}))
            release=root/'release.json';release.write_text(json.dumps({'target':'macos-arm64','component':'companion'}))
            self.assertEqual(installer.validate(app,verify=False)['component'],'companion')
            release.write_text(json.dumps({'target':'macos-arm64','component':'desktop'}))
            with self.assertRaisesRegex(ValueError,'do not match'):installer.validate(app,verify=False)

    def test_separate_companion_does_not_stop_desktop_shortcut(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(Path,'home',return_value=Path(directory)):
            home=Path(directory);login=home/'Library/LaunchAgents/com.augmentor.Agent.shortcut.plist'
            login.parent.mkdir(parents=True);login.write_bytes(plistlib.dumps({'ProgramArguments':['desktop']}))
            staged=home/'candidate.app';release=staged/'Contents/Resources/app/release.json'
            release.parent.mkdir(parents=True);release.write_text(json.dumps({'component':'companion'}))
            registrar=Mock();registrar.definition.return_value={'ProgramArguments':['companion']}
            with patch.object(installer,'shortcut_registrar',return_value=registrar):
                with installer.paused_shortcut(home/'Companion.app',staged):pass
            registrar.manage.assert_not_called()

    def test_process_exit_during_shortcut_stop_or_promotion_preserves_resume_intent(self):
        for boundary in ('stop','backup','promoted'):
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);destination=root/'installed.app';destination.mkdir()
                registration=root/'Library/LaunchAgents/com.augmentor.Agent.shortcut.plist'
                registration.parent.mkdir(parents=True);registration.write_text('owned fixture')
                staged=root/'staged.app';retry=root/'retry.app'
                for app in (staged,retry):
                    service=app/'Contents/Resources/app/apps/native/augmentor_linux/macos_shortcut_service.py'
                    service.parent.mkdir(parents=True);service.touch()
                code='''import importlib.util,os,sys
from pathlib import Path
from types import SimpleNamespace
spec=importlib.util.spec_from_file_location("installer",sys.argv[1])
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
root=Path(sys.argv[2]);boundary=sys.argv[3]
Path.home=classmethod(lambda cls:root)
os.environ["XDG_RUNTIME_DIR"]=str(root)
def manage(app,action):
    if action=="status":return {"loaded":True}
    if action=="stop" and boundary=="stop":os._exit(9)
    if action=="start":raise AssertionError("Exited process resumed unexpectedly")
m.shortcut_registrar=lambda:SimpleNamespace(manage=manage,validate=lambda app:None)
rename=Path.rename
def interrupted(self,target):
    result=rename(self,target)
    if (boundary=="backup" and self.name=="installed.app") or (boundary=="promoted" and self.name=="staged.app"):os._exit(9)
    return result
Path.rename=interrupted
with m.installation_transaction(root/"installed.app",root/"staged.app"):
    m.replace(root/"staged.app",root/"installed.app")
'''
                result=subprocess.run([sys.executable,'-c',code,installer.__file__,directory,boundary])
                self.assertEqual(result.returncode,9)
                pending=installer.shortcut_resume_path(destination)
                self.assertTrue(pending.exists())
                self.assertEqual(pending.stat().st_mode & 0o777,0o600)
                registrar=Mock();registrar.manage.return_value={'loaded':False}
                with patch.object(Path,'home',return_value=root),patch.dict(os.environ,{'XDG_RUNTIME_DIR':directory}),patch.object(installer,'shortcut_registrar',return_value=registrar):
                    with installer.installation_transaction(destination,retry):
                        installer.recover(destination)
                self.assertTrue(destination.exists())
                self.assertFalse(pending.exists())
                self.assertFalse(installer.journal_path(destination).exists())
                self.assertEqual([call.args[1] for call in registrar.manage.call_args_list],['status','start'])

    def test_changed_registration_refuses_recovery_without_stopping_service(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);destination=root/'installed.app';staged=root/'staged.app'
            registration=root/'Library/LaunchAgents/com.augmentor.Agent.shortcut.plist'
            registration.parent.mkdir(parents=True);registration.write_text('original')
            service=staged/'Contents/Resources/app/apps/native/augmentor_linux/macos_shortcut_service.py'
            service.parent.mkdir(parents=True);service.touch()
            installer.resume_intent(destination,registration,create=True)
            registration.write_text('changed')
            registrar=Mock();registrar.manage.return_value={'loaded':True}
            with patch.object(Path,'home',return_value=root),patch.dict(os.environ,{'XDG_RUNTIME_DIR':directory}),patch.object(installer,'shortcut_registrar',return_value=registrar):
                with self.assertRaisesRegex(ValueError,'changed'):
                    with installer.installation_transaction(destination,staged):self.fail('Entered changed registration')
            self.assertTrue(installer.shortcut_resume_path(destination).exists())
            self.assertEqual([call.args[1] for call in registrar.manage.call_args_list],['status'])

    def test_shortcut_resumes_after_releasing_write_lease_even_on_failure(self):
        for failure in (False, True):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root=Path(directory);destination=root/'installed.app';staged=root/'staged.app'
                registration=root/'Library/LaunchAgents/com.augmentor.Agent.shortcut.plist'
                registration.parent.mkdir(parents=True);registration.write_text('fixture')
                service=staged/'Contents/Resources/app/apps/native/augmentor_linux/macos_shortcut_service.py'
                service.parent.mkdir(parents=True);service.touch()
                registrar=Mock();actions=[]
                def manage(app, action):
                    actions.append(action)
                    if action=='status':return {'loaded':True}
                    if action=='start':
                        fd=installer.installation_lock();os.close(fd)
                registrar.manage.side_effect=manage
                with patch.object(Path,'home',return_value=root),patch.dict(os.environ,{'XDG_RUNTIME_DIR':directory}),patch.object(installer,'shortcut_registrar',return_value=registrar):
                    try:
                        with installer.installation_transaction(destination,staged):
                            self.assertEqual(actions,['status','stop'])
                            with self.assertRaises(BlockingIOError):
                                with installer.installation_transaction(destination,staged):self.fail('Second installer entered')
                            if failure:raise ValueError('Injected promotion failure')
                    except ValueError:
                        if not failure:raise
                self.assertEqual(actions,['status','stop','start'])
                registrar.validate.assert_called_once_with(destination)

    def test_active_task_refuses_update_and_restores_shortcut(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);registration=root/'Library/LaunchAgents/com.augmentor.Agent.shortcut.plist'
            registration.parent.mkdir(parents=True);registration.touch()
            staged=root/'staged.app';service=staged/'Contents/Resources/app/apps/native/augmentor_linux/macos_shortcut_service.py'
            service.parent.mkdir(parents=True);service.touch()
            registrar=Mock();registrar.manage.return_value={'loaded':True}
            fd=os.open(root/'installation.lock',os.O_CREAT|os.O_RDWR,0o600)
            try:
                fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
                with patch.object(Path,'home',return_value=root),patch.dict(os.environ,{'XDG_RUNTIME_DIR':directory}),patch.object(installer,'shortcut_registrar',return_value=registrar):
                    with self.assertRaises(BlockingIOError):
                        with installer.installation_transaction(root/'installed.app',staged):self.fail('Active task was ignored')
                self.assertEqual([call.args[1] for call in registrar.manage.call_args_list],['status','stop','start'])
            finally:os.close(fd)

    def test_paused_registration_is_not_started_by_update(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);registration=root/'Library/LaunchAgents/com.augmentor.Agent.shortcut.plist'
            registration.parent.mkdir(parents=True);registration.touch()
            staged=root/'staged.app';service=staged/'Contents/Resources/app/apps/native/augmentor_linux/macos_shortcut_service.py'
            service.parent.mkdir(parents=True);service.touch()
            registrar=Mock();registrar.manage.return_value={'loaded':False}
            with patch.object(Path,'home',return_value=root),patch.dict(os.environ,{'XDG_RUNTIME_DIR':directory}),patch.object(installer,'shortcut_registrar',return_value=registrar):
                with installer.installation_transaction(root/'installed.app',staged):pass
            self.assertEqual([call.args[1] for call in registrar.manage.call_args_list],['status'])

    def test_process_exit_after_backup_is_recovered(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); old=root/'installed.app'; new=root/'candidate.app'
            old.mkdir();new.mkdir();(old/'version').write_text('old')
            code='''import importlib.util,os,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("installer",sys.argv[1])
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original=Path.rename
def interrupted(self,target):
    result=original(self,target)
    if self.name=="installed.app":os._exit(9)
    return result
Path.rename=interrupted
m.replace(Path(sys.argv[2]),Path(sys.argv[3]))
'''
            result=subprocess.run([sys.executable,'-c',code,installer.__file__,str(new),str(old)])
            self.assertEqual(result.returncode,9)
            self.assertFalse(old.exists())
            self.assertTrue(installer.recover(old))
            self.assertEqual((old/'version').read_text(),'old')
            self.assertTrue(new.exists())
            self.assertFalse(installer.journal_path(old).exists())

    def test_upgrade_retains_previous_bundle_and_can_roll_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old, new = root/'installed.app', root/'candidate.app'
            old.mkdir(); new.mkdir()
            (old/'version').write_text('old'); (new/'version').write_text('new')
            backup = installer.replace(new, old)
            self.assertTrue(backup.name.startswith('.'))
            self.assertTrue(backup.name.endswith('.noindex'))
            self.assertEqual(list(root.glob('*.app')),[old])
            self.assertEqual((backup/'version').read_text(), 'old')
            self.assertEqual((old/'version').read_text(), 'new')
            newer = installer.replace(backup, old)
            self.assertEqual((old/'version').read_text(), 'old')
            self.assertEqual((newer/'version').read_text(), 'new')

    def test_failed_promotion_restores_previous_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); old = root/'installed.app'; old.mkdir();new=root/'candidate.app';new.mkdir()
            (old/'retained').write_text('original')
            rename=Path.rename
            def fail_candidate(path,target):
                if path==new:raise OSError('Injected promotion failure')
                return rename(path,target)
            with patch.object(Path,'rename',fail_candidate),self.assertRaises(OSError):
                installer.replace(new, old)
            self.assertEqual((old/'retained').read_text(), 'original')
            self.assertFalse(installer.journal_path(old).exists())

    def test_failed_promotion_does_not_overwrite_concurrent_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=root/'installed.app';new=root/'candidate.app'
            old.mkdir();new.mkdir();(old/'retained').write_text('original')
            rename=Path.rename
            def fail_candidate(path,target):
                if path==new:
                    old.mkdir()
                    raise OSError('Concurrent replacement')
                return rename(path,target)
            with patch.object(Path,'rename',fail_candidate),self.assertRaises(RuntimeError):
                installer.replace(new,old)
            replacement=installer.identity(old)
            with self.assertRaises(ValueError):installer.recover(old)
            self.assertEqual(installer.identity(old),replacement)
            record=json.loads(installer.journal_path(old).read_text())
            self.assertEqual((root/record['backup']/'retained').read_text(),'original')

    def test_recovery_after_completed_promotion_retains_new_app_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=root/'installed.app';new=root/'candidate.app'
            old.mkdir();new.mkdir();backup=root/'installed.before-fixture.app'
            record={'backup':backup.name,'old':installer.identity(old),'new':installer.identity(new)}
            installer.journal_path(old).write_text(json.dumps(record))
            old.rename(backup);new.rename(old)
            self.assertTrue(installer.recover(old))
            self.assertEqual(installer.identity(old),record['new'])
            self.assertEqual(installer.identity(backup),record['old'])

    def test_active_shared_lease_refuses_upgrade(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_RUNTIME_DIR': directory}):
            fd = os.open(Path(directory)/'installation.lock', os.O_CREAT|os.O_RDWR, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_SH|fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):
                    installer.installation_lock()
            finally:
                os.close(fd)
            exclusive = installer.installation_lock(); os.close(exclusive)

    def test_symlink_lock_is_refused_without_touching_target(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_RUNTIME_DIR': directory}):
            root = Path(directory); target = root/'retained'; target.write_text('user data')
            (root/'installation.lock').symlink_to(target)
            with self.assertRaises(OSError):
                installer.installation_lock()
            self.assertEqual(target.read_text(), 'user data')
