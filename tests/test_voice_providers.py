# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from augmentor_linux import voice_provider as provider
from augmentor_linux.live_dialogue import LiveDialogue


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.env=patch.dict(os.environ,{'AUGMENTOR_PI_CONFIG':self.directory.name,'RESONANT_VOICE_HOME':self.directory.name+'/local','AUGMENTOR_WINDOW_ID':'main'})
        self.env.start();self.addCleanup(self.env.stop)

    def test_settings_work_without_any_local_speech_installation(self):
        preferences=SimpleNamespace(values={'resonant_voice':True,'voice_mode':'manual','voice_pause_ms':800},save=Mock())
        status=provider.provider_settings({'action':'get'},preferences)
        self.assertFalse(status['configured']);self.assertEqual(status['status'],'needs-setup')
        self.assertEqual(status['voices'],[])
        provider.provider_settings({'action':'save','settings':{'enabled':False,'mode':'manual','pauseMs':800}},preferences)
        self.assertFalse(preferences.values['resonant_voice']);preferences.save.assert_called_once()

    def test_key_is_only_in_vault_and_verified_before_replacing_working_key(self):
        store=Mock();store.get_password.return_value='old-synthetic-key-123456'
        with patch.object(provider,'credential_store',return_value=store):
            provider.configure_cloud('new-synthetic-key-123456','marin',True,verify=Mock())
            raw=provider.config_path().read_text();self.assertNotIn('synthetic-key',raw)
            self.assertTrue(provider.snapshot()['configured'])
            verify=Mock(side_effect=RuntimeError('Cannot connect'))
            with self.assertRaises(RuntimeError):provider.configure_cloud('another-synthetic-key-123456','quartz',True,verify=verify)
            self.assertEqual(store.set_password.call_count,1)
            self.assertEqual(provider.load_config()['cloudVoice'],'marin')

    def test_browser_voice_preferences_preserve_appearance_without_decoding_qt_images(self):
        path=Path(self.directory.name)/'appearance.json'
        path.write_text(json.dumps({'background':'uploaded','background_image':'untouched-image','resonant_voice':True,'extra':'preserve'}))
        preferences=provider.VoicePreferences();preferences.values['resonant_voice']=False;preferences.save()
        saved=json.loads(path.read_text())
        self.assertFalse(saved['resonant_voice']);self.assertEqual(saved['background_image'],'untouched-image')
        self.assertEqual(saved['extra'],'preserve')

    def test_missing_audio_runtime_stays_actionable_even_with_verified_cloud_key(self):
        provider.save_config({'provider':'openai-live','cloudVoice':'marin','cloudConsent':True,'cloudVerified':True})
        with patch.object(provider,'audio_available',return_value=False),patch.object(provider,'cloud_key',return_value='synthetic-key'):
            state=provider.snapshot()
        self.assertFalse(state['configured']);self.assertEqual(state['status'],'needs-setup')
        self.assertTrue(state['providers']['openai-live']['configured'])
        self.assertIn('audio runtime',state['audioError'])

    def test_configuration_failure_restores_previous_vault_key(self):
        store=Mock();store.get_password.return_value='old-synthetic-key-123456'
        with patch.object(provider,'credential_store',return_value=store), patch.object(provider,'save_config',side_effect=OSError('disk')):
            with self.assertRaisesRegex(RuntimeError,'restored'):
                provider.configure_cloud('new-synthetic-key-123456','marin',True,verify=Mock())
        self.assertEqual(store.set_password.call_args.args[-1],'old-synthetic-key-123456')

    def test_secondary_configuration_and_vault_account_are_independent(self):
        provider.save_config({'provider':'openai-live','cloudVoice':'marin','cloudConsent':True,'cloudVerified':True})
        with patch.dict(os.environ,{'AUGMENTOR_WINDOW_ID':'secondary'}):
            self.assertEqual(provider.load_config()['provider'],'local')
            store=Mock();store.get_password.return_value='synthetic-key-123456'
            with patch.object(provider,'credential_store',return_value=store):provider.cloud_key()
            self.assertEqual(store.get_password.call_args.args[-1],'secondary')

    def test_vault_failure_is_sanitized_and_does_not_save_configuration(self):
        store=Mock();store.set_password.side_effect=RuntimeError('private-synthetic-secret')
        with patch.object(provider,'credential_store',return_value=store):
            with self.assertRaisesRegex(RuntimeError,'credential vault') as error:
                provider.configure_cloud('synthetic-key-123456','marin',True,verify=Mock())
        self.assertNotIn('private-synthetic',str(error.exception));self.assertFalse(provider.config_path().exists())

    def test_setup_requires_consent_and_uses_client_delegation_without_microphone(self):
        with self.assertRaises(ValueError):provider.configure_cloud('synthetic-key-123456','marin',False,verify=Mock())
        socket=Mock();socket.recv.side_effect=[json.dumps({'type':'session.started'}),json.dumps({'type':'session.closed','usage':{'seconds':1}})]
        connect=Mock(return_value=socket)
        provider.verify_cloud('synthetic-key-123456','marin',connect=connect)
        messages=[json.loads(call.args[0]) for call in socket.send.call_args_list]
        self.assertEqual(connect.call_args.kwargs['redirect_limit'],0)
        self.assertEqual(messages[0]['session']['delegation'],{'type':'client'})
        self.assertEqual(messages[0]['session']['model'],'gpt-live-1')
        self.assertEqual(messages[-1]['type'],'session.close');socket.close.assert_called_once()
        self.assertNotIn('session.input_audio.append',[m['type'] for m in messages])

    def test_failed_access_test_closes_and_never_exposes_upstream_error(self):
        socket=Mock();socket.recv.return_value=json.dumps({'type':'error','message':'synthetic-secret'})
        with self.assertRaises(RuntimeError) as error:provider.verify_cloud('synthetic-key-123456','marin',connect=Mock(return_value=socket))
        self.assertNotIn('synthetic-secret',str(error.exception));socket.close.assert_called_once()

    def test_initial_local_config_is_not_ready_without_models(self):
        home=Path(os.environ['RESONANT_VOICE_HOME']);home.mkdir()
        (home/'config.json').write_text(json.dumps({'tts':{'url':'http://127.0.0.1:8878'}}));(home/'token').write_text('a'*64)
        with patch.object(provider.urllib.request,'build_opener') as opener:
            opener.return_value.open.side_effect=OSError('offline')
            self.assertFalse(provider.local_configured())
        self.assertEqual(json.loads((home/'config.json').read_text()),{'tts':{'url':'http://127.0.0.1:8878'}})

    def test_cloud_can_be_selected_and_removed_without_touching_local_models(self):
        store=Mock();store.get_password.return_value='synthetic-key-123456'
        with patch.object(provider,'credential_store',return_value=store):
            provider.configure_cloud('synthetic-key-123456','marin',True,verify=Mock())
            ticket=provider.cloud_ticket('current');self.assertEqual(ticket['protocol'],'augmentor-live/1')
            provider.remove_cloud();self.assertFalse(provider.snapshot()['configured'])
            store.delete_password.assert_called_once()
        self.assertFalse(Path(os.environ['RESONANT_VOICE_HOME']).exists())


class DelegationTests(unittest.TestCase):
    def setUp(self):
        self.now=0;self.submissions=[];self.updates=[];self.clears=[]
        self.dialogue=LiveDialogue(self.submissions.append,self.updates.append,lambda:self.clears.append(True),hands_free=True,clock=lambda:self.now)

    def transcript(self,text,end=100,event='fragment'):
        self.dialogue.receive({'type':'session.input_transcript.delta','event_id':event,'delta':text,'end_ms':end})

    def submit(self,text='Check the order'):
        self.transcript(text);self.now+=1;self.dialogue.tick();return self.submissions[-1]['requestId']

    def backend(self,identifier,answer='The order shipped.',reason='completed',turn='turn-1'):
        self.dialogue.observe({'type':'user/message','turnId':turn,'data':{'source':{'rpcId':'augmentor-voice:'+identifier},'content':[{'type':'text','text':'Check the order'}]}})
        self.dialogue.observe({'type':'assistant/message','turnId':turn,'data':{'message':{'content':[{'type':'reasoning','text':'Private reasoning'},{'type':'text','text':answer}]}}})
        self.dialogue.observe({'type':'turn/end','turnId':turn,'data':{'reason':{'kind':reason}}})

    def test_every_utterance_delegates_even_without_a_live_delegation_event(self):
        self.submit('Hello');self.assertEqual(self.submissions[0]['text'],'Hello')
        self.assertFalse(self.dialogue.output_allowed);self.assertEqual(self.updates,[])

    def test_fragments_and_duplicate_delegations_submit_once(self):
        self.transcript('Check ');self.transcript('the order',200,'fragment-2')
        event={'type':'session.delegation.created','delegation':{'id':'task-1','target':'client'}}
        self.dialogue.receive(event);self.dialogue.receive(event)
        self.now=1;self.dialogue.tick();self.dialogue.tick();self.dialogue.receive(event)
        self.transcript('late repeated words',200,'late');self.now=2;self.dialogue.tick()
        self.assertEqual(len(self.submissions),1);self.assertEqual(self.submissions[0]['text'],'Check the order')

    def test_manual_release_is_required_and_late_fragments_are_included(self):
        self.dialogue.hands_free=False;self.dialogue.begin();self.transcript('Check ')
        self.now=2;self.dialogue.tick();self.assertEqual(self.submissions,[])
        self.dialogue.end();self.transcript('the order',200,'late');self.now=3;self.dialogue.tick()
        self.assertEqual(self.submissions[0]['text'],'Check the order')

    def test_public_result_only_after_successful_matching_turn_and_ack(self):
        identifier=self.submit();self.backend(identifier)
        self.assertEqual(self.updates[0]['content'],'The order shipped.')
        self.assertFalse(self.dialogue.output_allowed)
        self.dialogue.receive({'type':'session.commentary.appended','client_event_id':self.updates[0]['event_id']})
        self.assertTrue(self.dialogue.output_allowed)
        self.assertNotIn('Private',str(self.updates))

    def test_failed_or_unrelated_turn_cannot_speak(self):
        identifier=self.submit();self.backend('unrelated');self.assertEqual(self.updates,[])
        self.backend(identifier,reason='aborted');self.assertEqual(self.updates,[])

    def test_barge_in_invalidates_queued_result_acknowledgements(self):
        identifier=self.submit();self.backend(identifier);event=self.updates[-1]['event_id']
        self.dialogue.interrupt()
        self.dialogue.receive({'type':'session.commentary.appended','client_event_id':event})
        self.assertFalse(self.dialogue.output_allowed)

    def test_dsh_sequence_boundaries_work_without_turn_ids(self):
        identifier=self.submit()
        for event in [
            {'type':'turn/start','seq':10,'data':{}},
            {'type':'user/message','seq':11,'data':{'source':{'rpcId':'augmentor-voice:'+identifier},'content':[]}},
            {'type':'assistant/message','seq':12,'data':{'message':{'content':[{'type':'text','text':'Verified DSH result.'}]}}},
            {'type':'turn/end','seq':13,'data':{'reason':{'kind':'completed'}}},
        ]:self.dialogue.observe(event)
        self.assertEqual(self.updates[0]['content'],'Verified DSH result.')

    def test_pi_text_match_and_turn_identity_bind_the_existing_model_reply(self):
        self.submit();self.dialogue.observe({'type':'user/message','turnId':'pi-turn','data':{'source':{'kind':'user'},'content':[{'type':'text','text':'Check the order'}]}})
        self.dialogue.observe({'type':'assistant/message','turnId':'pi-turn','data':{'message':{'content':[{'type':'text','text':'Pi result'}]}}})
        self.dialogue.observe({'type':'turn/end','turnId':'pi-turn','data':{'reason':{'kind':'completed'}}})
        self.assertEqual(self.updates[0]['content'],'Pi result')

    def test_latest_correction_supersedes_previous_backend_reply(self):
        old=self.submit();self.transcript('Actually check another order',300,'correction');self.now=2;self.dialogue.tick()
        self.backend(old);self.assertEqual(self.updates,[])

    def test_unicode_result_chunks_are_bounded_and_usage_is_not_summed(self):
        identifier=self.submit();self.backend(identifier,answer='结果'*900)
        self.assertEqual(''.join(v['content'] for v in self.updates),'结果'*900)
        self.assertTrue(all(len(v['content'].encode())<=400 for v in self.updates))
        for seconds in (12,15):self.dialogue.receive({'type':'session.usage.updated','usage':{'seconds':seconds}})
        self.assertEqual(self.dialogue.seconds,15)

    def test_unconfirmed_submission_stops_without_replaying(self):
        identifier=self.submit()
        with self.assertRaisesRegex(ValueError,'not confirmed'):self.dialogue.submission({'id':'augmentor-voice:'+identifier,'accepted':False})
        self.now=5;self.dialogue.tick();self.assertEqual(len(self.submissions),1)

    def test_transcript_overflow_and_responses_delegation_are_rejected(self):
        with self.assertRaises(ValueError):self.transcript('x'*8193)
        with self.assertRaisesRegex(ValueError,'delegate to Augmentor'):
            self.dialogue.receive({'type':'session.delegation.created','delegation':{'id':'bad','target':'responses'}})


if __name__=='__main__':unittest.main()
