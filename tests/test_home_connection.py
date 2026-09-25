# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services'))
from home import client

class Response:
    def __init__(self,data):self.data=json.dumps(data).encode()
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,_limit):return self.data

class HomeConnectionTests(unittest.TestCase):
    def test_private_pairing_state_and_failed_revocation(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'AUGMENTOR_HOME_CONNECTION':str(Path(directory)/'home.json')}):
            class Opener:
                def open(self,request,timeout):return Response({'token':'fixture-token-long-enough-only'})
            with patch.object(client.urllib.request,'build_opener',return_value=Opener()):
                result=client.call('home.connection.pair',{'url':'https://home.example.com','code':'fixture','name':'Laptop'})
            self.assertTrue(result['connected']);self.assertNotIn('token',result)
            self.assertEqual(client.config_path().stat().st_mode&0o777,0o600)
            self.assertNotIn('token',client.call('home.connection.state',{}))
            with self.assertRaises(ValueError):client.call('home.connection.pair',{'url':'https://other.example.com','code':'fixture','name':'Other'})
            with patch.object(client.urllib.request,'build_opener',side_effect=OSError('unavailable')):
                with self.assertRaises(OSError):client.call('home.connection.disconnect',{})
            self.assertTrue(client.config_path().exists())
    def test_reject_unsafe_endpoints(self):
        for value in ['http://nas.local','https://name:secret@home.example.com','https://home.example.com/api','https://home.example.com?token=x']:
            with self.assertRaises(ValueError):client.endpoint(value)
        self.assertEqual(client.endpoint('http://127.0.0.1:8181/'),'http://127.0.0.1:8181')

class HomeDialogTests(unittest.TestCase):
    def test_pairing_uses_shared_service_and_clears_code(self):
        from PySide6.QtWidgets import QApplication,QWidget
        from augmentor_linux.home_settings import HomeDialog
        app=QApplication.instance() or QApplication([])
        class Window(QWidget):
            def call_in_background(self,work,done):done(work())
        window=Window();calls=[]
        def request(_self,method,data):
            calls.append((method,data))
            return {'connected':method=='home.connection.pair','url':'https://home.example.com'}
        with patch('augmentor_linux.home_settings.PromptClient.call',request):
            dialog=HomeDialog(window);dialog.url.setText('https://home.example.com');dialog.code.setText('fixture');dialog.pair()
            self.assertEqual(calls[-1][0],'home.connection.pair');self.assertEqual(dialog.code.text(),'')
            self.assertFalse(dialog.connect.isEnabled());self.assertTrue(dialog.disconnect.isEnabled())
            dialog.close();window.close()
