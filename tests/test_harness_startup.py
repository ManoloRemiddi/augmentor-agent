# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authored startup/recovery fixtures; never read owner profiles or start their services."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from contextlib import nullcontext
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(sys.platform=='linux','MX startup controller')
class HarnessStartupTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(dir=os.environ.get('AUGMENTOR_BUILD_WORKSPACE'));self.addCleanup(temp.cleanup);self.home=Path(temp.name)
        spec=importlib.util.spec_from_file_location('startup_fixture',ROOT/'scripts/harness-startup.py');self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
        self.env=patch.dict(os.environ,{'HOME':str(self.home),'XDG_DATA_HOME':str(self.home/'data'),'XDG_CONFIG_HOME':str(self.home/'config')});self.env.start();self.addCleanup(self.env.stop)
        self.registry=self.home/'registry';self.registry.mkdir(mode=0o700)
        self.config={'schema':self.m.SCHEMA,'registry':str(self.registry),'review':'pilot','opener':str(self.home/'.local/bin/augmentor-harness-review')}
        self.entry={'deployment':{'root':str(self.home/'release'),'version':'authored','artifactSha256':'a'*64},'profile':{'port':41789,'state':str(self.home/'state'),'config':str(self.home/'profile-config')}}
        self.review=types.SimpleNamespace(registry_lock=lambda *_:nullcontext(),registry_read=lambda *_:{'entries':{'pilot':self.entry}},profile_record=lambda p:p,sealed_release=lambda *_:(self.entry['deployment'],{}),desktop_field=lambda x:'"'+str(x)+'"',open_review=Mock())

    def stage(self):
        with patch.object(self.m,'review_tool',return_value=self.review),patch.object(self.m.subprocess,'run'):
            self.m.install(self.registry,'pilot')
        return self.m.paths()[1]

    def test_login_is_headless_and_imports_only_graphical_environment(self):
        with patch.dict(os.environ,{'DISPLAY':':88','OPENAI_API_KEY':'AUTHORED_NOT_FORWARDED'}),patch.object(self.m.subprocess,'run') as run:
            self.m.start_service()
        self.assertEqual(run.call_args_list[-1].args[0],['systemctl','--user','start',self.m.SERVICE]);self.assertNotIn('OPENAI_API_KEY',run.call_args_list[0].args[0]);self.assertNotIn('xdg-open',str(run.call_args_list))

    def test_open_falls_back_to_verified_launcher_without_service_manager(self):
        with patch.object(self.m,'start_service',side_effect=FileNotFoundError),patch.object(self.m,'configuration',return_value=self.config),patch.object(self.m,'review_tool',return_value=self.review),patch.object(self.m,'selection') as selected:self.m.open_app()
        selected.assert_called_once_with(self.config,self.review,browser=True)

    def test_menu_waits_for_concurrent_startup_without_replaying_other_errors(self):
        with patch.object(self.m,'start_service'),patch.object(self.m,'configuration',return_value=self.config),patch.object(self.m,'review_tool',return_value=self.review),patch.object(self.m.time,'sleep'),patch.object(self.m,'selection',side_effect=[ValueError('Review registration is busy.'),None]) as selected:self.m.open_app()
        self.assertEqual(selected.call_count,2)
        with patch.object(self.m,'start_service'),patch.object(self.m,'configuration',return_value=self.config),patch.object(self.m,'review_tool',return_value=self.review),patch.object(self.m,'selection',side_effect=ValueError('A live owner is unconfirmed.')) as selected:
            with self.assertRaises(ValueError):self.m.open_app()
        selected.assert_called_once()

    def test_missing_registration_never_opens_another_profile(self):
        self.review.registry_read=lambda *_:{'entries':{}}
        with self.assertRaisesRegex(ValueError,'no empty or alternate'):self.m.selection(self.config,self.review)
        self.review.open_review.assert_not_called()

    def test_private_link_never_reaches_service_output(self):
        (self.registry/'reviews.json').write_text('{}');(self.registry/'reviews.json').chmod(0o600)
        self.review.open_review.side_effect=lambda *_:print('http://127.0.0.1:41789/#token=AUTHORED_SECRET')
        import io
        output=io.StringIO()
        with patch('sys.stdout',output):entry,stamp=self.m.selection(self.config,self.review)
        self.assertEqual(output.getvalue(),'');self.assertEqual(entry,self.entry);self.assertEqual(len(stamp),64)

    def test_controller_install_has_no_release_path_or_token_and_uses_graphical_login(self):
        data=self.stage();home,_,config=self.m.paths();unit=(config/'systemd/user'/self.m.SERVICE).read_text();login=(config/'autostart/com.augmentor.Harness.desktop').read_text();desktop=(home/'data/applications/com.augmentor.Harness.desktop').read_text()
        self.assertIn('Restart=always',unit);self.assertIn('KillMode=process',unit);self.assertIn('WantedBy=graphical-session.target',unit);self.assertIn('--login',login);self.assertIn('Name=Augmentor Harness\n',desktop)
        for text in [unit,login,desktop,(home/'.local/bin/augmentor-harness').read_text()]:self.assertNotIn(self.entry['deployment']['root'],text);self.assertNotIn('token=',text)
        self.assertEqual(self.m.configuration()['review'],'pilot');self.assertEqual((data/'launch.py').stat().st_mode&0o777,0o600)

    def test_owned_install_preserves_edits_and_reverses_validation_failure(self):
        data=self.stage();unit=self.m.paths()[2]/'systemd/user'/self.m.SERVICE;original=unit.read_bytes();selection=(data/'current.json').read_bytes();unit.write_bytes(b'AUTHORED_KEEP_EDIT')
        with patch.object(self.m,'review_tool',return_value=self.review),patch.object(self.m.subprocess,'run'):
            with self.assertRaisesRegex(ValueError,'edited'):self.m.install(self.registry,'pilot')
        self.assertEqual(unit.read_bytes(),b'AUTHORED_KEEP_EDIT');unit.write_bytes(original)
        with patch.object(self.m,'review_tool',return_value=self.review),patch.object(self.m.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['authored-validator'])):
            with self.assertRaises(subprocess.CalledProcessError):self.m.install(self.registry,'pilot')
        self.assertEqual(unit.read_bytes(),original);self.assertEqual((data/'current.json').read_bytes(),selection)

    def test_bootstrap_refuses_tampered_controller_without_executing_it(self):
        data=self.stage();config=self.m.configuration();controller=Path(config['controller']);controller.write_bytes(b'raise RuntimeError("AUTHORED_MUST_NOT_EXECUTE")')
        r=subprocess.run([sys.executable,'-B',str(data/'launch.py'),'--status'],capture_output=True,text=True)
        self.assertEqual(r.returncode,1);self.assertNotIn('AUTHORED_MUST_NOT_EXECUTE',r.stderr);self.assertIn('Reinstall',r.stderr)

    def test_opener_hash_must_match_registered_ownership(self):
        opener=Path(self.config['opener']);opener.parent.mkdir(parents=True);opener.write_text('raise RuntimeError("AUTHORED_MUST_NOT_EXECUTE")');opener.chmod(0o700);registry=self.registry/'reviews.json';registry.write_text(json.dumps({'ownedFiles':{str(opener):'0'*64}}));registry.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'changed'):self.m.review_tool(self.config)

    def test_supervisor_retries_transient_startup_without_logging_secrets_or_forcing_owner(self):
        self.stage();stop=threading.Event();calls=[]
        class Step:
            def __init__(self):self.n=0
            def is_set(self):return self.n>=3
            def wait(self,_):self.n+=1
        step=Step();self.m.atomic=lambda *args,**kwargs:calls.append(args)
        with patch.object(self.m,'configuration',return_value=self.config),patch.object(self.m,'review_tool',return_value=self.review),patch.object(self.m,'private_bytes',return_value=b'{}'),patch.object(self.m,'selection',side_effect=[ValueError('AUTHORED_SECRET'),(self.entry,'a'),(self.entry,'a')]) as selected,patch.object(self.m,'verified_owner',return_value=os.getpid()),patch.object(self.m.os,'pidfd_open',side_effect=lambda *_:os.open('/dev/null',os.O_RDONLY)),patch.object(self.m.select,'select',return_value=([],[],[])):
            import io
            output=io.StringIO()
            with patch('sys.stdout',output):self.m.supervise(step,0)
        self.assertNotIn('AUTHORED_SECRET',output.getvalue());self.assertEqual(selected.call_count,3);self.assertIn('ready',output.getvalue());self.assertNotIn('kill',str(calls));self.assertNotIn('token=',str(calls))

    def test_duplicate_supervisor_does_not_start_another_owner(self):
        data=self.stage();lock=os.open(data/'supervisor.lock',os.O_CREAT|os.O_RDWR,0o600)
        import fcntl
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:
            with patch.object(self.m,'selection') as selected:self.m.supervise(threading.Event(),0)
            selected.assert_not_called()
        finally:os.close(lock)

    def test_http_health_requires_the_verified_listener_and_never_sends_a_key(self):
        proc=self.home/'proc/123';(proc/'net').mkdir(parents=True);(proc/'fd').mkdir();table=proc/'net/tcp';table.write_text('header\n 0: 0100007F:A33D 00000000:0000 0A 0 0 0 1000 0 777\n');(proc/'fd/9').symlink_to('socket:[888]')
        opener=Mock()
        with patch.object(self.m.urllib.request,'build_opener',return_value=opener):
            with self.assertRaisesRegex(ValueError,'does not own'):self.m.http_ready(123,41789,self.home/'proc')
        opener.open.assert_not_called();(proc/'fd/9').unlink();(proc/'fd/9').symlink_to('socket:[777]')
        import urllib.error
        opener.open.side_effect=urllib.error.HTTPError('authored',401,'Unauthorized',{},None)
        with patch.object(self.m.urllib.request,'build_opener',return_value=opener):self.m.http_ready(123,41789,self.home/'proc')
        self.assertEqual(opener.open.call_args.args,('http://127.0.0.1:41789/api/access',));self.assertNotIn('Authorization',str(opener.open.call_args))

    def test_recovery_diagnostics_are_specific_and_never_echo_secrets(self):
        self.assertIn('maintenance',self.m.startup_message(ValueError('maintenance')))
        self.assertIn('without changing',self.m.startup_message(ValueError('fixed browser port')))
        self.assertIn('no replacement',self.m.startup_message(ValueError('live process')))
        self.assertNotIn('AUTHORED_SECRET',self.m.startup_message(ValueError('token=AUTHORED_SECRET')))

    def test_healthy_monitor_does_not_repeatedly_verify_or_restart_the_whole_build(self):
        self.stage()
        class Step:
            def __init__(self):self.n=0
            def is_set(self):return self.n>=3
            def wait(self,_):self.n+=1
        with patch.object(self.m,'configuration',return_value=self.config),patch.object(self.m,'review_tool',return_value=self.review),patch.object(self.m,'private_bytes',return_value=b'{}'),patch.object(self.m,'selection',return_value=(self.entry,hashlib.sha256(b'{}').hexdigest())) as selected,patch.object(self.m,'verified_owner',return_value=os.getpid()) as verified,patch.object(self.m.os,'pidfd_open',side_effect=lambda *_:os.open('/dev/null',os.O_RDONLY)),patch.object(self.m.select,'select',return_value=([],[],[])):
            self.m.supervise(Step(),0)
        selected.assert_called_once();self.assertEqual(verified.call_count,3)
