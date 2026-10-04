# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from augmentor_linux import dictation

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('dictation_broker',ROOT/'services/dictation/server.py')
broker=importlib.util.module_from_spec(spec);spec.loader.exec_module(broker)


class DictationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='augmentor-dictation-test-');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        environment=patch.dict(os.environ,{'XDG_RUNTIME_DIR':str(self.base/'run'),
            'XDG_STATE_HOME':str(self.base/'state')})
        environment.start();self.addCleanup(environment.stop)
        self.backend=broker.Backend(self.base)

    def test_theme_round_trip_while_disabled_never_starts_microphone(self):
        value=dictation.theme({'theme':'light','accent_hue':32,'opacity':70,'animation':False})
        with patch.object(self.backend,'start',side_effect=AssertionError('Started capture')):
            self.backend.request('theme',value)
            result=self.backend.request('status',{})
        self.assertFalse(result['enabled']);self.assertEqual(result['theme'],value)
        self.assertEqual(broker.Backend(self.base).preferences['theme'],value)
        for invalid in ({**value,'accent':'red'},{**value,'opacity':float('nan')},{**value,'extra':'ignored'}):
            with self.assertRaises(ValueError):self.backend.request('theme',invalid)
        self.assertEqual(json.loads((self.base/'preferences.json').read_text())['theme'],value)

    def test_only_matching_conversation_owner_can_release_capture(self):
        first={'token':'a'*32,'pid':os.getpid()};second={'token':'b'*32,'pid':os.getpid()}
        self.backend.request('conversation.acquire',first)
        self.backend.request('conversation.acquire',first)
        with self.assertRaisesRegex(RuntimeError,'busy'):self.backend.request('conversation.acquire',second)
        self.backend.request('conversation.release',second);self.assertEqual(self.backend.owner,first)
        self.backend.request('conversation.release',first);self.assertIsNone(self.backend.owner)
        self.backend.request('conversation.acquire',second);self.assertEqual(self.backend.owner,second)

    def test_unknown_operations_and_invalid_owner_cannot_start_component(self):
        with patch.object(self.backend,'start',side_effect=AssertionError('Started component')):
            with self.assertRaises(ValueError):self.backend.request('shell',{'command':'echo ignored'})
            with self.assertRaises(ValueError):self.backend.request('conversation.acquire',{'token':'a','pid':os.getpid()})
            with self.assertRaises(ValueError):self.backend.request('enable',{'enabled':'true'})
            with self.assertRaisesRegex(ValueError,'publisher terms'):self.backend.request('model.download',{'id':'unreviewed'})

    def test_uncertain_native_save_releases_portal_binding_and_disables_capture(self):
        from unittest.mock import Mock
        self.backend.generation=42;self.backend.portal=Mock();self.backend.preferences['enabled']=True
        current={'revision':0,'phase':'ready','settings':{'shortcut':'ctrl+space'}}
        with patch.object(self.backend,'start'),patch.object(self.backend,'stop') as stop,patch.object(self.backend,'call',side_effect=[current,TimeoutError('Lost acknowledgement')]):
            with self.assertRaises(TimeoutError):self.backend.request('settings',{'revision':'42/0','values':{'shortcut':'ctrl+shift+space'}})
        self.backend.portal.bind.assert_called_once_with('ctrl+shift+space');stop.assert_called_once()
        self.assertFalse(self.backend.preferences['enabled'])

    def test_last_explicit_colour_edit_wins_even_when_messages_arrive_late(self):
        old=dictation.theme({'accent_hue':10});new=dictation.theme({'accent_hue':280})
        self.backend.request('theme',{**old,'edited_at':100})
        self.backend.request('theme',{**new,'edited_at':200})
        self.backend.request('theme',{**old,'edited_at':150})
        self.assertEqual(self.backend.preferences['theme'],new)

    def test_maintenance_refuses_live_conversation_capture(self):
        self.backend.request('conversation.acquire',{'token':'a'*32,'pid':os.getpid()})
        with self.assertRaisesRegex(RuntimeError,'Nothing was cancelled'):self.backend.request('shutdown',{})
        self.assertIsNotNone(self.backend.owner)
        self.backend.request('conversation.release',{'token':'a'*32})
        self.backend.request('shutdown',{})

    def test_lost_acquire_acknowledgement_releases_its_exact_owner(self):
        admitted=[]
        def call(method,params,**options):
            admitted.append((method,params))
            if method=='conversation.acquire':raise TimeoutError('Lost reply after admission')
            return {}
        lease=dictation.MicrophoneLease()
        with patch.object(dictation,'request',side_effect=call):
            with self.assertRaises(TimeoutError):lease.acquire()
        self.assertIsNone(lease.token)
        self.assertEqual(admitted[1][0],'conversation.release')
        self.assertEqual(admitted[0][1]['token'],admitted[1][1]['token'])

    def test_old_snapshot_cannot_write_after_component_restart(self):
        self.backend.generation=42
        with patch.object(self.backend,'start'),patch.object(self.backend,'call',return_value={'revision':0}) as calls:
            with self.assertRaisesRegex(RuntimeError,'refresh'):self.backend.request('settings',{'revision':'41/0','values':{'shortcut':'ctrl+space'}})
            calls.assert_not_called()
            self.backend.request('settings',{'revision':'42/0','values':{'shortcut':'ctrl+space'}})
            self.assertEqual(calls.call_args.args[1]['revision'],0)

    def test_timed_out_voice_request_cannot_be_admitted_after_slow_model_work(self):
        from unittest.mock import Mock
        value={'token':'a'*32,'pid':os.getpid(),'expires_at':100}
        with patch.object(broker.time,'time_ns',return_value=101),patch.object(self.backend,'call') as native:
            with self.assertRaisesRegex(RuntimeError,'expired'):self.backend.request('conversation.acquire',value)
            native.assert_not_called();self.assertIsNone(self.backend.owner)
        self.backend.child=Mock();self.backend.child.poll.return_value=None
        with patch.object(broker.time,'time_ns',side_effect=[99,101]),patch.object(self.backend,'call') as native:
            with self.assertRaisesRegex(RuntimeError,'expired'):self.backend.request('conversation.acquire',value)
            self.assertEqual([entry.args[0] for entry in native.call_args_list],['conversation.acquire','conversation.release'])
            self.assertEqual(native.call_args_list[0].args[1]['expires_at'],100)
            self.assertEqual(native.call_args.args[1]['token'],value['token']);self.assertIsNone(self.backend.owner)

    def test_private_authenticated_ipc_and_single_owner(self):
        with patch.dict(os.environ,{'AUGMENTOR_DICTATION_STATE':str(self.base)}):
            state=dictation.request('status');self.assertFalse(state['enabled']);self.assertFalse(state['tray'])
            try:
                _,address,key=dictation.location()
                from multiprocessing.connection import Client
                from multiprocessing import AuthenticationError
                with self.assertRaises(AuthenticationError):Client(address,family='AF_UNIX',authkey=b'x'*32)
                value=dictation.theme({'accent_hue':280,'animation':False})
                dictation.request('theme',value)
                self.assertEqual(dictation.request('status')['theme'],value)
                lease=dictation.MicrophoneLease();lease.acquire();self.assertIsNotNone(lease.token);lease.release();self.assertIsNone(lease.token)
                self.assertEqual((self.base/'auth.key').stat().st_mode&0o777,0o600)
            finally:dictation.request('shutdown',start=False)

    def test_incomplete_checkout_cannot_own_an_enabled_session(self):
        checkout=self.base/'checkout'
        for relative in ('services/dictation/server.py','services/dictation/portal.py',
                'services/dictation/maintenance.py','services/lifecycle/admission.py','apps/native/augmentor_linux/dictation.py'):
            target=checkout/relative;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/relative,target)
        state=self.base/'state';state.mkdir(mode=0o700)
        original=b'{"enabled": true}\n';(state/'preferences.json').write_bytes(original)
        env={**os.environ,'AUGMENTOR_DICTATION_STATE':str(state),'PYTHONPATH':str(checkout/'apps/native')}
        result=subprocess.run([sys.executable,str(checkout/'services/dictation/server.py')],env=env,capture_output=True,timeout=8)
        self.assertNotEqual(result.returncode,0)
        self.assertIn(b'bundled Handy component is unavailable',result.stderr)
        self.assertEqual((state/'preferences.json').read_bytes(),original)
        with patch.dict(os.environ,{'AUGMENTOR_DICTATION_STATE':str(state)}):
            with self.assertRaisesRegex(RuntimeError,'not running'):dictation.request('status',start=False)

    def test_offscreen_ui_cannot_share_the_login_session_broker(self):
        home=self.base/'home';home.mkdir()
        with patch.dict(os.environ,{'HOME':str(home),'QT_QPA_PLATFORM':'offscreen'}):
            os.environ.pop('AUGMENTOR_DICTATION_STATE',None)
            state,address,key=dictation.location()
            try:
                self.assertNotEqual(state,home/'.local/share/augmentor/dictation')
                self.assertEqual(os.environ['AUGMENTOR_DICTATION_STATE'],str(state))
                self.assertEqual(state.stat().st_mode&0o777,0o700)
                self.assertFalse((home/'.local/share/augmentor/dictation').exists())
                self.assertEqual(dictation.location(),(state,address,key))
                lease=dictation.MicrophoneLease();lease.acquire();lease.release()
                self.assertFalse(dictation.request('status',start=False)['enabled'])
                self.assertFalse((home/'.local/share/augmentor/dictation').exists())
            finally:
                dictation.request('shutdown',start=False)
                shutil.rmtree(state)

    @unittest.skipIf(os.name=='nt','Unix socket path limit')
    def test_long_state_path_uses_private_short_socket_and_preserves_capture_ownership(self):
        long_base=self.base/('long-home-'+'a'*110)
        with patch.dict(os.environ,{'AUGMENTOR_DICTATION_STATE':str(long_base)}):
            _,address,_=dictation.location();socket_base=Path(address).parent
            self.addCleanup(socket_base.rmdir)
            self.assertLess(len(os.fsencode(address)),100)
            self.assertEqual(socket_base.stat().st_mode&0o777,0o700)
            try:
                state=dictation.request('status');self.assertFalse(state['enabled'])
                lease=dictation.MicrophoneLease();lease.acquire();self.assertIsNotNone(lease.token);lease.release()
                self.assertEqual((long_base/'auth.key').stat().st_mode&0o777,0o600)
            finally:
                dictation.request('shutdown',start=False)
                import time
                for _ in range(100):
                    if not Path(address).exists():break
                    time.sleep(.01)
                Path(address).unlink(missing_ok=True)

    def test_theme_matches_native_colour_math(self):
        from PySide6.QtGui import QColor
        from augmentor_linux.preferences import DEFAULTS
        for mode in ('dark','light'):
            values={**DEFAULTS,'theme':mode,'hue':28,'accent_hue':278,'brightness':5,'accent_brightness':-4}
            actual=dictation.theme(values);s=values['saturation']/100
            background=QColor.fromHslF(28/360,s*.5625,(.12 if mode=='dark' else .92)+5/150)
            self.assertEqual(actual['background'],background.name())
            accent=QColor.fromHslF(278/360,s,(.73 if mode=='dark' else .30)-4/150)
            self.assertEqual(actual['accent'],accent.name())

if __name__=='__main__':unittest.main()
