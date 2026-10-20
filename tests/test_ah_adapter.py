# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real private IPC, independently authored profiles, no owner state/model calls."""
import json
import os
from pathlib import Path
import socketserver
import plistlib
import tempfile
import threading
import unittest
from unittest.mock import patch
from augmentor_linux.ah_connection import selection
from augmentor_linux.adapters.ah import AhAdapter
from augmentor_linux.controller import Controller
from augmentor_linux.preferences import Preferences


class AhAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='ag-ah-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.profile={}
        for key in ('config','state','workspace','sharedState','sharedData'):
            p=self.root/key;p.mkdir(mode=0o700);self.profile[key]=str(p)
        self.profile['socket']=str(self.root/'host.sock');self.record=self.root/'connection.json'
        self.value=dict(schema='augmentor-ah-connection/1',profile=self.profile,root=str(self.root),version='authored-test')
        self.save();self.calls=[];self.wrong=False
        env=patch.dict(os.environ,{'AUGMENTOR_AH_CONNECTION':str(self.record),'AUGMENTOR_PI_CONFIG':str(self.root/'unrelated-config'),
                                   'AUGMENTOR_PI_STATE':str(self.root/'unrelated-state'),'AUGMENTOR_AGENT_ENTRIES':str(self.root/'entries.json')})
        env.start();self.addCleanup(env.stop)

    def save(self):
        self.record.write_text(json.dumps(self.value));self.record.chmod(0o600)

    def server(self):
        owner=self
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                for line in self.rfile:
                    r=json.loads(line);owner.calls.append(r)
                    if r['method']=='host.hello':result={'protocol':'augmentor-pi/1'}
                    elif r['method']=='host.describe':result=dict(protocol='augmentor-pi/1',stateDir='wrong' if owner.wrong else owner.profile['state'],configDir=owner.profile['config'],version='authored-test',capabilities={'queue':True,'promptImprovement':True})
                    elif r['method']=='models.list':result={'groups':[{'provider':'authored','models':[{'model':'fixture'}]}]}
                    else:result={'accepted':True}
                    self.wfile.write((json.dumps({'id':r['id'],'result':result})+'\n').encode());self.wfile.flush()
        s=socketserver.ThreadingUnixStreamServer(self.profile['socket'],Handler);s.daemon_threads=True
        thread=threading.Thread(target=s.serve_forever,daemon=True);thread.start()
        self.addCleanup(s.server_close);self.addCleanup(s.shutdown)

    def test_real_ipc_routes_to_ah_and_preserves_model_request_identity(self):
        self.server();c=AhAdapter();c.call('host.describe');c.model_catalog()
        p={'sessionId':'authored-chat','requestId':'never-replay','content':[{'type':'text','text':'fixture'}]}
        self.assertTrue(c.call('session.prompt',p)['accepted'])
        self.assertEqual([r['params'] for r in self.calls if r['method']=='session.prompt'],[p])
        self.assertTrue(c.supports_queue)
        self.assertFalse((self.root/'unrelated-state').exists())

    def test_wrong_owner_refuses_before_action(self):
        self.server();self.wrong=True;c=AhAdapter()
        with self.assertRaisesRegex(Exception,'does not match'):c.call('session.prompt',{'requestId':'refused'})
        self.assertFalse(any(r['method']=='session.prompt' for r in self.calls))

    def test_changed_selection_refuses_even_a_valid_old_owner(self):
        self.server();c=AhAdapter();self.value['version']='replacement';self.save()
        with self.assertRaisesRegex(Exception,'changed'):c.call('models.list')
        self.assertEqual(self.calls,[])

    def test_missing_or_unsafe_record_never_falls_back_to_pi(self):
        self.record.unlink();c=AhAdapter()
        with self.assertRaisesRegex(Exception,'not connected'):c.call('host.describe')
        self.assertFalse((self.root/'unrelated-state').exists())
        self.save();self.record.chmod(0o644)
        with self.assertRaisesRegex(ValueError,'private'):selection()

    def test_ah_is_default_but_saved_dsh_choice_is_retained(self):
        with patch.dict(os.environ,{'AUGMENTOR_PI_CONFIG':self.profile['config']}):
            self.assertEqual(Preferences().values['harness'],'ah')
            p=Preferences();p.values['harness']='dsh';p.save()
            self.assertEqual(Preferences().values['harness'],'dsh')

    def test_preferences_and_controller_resume_the_ah_identity_only(self):
        self.server()
        with patch.dict(os.environ,{'AUGMENTOR_PI_CONFIG':self.profile['config']}):
            p=Preferences();p.values['harness']='ah';p.save();self.assertEqual(Preferences().values['harness'],'ah')
            c=Controller(harness='ah');c.session='authored-chat';c.selection={'provider':'authored','model':'fixture'};c.save_session();c.close()
            again=Controller(harness='ah');self.addCleanup(again.close)
            self.assertEqual(again.harness,'ah');self.assertEqual(again.session,'authored-chat')
            self.assertEqual(again.selection,{'provider':'authored','model':'fixture'})
            self.assertEqual(again.client.workspace(),Path(self.profile['workspace']))

    def test_shared_library_uses_the_ah_store_not_the_process_default(self):
        c=AhAdapter();captured={}
        def make(**kwargs):
            captured.update(kwargs)
            return type('Stub',(),{'call':lambda *a:{'revision':7,'prompts':[]}})()
        with patch('augmentor_linux.prompt_client.PromptClient',side_effect=make):
            self.assertEqual(c.prompt_client().call('prompts.list')['revision'],7)
        self.assertEqual(captured['environment']['AUGMENTOR_SHARED_STATE'],self.profile['sharedState'])
        self.assertEqual(captured['root'],self.root)

    def test_offline_explicit_profile_requires_its_manager_and_never_creates_pi_state(self):
        c=AhAdapter()
        with self.assertRaisesRegex(Exception,'Start the registered'):c.call('host.describe')
        self.assertFalse((self.root/'unrelated-state').exists())

    def test_macos_reads_the_installed_launchagent_environment(self):
        app=self.root/'app';app.mkdir();(app/'package.json').write_text('{"version":"authored-test"}')
        home=self.root/'home';launch=home/'Library/LaunchAgents';launch.mkdir(parents=True)
        current=home/'Library/Application Support/Augmentor Harness/current';current.parent.mkdir(parents=True);current.symlink_to(app,target_is_directory=True)
        env=dict(AUGMENTOR_PI_CONFIG=self.profile['config'],AUGMENTOR_PI_STATE=self.profile['state'],AUGMENTOR_PI_SOCKET=self.profile['socket'],AUGMENTOR_PI_WORKSPACE=self.profile['workspace'],AUGMENTOR_SHARED_STATE=self.profile['sharedState'],AUGMENTOR_SHARED_DATA=self.profile['sharedData'])
        plist=launch/'com.augmentor.Harness.plist';plist.write_bytes(plistlib.dumps({'Label':'com.augmentor.Harness','EnvironmentVariables':env}));plist.chmod(0o644)
        with patch.dict(os.environ,{'AUGMENTOR_AH_CONNECTION':''}),patch('augmentor_linux.ah_connection.sys.platform','darwin'),patch('augmentor_linux.ah_connection.Path.home',return_value=home):
            result=selection()
        self.assertEqual(result['root'],str(app));self.assertEqual(result['profile'],self.profile)
        self.assertEqual(result['start'][0],'launchctl')

    def shell_installation(self):
        home=self.root/'shell-home';base=home/'Library/Application Support/Augmentor Harness';bin=base/'bin';bin.mkdir(parents=True,mode=0o700)
        app=self.root/'shell-app';app.mkdir();(app/'package.json').write_text('{"version":"authored-test"}');(base/'current').symlink_to(app,target_is_directory=True)
        wrapper=bin/'start-harness';wrapper.write_text('#!/bin/sh\n');wrapper.chmod(0o700)
        profile=dict(self.profile);profile['socket']=str(self.root/'host.sock')
        text='export AUGMENTOR_HARNESS_HOME="$HOME/Library/Application Support/Augmentor Harness"\nexport XDG_RUNTIME_DIR="'+str(self.root)+'"\n'
        names={'config':'AUGMENTOR_PI_CONFIG','state':'AUGMENTOR_PI_STATE','socket':'AUGMENTOR_PI_SOCKET','workspace':'AUGMENTOR_PI_WORKSPACE','sharedState':'AUGMENTOR_SHARED_STATE','sharedData':'AUGMENTOR_SHARED_DATA'}
        text+=''.join('export '+name+'="'+profile[key]+'"\n' for key,name in names.items())
        env=bin/'environment.sh';env.write_text(text);env.chmod(0o700)
        job=home/'Library/LaunchAgents/com.augmentor.Harness.plist';job.parent.mkdir(parents=True);job.write_bytes(plistlib.dumps({'Label':'com.augmentor.Harness','ProgramArguments':[str(wrapper)]}));job.chmod(0o600)
        return home,profile,env,job

    def test_macos_reads_private_shell_installer_without_executing_it(self):
        home,profile,env,_=self.shell_installation()
        text=env.read_text().replace('export XDG_RUNTIME_DIR="'+str(self.root)+'"','export XDG_RUNTIME_DIR="/tmp/authored-$(id -u)"')
        env.write_text(text)
        with patch.dict(os.environ,{'AUGMENTOR_AH_CONNECTION':''}),patch('augmentor_linux.ah_connection.sys.platform','darwin'),patch('augmentor_linux.ah_connection.Path.home',return_value=home),patch('augmentor_linux.ah_connection.subprocess.run') as run:
            value=selection()
        run.assert_not_called();self.assertEqual(value['profile'],profile)
        self.assertEqual(value['start'],['launchctl','kickstart','gui/'+str(os.getuid())+'/com.augmentor.Harness'])

    def test_macos_refuses_dynamic_or_unowned_environment_instead_of_running_shell(self):
        home,profile,env,_=self.shell_installation();original=env.read_text();canary=self.root/'must-not-exist'
        with patch.dict(os.environ,{'AUGMENTOR_AH_CONNECTION':''}),patch('augmentor_linux.ah_connection.sys.platform','darwin'),patch('augmentor_linux.ah_connection.Path.home',return_value=home):
            env.write_text(original.replace(profile['state'],'$(touch '+str(canary)+')'))
            with self.assertRaisesRegex(ValueError,'Dynamic'):selection()
            self.assertFalse(canary.exists())
            env.write_text(original);env.chmod(0o644)
            with self.assertRaisesRegex(ValueError,'private'):selection()


if __name__=='__main__':unittest.main()
