# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Current DSH transport refuses replay and preserves role/history semantics."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services'))
from dsh.remote import Remote

class Response:
    def __init__(self,status,body):self.status=status;self.body=body
    def read(self,_limit):return json.dumps(self.body).encode()
    def __enter__(self):return self
    def __exit__(self,*_):pass

class RemoteTests(unittest.TestCase):
    def setUp(self):self.remote=Remote('http://127.0.0.1:1234',Path('/tmp/disposable-dsh'))
    def test_server_error_never_replays_mutation(self):
        with patch.object(self.remote,'request',return_value=Response(500,{})) as send:
            with self.assertRaisesRegex(ValueError,'not replayed'):self.remote.call('session.prompt',{'sessionId':'test','content':[]})
            self.assertEqual(send.call_count,1)
    def test_only_authentication_refusal_can_retry_and_preserves_identity(self):
        calls=[]
        def send(path,body,headers):
            calls.append(body)
            return Response(401,{}) if len(calls)==1 else Response(200,{'type':'server-response','rpcId':body['rpcId'],'result':{'ok':True,'value':{'accepted':True}}})
        with patch.object(self.remote,'request',side_effect=send),patch.object(self.remote,'authorize') as auth:
            self.assertTrue(self.remote.call('session.prompt',{'sessionId':'test','content':[]})['accepted'])
            self.assertEqual(calls[0],calls[1]);auth.assert_called_once()
            self.assertEqual(calls[0]['method'],'session/prompt')
            self.assertIn('requestId',calls[0]['payload']['args']['request'])
    def test_role_comes_from_current_projection_and_history_keeps_cursor(self):
        with patch.object(self.remote,'invoke',return_value={'items':[{'sessionId':'one','projections':{'values':{'agentPreset':'augmentor-browser-product'}}}]}) as invoke:
            self.assertEqual(self.remote.call('session.list')['items'][0]['agentPreset'],'augmentor-browser-product')
        with patch.object(self.remote,'snapshot',return_value={'cursor':12,'header':{'id':'one'}}),patch.object(self.remote,'invoke',return_value={'records':[],'hasMore':False}) as invoke:
            self.remote.call('session.history',{'sessionId':'one','beforeSeq':8,'maxMessages':2})
            invoke.assert_called_once_with('session/page',{'request':{'address':{'kind':'session','sessionId':'one'},'throughSeq':12,'beforeSeq':8,'maxMessages':2}})
    def test_remote_endpoint_refused_before_credentials(self):
        for endpoint in ['https://example.com','http://192.168.1.5','http://user:password@127.0.0.1','http://127.0.0.1/?token=abc']:
            with self.assertRaises(ValueError):Remote(endpoint,Path('/tmp/unused'))

    def test_slash_command_uses_registry_without_model_prompt(self):
        result={'commandId':'c','result':{'kind':'success','text':'No goal set.'}}
        with patch.object(self.remote,'invoke',return_value=result) as invoke:
            response=self.remote.call('session.prompt',{'sessionId':'s','content':[{'type':'text','text':'/goal'}]})
            self.assertEqual(response,{'accepted':True,'command':result})
            invoke.assert_called_once_with('commands/execute',{'agentId':'s','line':'/goal','submittedAttachments':[]})

    def test_unknown_failed_and_uncertain_commands_never_fall_back_to_model(self):
        for result in (None,{'result':{'kind':'error','text':'No active goal'}}):
            with patch.object(self.remote,'invoke',return_value=result) as invoke:
                with self.assertRaises(ValueError):self.remote.call('session.prompt',{'sessionId':'s','content':[{'type':'text','text':'/goal pause'}]})
                self.assertEqual(invoke.call_count,1)
        with patch.object(self.remote,'invoke',side_effect=OSError('connection lost')) as invoke:
            with self.assertRaises(OSError):self.remote.call('session.prompt',{'sessionId':'s','content':[{'type':'text','text':'/goal pause'}]})
            self.assertEqual(invoke.call_count,1)

    def test_plain_text_and_absolute_paths_still_reach_model(self):
        for line in ('Summarise the news','/home/example/file.txt'):
            with patch.object(self.remote,'invoke',return_value={'accepted':True}) as invoke:
                self.remote.call('session.prompt',{'sessionId':'s','content':[{'type':'text','text':line}]})
                self.assertEqual(invoke.call_args.args[0],'session/prompt')
