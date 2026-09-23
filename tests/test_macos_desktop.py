# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Executor policy tests with a fake native boundary, not macOS GUI evidence."""
import importlib.util
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('macos_desktop',Path(__file__).resolve().parents[1]/'services/desktop/macos.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class MacDesktopTests(unittest.TestCase):
    def setUp(self):
        root=tempfile.TemporaryDirectory();self.addCleanup(root.cleanup)
        self.env=patch.dict(os.environ,{'XDG_RUNTIME_DIR':root.name});self.env.start();self.addCleanup(self.env.stop)
        self.backend=module.MacDesktop(lambda *_:None);self.addCleanup(self.backend.stop)
        self.calls=[]
        self.scene={'window':{'pid':42,'id':5},'screens':[{'geometry':{'x':-100,'y':0,'width':200,'height':100}}]}
        def native(method,**params):
            self.calls.append((method,params))
            if method=='status':return {'permissions':{'screenRecording':True,'accessibility':True},'displays':1}
            if method=='capture':return {'scene':self.scene,'image':{'data':'fixture','mimeType':'image/jpeg','width':100,'height':50}}
            return {'dispatched':True,'verified':False}
        self.native=native;self.backend.native=native

    def connected(self):
        self.backend.connect('pi:one')
        return self.backend.capture('pi:one')['token']

    def test_stop_revokes_grant_and_old_observation(self):
        token=self.connected();grant=self.backend.authorization
        self.assertTrue(grant.exists());self.assertEqual(grant.stat().st_mode&0o777,0o600)
        self.backend.stop();self.assertFalse(grant.exists())
        with self.assertRaisesRegex(RuntimeError,'Connect'):
            self.backend.action('pi:one',{'token':token,'kind':'click','x':10,'y':10})
        self.assertFalse(any(method=='action' for method,_ in self.calls))

    def test_token_consumed_once_and_coordinates_match_display(self):
        token=self.connected()
        value=self.backend.action('pi:one',{'token':token,'kind':'click','x':25,'y':25})
        self.assertFalse(value['verified'])
        self.assertEqual(self.calls[-1][1]['x'],-50);self.assertEqual(self.calls[-1][1]['y'],50)
        with self.assertRaisesRegex(RuntimeError,'already used'):
            self.backend.action('pi:one',{'token':token,'kind':'click','x':25,'y':25})

    def test_cross_owner_cannot_act_or_take_connection(self):
        token=self.connected()
        with self.assertRaises(RuntimeError):self.backend.connect('dsh:two')
        with self.assertRaises(RuntimeError):self.backend.action('dsh:two',{'token':token,'kind':'type','text':'wrong'})
        self.assertEqual(self.backend.owner,'pi:one')

    def test_stop_during_text_prevents_next_character(self):
        token=self.connected();sent=[]
        def native(method,**params):
            if method=='action':sent.append(params['text']);self.backend.stop()
            return {}
        self.backend.native=native
        with self.assertRaises(RuntimeError):self.backend.action('pi:one',{'token':token,'kind':'type','text':'Café'})
        self.assertEqual(sent,['C'])

    def test_stop_during_permission_prompt_cannot_reactivate(self):
        entered=threading.Event();release=threading.Event();errors=[]
        def native(method,**params):
            if method=='status':return {'permissions':{},'displays':1}
            entered.set();release.wait(2)
            return {'permissions':{'screenRecording':True,'accessibility':True}}
        self.backend.native=native
        def connect():
            try:self.backend.connect('pi:one')
            except RuntimeError as error:errors.append(str(error))
        thread=threading.Thread(target=connect);thread.start()
        self.assertTrue(entered.wait(1));self.backend.stop();release.set();thread.join(3)
        self.assertFalse(thread.is_alive());self.assertTrue(errors)
        self.assertIsNone(self.backend.authorization);self.assertIsNone(self.backend.owner)

    def test_refused_permission_never_creates_authorization(self):
        self.backend.native=lambda method,**params:{'permissions':{'screenRecording':False,'accessibility':False},'displays':1}
        with self.assertRaisesRegex(RuntimeError,'System Settings'):self.backend.connect('pi:one')
        self.assertIsNone(self.backend.authorization);self.assertIsNone(self.backend.owner)
