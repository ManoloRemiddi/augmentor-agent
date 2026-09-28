# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private profile and ownership refusal; actual service runs in native assembly."""
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from lifecycle.windows_voice import profile,discover_voice,VoiceParticipant
from platform_adapters.paths import private_directory
from platform_adapters.private_files import atomic_json,descriptor
from windows_supervisor import Supervisor


class VoiceOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home=private_directory(Path(self.temporary.name)/'voice')
        self.environment=patch.dict(os.environ,{'RESONANT_VOICE_HOME':str(self.home)})
        self.environment.start();self.addCleanup(self.environment.stop)
        self.secret='a'*64
        atomic_json(self.home/'config.json',{'port':18877,'tts':{'voiceId':'resonant-personal'}})
        with os.fdopen(descriptor(self.home/'token',writable=True,create=True),'w',encoding='utf-8') as stream:stream.write(self.secret)

    def test_read_only_profile_validation_preserves_voice_settings(self):
        before=(self.home/'config.json').read_bytes()
        self.assertEqual(profile(),(self.home,18877,self.secret))
        self.assertEqual((self.home/'config.json').read_bytes(),before)
        for port in (True,0,1023,65536,'18877'):
            atomic_json(self.home/'config.json',{'port':port})
            with self.subTest(port=port),self.assertRaisesRegex(ValueError,'port'):profile()

    def test_malformed_or_overlong_token_refuses_before_any_connection(self):
        for raw in ('bad',self.secret+'\nMORE','a'*65):
            with os.fdopen(descriptor(self.home/'token',writable=True),'w',encoding='utf-8') as stream:
                stream.write(raw);stream.truncate()
            with self.subTest(length=len(raw)),self.assertRaisesRegex(ValueError,'token'):profile()

    def test_external_listener_is_never_adopted_or_replaced(self):
        root=Path(self.temporary.name)/'payload'
        for name in ('node/node.exe','dsh/node_modules/dsh-resonant-voice/bin/resonant-voice.js'):
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture',encoding='utf-8')
        with socket.socket() as external,patch('windows_supervisor.OwnedProcess') as launch:
            external.bind(('127.0.0.1',0));external.listen()
            atomic_json(self.home/'config.json',{'port':external.getsockname()[1]})
            supervisor=Supervisor(root)
            with self.assertRaisesRegex(ValueError,'outside this background owner'):supervisor.start_voice()
            launch.assert_not_called();self.assertIsNone(supervisor.voice)
            external.settimeout(1);connection,_=external.accept();connection.close()

    def test_unknown_inventory_or_changed_profile_cannot_authorize_maintenance(self):
        owner=Mock()
        for value in ({},{'voice':{}},{'voice':{'running':'true'}}):
            owner.exchange.return_value=value
            with self.assertRaisesRegex(ValueError,'inventory'):discover_voice(ROOT,owner)
        owner.exchange.return_value={'voice':{'running':False}}
        self.assertIsNone(discover_voice(ROOT,owner))
        for record in ({'home':str(self.home),'port':18878},{'home':str(self.home/'other'),'port':18877}):
            with self.assertRaisesRegex(ValueError,'profile changed'):VoiceParticipant(ROOT,record,owner)
        owner.observe_child.assert_not_called()

    def test_live_voice_job_prevents_owner_exit_even_after_its_leader_exits(self):
        supervisor=Supervisor();voice=Mock();voice.drained.return_value=False;voice.poll.return_value=0
        supervisor.voice=voice
        self.assertTrue(supervisor.status()['voice']['running'])
        with self.assertRaisesRegex(ValueError,'running component'):supervisor.dispatch({'action':'exit-if-empty'})
        token='c'*32
        supervisor.dispatch({'action':'maintenance','method':'host.maintenance.prepare','params':{'token':token}})
        with self.assertRaisesRegex(ValueError,'running component'):
            supervisor.dispatch({'action':'maintenance','method':'host.maintenance.commit','params':{'token':token}})
        voice.terminate.assert_not_called();voice.wait_graceful.assert_not_called()

    def test_available_loopback_port_allows_owned_voice_launch(self):
        root=Path(self.temporary.name)/'payload'
        for name in ('node/node.exe','dsh/node_modules/dsh-resonant-voice/bin/resonant-voice.js'):
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture',encoding='utf-8')
        with socket.socket() as vacant:
            vacant.bind(('127.0.0.1',0));port=vacant.getsockname()[1]
        atomic_json(self.home/'config.json',{'port':port})
        with patch('windows_supervisor.OwnedProcess') as launch,patch('windows_supervisor.owner_directory',return_value=self.home):
            supervisor=Supervisor(root);supervisor.start_voice()
            launch.assert_called_once()
            self.assertIs(supervisor.voice,launch.return_value)
            self.assertEqual(supervisor.voice_profile,{'home':str(self.home),'port':port})


if __name__=='__main__':unittest.main()
