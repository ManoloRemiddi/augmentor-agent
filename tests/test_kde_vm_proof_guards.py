# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Refuse stale native/selected identities and unobserved KDE consent clicks."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]


def functions(path,names):
    # These command-line fixtures intentionally execute only when invoked.
    # Extract their actual pure admission functions without starting SSH/Qt.
    tree=ast.parse(path.read_text())
    selected=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    assert {node.name for node in selected}==set(names)
    namespace={'Path':Path,'json':json,'hashlib':hashlib,'subprocess':subprocess}
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(path),'exec'),namespace)
    return namespace


class SelectedIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code=functions(ROOT/'release/vm-desktop-session.py',('selected_identity','package_query'))

    def setUp(self):
        self.source='3'*40;self.target='fedora44-x86_64';self.store=Path('/home/augmentor-complete-proof/.local/share/augmentor/releases')
        self.root=self.store/'release-proof'
        self.selected={'root':str(self.root),'sourceRef':self.source,'version':'0.2.13','artifactSha256':'a'*64}
        self.release={'source':{'commit':self.source,'dirty':False},'target':self.target,'version':'0.2.13'}
        self.installed=copy.deepcopy(self.release)
        self.deployment={'deployment':copy.deepcopy(self.selected),'artifactSha256':'a'*64}

    def check(self):
        return self.code['selected_identity'](self.root,self.selected,self.release,self.installed,self.deployment,self.source,self.target,self.store)

    def test_selected_native_matching_source(self):
        self.assertEqual(self.check()['source'],self.source)

    def test_changed_selected_and_native_sources_refuse(self):
        for record in (self.release,self.installed):
            with self.subTest(record=record):
                previous=copy.deepcopy(record);record['source']['commit']='4'*40
                with self.assertRaisesRegex(ValueError,'clean source'):self.check()
                record.clear();record.update(previous)

    def test_dirty_native_source_refuses(self):
        self.installed['source']['dirty']=True
        with self.assertRaisesRegex(ValueError,'clean source'):self.check()

    def test_cross_target_and_version_refuse(self):
        self.installed['target']='fedora43-x86_64'
        with self.assertRaisesRegex(ValueError,'target'):self.check()
        self.installed['target']=self.target;self.installed['version']='0.2.12'
        with self.assertRaisesRegex(ValueError,'version'):self.check()

    def test_stale_selection_receipt_refuses(self):
        self.deployment['deployment']['artifactSha256']='b'*64
        with self.assertRaisesRegex(ValueError,'receipt'):self.check()

    def test_missing_and_nonhash_identity_refuse(self):
        for value in (None,'','z'*64):
            with self.subTest(value=value):
                self.selected['artifactSha256']=value
                self.deployment={'deployment':copy.deepcopy(self.selected),'artifactSha256':value}
                with self.assertRaisesRegex(ValueError,'identity'):self.check()

    def test_external_or_traversal_root_refuses(self):
        for root in (Path('/usr/lib/augmentor'),self.store,self.store/'..'/'unselected'):
            with self.subTest(root=root):
                self.root=root
                with self.assertRaisesRegex(ValueError,'managed release'):self.check()

    def test_native_package_adapter_and_unknown_target(self):
        query=self.code['package_query']('fedora44-x86_64')
        self.assertEqual(query[:2],['rpm','-q']);self.assertIn('augmentor-agent',query);self.assertIn('kwin',query)
        self.assertEqual(self.code['package_query']('debian13-amd64')[0],'dpkg-query')
        with self.assertRaises(ValueError):self.code['package_query']('opensuse-leap16.0-x86_64')


class ObservedConsent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code=functions(ROOT/'scripts/vm-desktop-proof.py',('consent_point','load_consent_observation','portal_dialog'))

    def setUp(self):
        self.source='3'*40;self.target='fedora44-x86_64';self.portal='xdg-desktop-portal-kde 6.7.5-1.fc44 x86_64'
        self.record={'format':'augmentor-kde-consent-observation/1','source':self.source,'target':self.target,'portalPackage':self.portal,
            'dialog':{'title':'Synthetic pending consent','application':'org.example.fixture','width':390,'height':240},
            'buttons':{'allow':{'label':'Share','x':310,'y':210},'deny':{'label':'Cancel','x':220,'y':210}}}
        self.window={'title':'Synthetic pending consent','application':'org.example.fixture','geometry':{'x':400,'y':200,'width':390,'height':240}}

    def point(self,allow=True):
        return self.code['consent_point'](self.record,self.window,allow=allow,source=self.source,target=self.target,portal_package=self.portal)

    def test_observed_translated_allow_and_deny(self):
        self.assertEqual(self.point(),(710,410));self.assertEqual(self.point(False),(620,410))

    def test_portal_window_must_be_unique_focused_and_current_owner(self):
        window=dict(self.window,id=7,pid=4321)
        scene={'window':window,'windows':[window]}
        select=self.code['portal_dialog']
        self.assertEqual(select(scene,4321,self.record['dialog']),window)
        self.assertIsNone(select(scene,4322,self.record['dialog']))
        scene['window']=dict(window,id=8)
        self.assertIsNone(select(scene,4321,self.record['dialog']))
        scene['window']=window;scene['windows'].append(dict(window,id=9))
        self.assertIsNone(select(scene,4321,self.record['dialog']))
        scene['windows']=[window];window['title']='Different native window'
        self.assertIsNone(select(scene,4321,self.record['dialog']))

    def test_changed_native_source_target_or_portal_refuses(self):
        for key,value in [('source','4'*40),('target','fedora43-x86_64'),('portalPackage','stale')]:
            with self.subTest(key=key):
                previous=self.record[key];self.record[key]=value
                with self.assertRaisesRegex(ValueError,'source/target/native'):self.point()
                self.record[key]=previous

    def test_changed_application_title_or_geometry_refuses(self):
        for key,value in [('title','Other'),('application','org.example.other')]:
            with self.subTest(key=key):
                previous=self.window[key];self.window[key]=value
                with self.assertRaisesRegex(ValueError,'window'):self.point()
                self.window[key]=previous
        self.window['geometry']['height']=241
        with self.assertRaisesRegex(ValueError,'geometry changed'):self.point()

    def test_blank_labels_and_outside_or_boolean_points_refuse(self):
        self.record['buttons']['allow']['label']=None
        with self.assertRaisesRegex(ValueError,'button label'):self.point()
        self.record['buttons']['allow']['label']='Share'
        for x in (0,390,-1,True,float('nan')):
            with self.subTest(x=x):
                self.record['buttons']['allow']['x']=x
                with self.assertRaisesRegex(ValueError,'outside'):self.point()

    def test_screenshot_bytes_and_redirects_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);screenshot=folder/'synthetic.ppm';screenshot.write_bytes(b'P6\n1 1\n255\n\0\0\0')
            self.record['screenshot']={'file':str(screenshot),'sha256':hashlib.sha256(screenshot.read_bytes()).hexdigest()}
            path=folder/'observation.json';path.write_text(json.dumps(self.record))
            self.assertEqual(self.code['load_consent_observation'](path)['source'],self.source)
            screenshot.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'hash differs'):self.code['load_consent_observation'](path)
            link=folder/'redirect.json';link.symlink_to(path)
            with self.assertRaisesRegex(ValueError,'ordinary file'):self.code['load_consent_observation'](link)

    def test_cli_refuses_unobserved_consent_before_ssh(self):
        command=[sys.executable,'-B',str(ROOT/'scripts/vm-desktop-proof.py'),'--expected-source',self.source,
                 '--expected-target',self.target,'--expected-marker','Isolated Augmentor synthetic test',
                 '--expected-vm-name','synthetic-nonexistent-vm']
        result=subprocess.run(command,text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,2);self.assertIn('screenshot-bound',result.stderr)
        result=subprocess.run([*command,'--observe-consent','--guest-user','augmentor-complete-proof','--guest-uid','1000'],text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,2);self.assertIn('account/UID pair',result.stderr)


class NativeProofHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code=functions(ROOT/'release/vm-desktop-session.py',('window_observation_source','kscreen_environment','configure_scale'))

    def test_compositor_projection_preserves_owner_and_focused_identity(self):
        source=self.code['window_observation_source']()
        driver='''const vm=require('node:vm');let result;
const portal={internalId:'portal-id',pid:4321,resourceClass:'native-portal',caption:'Actual consent',frameGeometry:{x:5,y:10,width:390,height:240}};
const other={...portal,internalId:'editor-id',pid:5678,resourceClass:'editor'};
const context={SERVICE:'synthetic-proof',TOKEN:'synthetic-token',workspace:{activeWindow:portal,stackingOrder:[other,portal],screens:[{name:'Virtual-1',geometry:{x:0,y:0,width:1280,height:800}}]},callDBus:(...args)=>{if(args[0]!=='synthetic-proof'||args[4]!=='synthetic-token')throw Error('report identity differs');result=JSON.parse(args[5]);}};
vm.runInNewContext(SOURCE,context);console.log(JSON.stringify(result));'''.replace('SOURCE',json.dumps(source))
        result=subprocess.run(['node','-e',driver],capture_output=True,text=True,check=True,timeout=10)
        projection=json.loads(result.stdout)
        self.assertEqual(projection['window'],projection['windows'][1])
        self.assertEqual([(w['id'],w['pid'],w['application']) for w in projection['windows']],
                         [('editor-id',5678,'editor'),('portal-id',4321,'native-portal')])
        select=functions(ROOT/'scripts/vm-desktop-proof.py',('portal_dialog',))['portal_dialog']
        self.assertEqual(select(projection,4321),projection['window'])
        self.assertIsNone(select(projection,5678))

    def test_wayland_display_child_changes_only_its_backend(self):
        original={'XDG_SESSION_TYPE':'wayland','WAYLAND_DISPLAY':'wayland-0','QT_QPA_PLATFORM':'xcb','DISPLAY':':1'}
        child=self.code['kscreen_environment'](original)
        self.assertEqual(original['QT_QPA_PLATFORM'],'xcb')
        self.assertEqual(child,{**original,'QT_QPA_PLATFORM':'wayland'})
        for values in ({},dict(original,XDG_SESSION_TYPE='x11'),dict(original,WAYLAND_DISPLAY='')):
            with self.assertRaisesRegex(ValueError,'Wayland session/display'):self.code['kscreen_environment'](values)

    def test_scale_child_has_its_own_bound_and_preserves_timeout(self):
        class DisplayChild:
            DEVNULL=subprocess.DEVNULL
            run=Mock(side_effect=subprocess.TimeoutExpired(['kscreen-doctor'],20))
        self.code['configure_scale'].__globals__['subprocess']=DisplayChild
        try:
            with self.assertRaises(subprocess.TimeoutExpired):
                self.code['configure_scale']('Virtual-1',1.0,{'XDG_SESSION_TYPE':'wayland','WAYLAND_DISPLAY':'wayland-0'})
            args,kwargs=DisplayChild.run.call_args
            self.assertEqual(args[0],['kscreen-doctor','output.Virtual-1.scale.1.0'])
            self.assertEqual(kwargs['timeout'],20);self.assertTrue(kwargs['check'])
            self.assertEqual(kwargs['env']['QT_QPA_PLATFORM'],'wayland')
        finally:self.code['configure_scale'].__globals__['subprocess']=subprocess


class ExistingEditorSave(unittest.TestCase):
    def setUp(self):
        self.code=functions(ROOT/'scripts/vm-desktop-proof.py',('editor_fixture_name','save_owned_editor'))
        self.home='/home/augmentor-complete-proof'
        self.editor={'path':self.home+'/augmentor-desktop-acceptance.txt'}

    def test_existing_fixture_path_is_bound_to_dedicated_home(self):
        self.assertEqual(self.code['editor_fixture_name'](self.editor,self.home),'augmentor-desktop-acceptance.txt')
        for path in ('augmentor-desktop-acceptance.txt',self.home+'/../augmentor-desktop-acceptance.txt',
                     '/home/beta/augmentor-desktop-acceptance.txt',self.home+'/augmentor-desktop-acceptance-saved.txt'):
            with self.subTest(path=path),self.assertRaisesRegex(ValueError,'existing owned'):
                self.code['editor_fixture_name']({'path':path},self.home)

    def test_existing_save_waits_for_exact_readback_without_pathname_input(self):
        reads=[];pending=iter(({'exists':True,'text':'Fixture ready\n'},
                               {'exists':True,'text':'Wayland ASCII verified\n'},
                               {'exists':True,'text':'Wayland ASCII verified\n'}))
        def guest(action,name):
            reads.append((action,name));return next(pending)
        def until(check):
            self.assertFalse(check(),'An old saved file must not satisfy the save check.')
            self.assertTrue(check())
        action=Mock()
        self.code.update(act=action,guest=guest,until=until)
        name=self.code['save_owned_editor'](self.editor,self.home,'Wayland ASCII verified\n')
        action.assert_called_once_with('key',keys=['CTRL','S'])
        self.assertEqual(name,'augmentor-desktop-acceptance.txt')
        self.assertEqual(reads,[('file',name)]*3)

    def test_save_refusal_never_falls_back_to_save_as_or_replays_input(self):
        failure=RuntimeError('Target changed before the key. No input was sent.')
        action=Mock(side_effect=failure);read=Mock();wait=Mock()
        self.code.update(act=action,guest=read,until=wait)
        with self.assertRaisesRegex(RuntimeError,'Target changed'):
            self.code['save_owned_editor'](self.editor,self.home,'Wayland ASCII verified\n')
        action.assert_called_once_with('key',keys=['CTRL','S'])
        read.assert_not_called();wait.assert_not_called()

    def test_same_process_save_as_completion_keeps_scene_change_refusal(self):
        compare=functions(ROOT/'services/desktop/scene.py',('same_scene',))['same_scene']
        before={'window':{'id':'save-dialog','pid':4321,'application':'org.kde.kate','title':'Save File — Kate',
                          'geometry':{'x':100,'y':100,'width':800,'height':600}},'above':[]}
        after=copy.deepcopy(before)
        after['above'].append({'id':'name-completion','pid':4321,
                               'geometry':{'x':300,'y':500,'width':400,'height':30}})
        self.assertFalse(compare(before,after),'A covering completion popup remains a scene change even with the same PID.')


class UnlockedSessionInput(unittest.TestCase):
    def setUp(self):
        self.helper=functions(ROOT/'release/vm-desktop-session.py',('admit_session_state',))
        self.driver=functions(ROOT/'scripts/vm-desktop-proof.py',('require_unlocked_session','qmp','rpc','async_rpc'))
        self.session={'Id':'250','User':'1001','Type':'wayland','Class':'user','Seat':'seat0',
                      'Remote':'no','Active':'yes','State':'active','LockedHint':'no'}
        self.screensaver={'owner':':1.123','pid':17743,'uid':1001,'startTicks':'1190000','active':False}

    def record(self):
        return self.helper['admit_session_state']([self.session],1001,'250',self.screensaver)

    def test_same_ordinary_session_and_actual_screensaver_admit(self):
        self.assertEqual(self.driver['require_unlocked_session'](self.record(),1001),'250')

    def test_native_admission_refusal_is_not_overridden_by_old_unlocked_properties(self):
        record=self.record();record.update(admitted=False,error='Lock changed during native check')
        with self.assertRaisesRegex(ValueError,'Lock changed'):
            self.driver['require_unlocked_session'](record,1001,'250')

    def test_hint_or_actual_screensaver_lock_refuses_independently(self):
        self.session['LockedHint']='yes'
        with self.assertRaisesRegex(ValueError,'locked'):self.record()
        self.session['LockedHint']='no';self.screensaver['active']=True
        with self.assertRaisesRegex(ValueError,'ScreenSaver'):self.record()

    def test_inactive_remote_foreign_greeter_or_unknown_lock_refuses(self):
        for key,value in [('User','1000'),('Type','x11'),('Class','greeter'),('Seat','seat1'),
                          ('Remote','yes'),('Active','no'),('State','closing'),('LockedHint','')]:
            with self.subTest(key=key):
                original=self.session[key];self.session[key]=value
                with self.assertRaises(ValueError):self.record()
                self.session[key]=original

    def test_ambiguous_or_changed_session_refuses(self):
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            self.helper['admit_session_state']([self.session,dict(self.session,Id='251')],1001,'250',self.screensaver)
        record=self.record();record['session']=dict(self.session,Id='251')
        with self.assertRaisesRegex(ValueError,'same ordinary'):
            self.driver['require_unlocked_session'](record,1001,'250')

    def test_missing_or_foreign_screensaver_authority_fails_closed(self):
        for field,value in [('active',None),('uid',1000),('owner',''),('pid',True),('pid',0)]:
            with self.subTest(field=field):
                screen=dict(self.screensaver);screen[field]=value
                with self.assertRaisesRegex(ValueError,'ScreenSaver'):
                    self.helper['admit_session_state']([self.session],1001,'250',screen)

    def test_each_qmp_key_and_button_checks_lock_after_identity_before_dispatch(self):
        sent=[]
        class Wire:
            greeting=True
            def write(self,value):sent.append(json.loads(value))
            def readline(self):
                if self.greeting:self.greeting=False;return b'{"QMP":{}}\n'
                last=sent[-1];value={'name':'owned-vm'} if last['execute']=='query-name' else {}
                return (json.dumps({'id':last['id'],'return':value})+'\n').encode()
        class Connection:
            def __enter__(self):return self
            def __exit__(self,*unused):pass
            def settimeout(self,value):pass
            def connect(self,value):pass
            def makefile(self,*args,**kwargs):return Wire()
        guard=Mock()
        self.driver.update(socket=SimpleNamespace(AF_UNIX=1,socket=lambda *args:Connection()),
                           os=os,vm=Path('/tmp/owned-vm'),a=SimpleNamespace(expected_vm_name='owned-vm'),
                           require_current_session=guard)
        qmp=self.driver['qmp']
        qmp('send-key',{'keys':[]});qmp('input-send-event',{'events':[{'type':'btn','data':{'down':True}}]})
        self.assertEqual([call.args[0] for call in guard.call_args_list],['send-key','input-send-event'])
        guard.side_effect=ValueError('Session locked between mouse press and release')
        before=len(sent)
        with self.assertRaisesRegex(ValueError,'between mouse'):
            qmp('input-send-event',{'events':[{'type':'btn','data':{'down':False}}]})
        self.assertEqual([row['execute'] for row in sent[before:]],['qmp_capabilities','query-name'])
        self.assertEqual(guard.call_count,3,'A prior successful input must not cache unlocked state.')

    def test_portal_request_and_product_input_refuse_before_transport_when_locked(self):
        guard=Mock(side_effect=ValueError('Current session locked'))
        transport=Mock();child=Mock()
        self.driver.update(require_current_session=guard,remote=transport,helper_command=Mock(),
                           subprocess=SimpleNamespace(Popen=child))
        for function in ('rpc','async_rpc'):
            for method in ('connect','action'):
                with self.subTest(function=function,method=method),self.assertRaisesRegex(ValueError,'locked'):
                    self.driver[function](method)
        transport.assert_not_called();child.assert_not_called()

    def test_fast_guard_keeps_selected_identity_without_full_runtime_audit(self):
        code=functions(ROOT/'scripts/vm-desktop-proof.py',('helper_command',))
        root='/home/augmentor-complete-proof/.local/share/augmentor/releases/owned'
        code.update(root=root,guest_python='/home/augmentor-complete-proof/.local/share/augmentor/python/bin/python',
                    a=SimpleNamespace(source=False,guest_root=None,expected_source='3'*40,
                                      expected_target='fedora44-x86_64',guest_uid=1001,guest_user='augmentor-complete-proof'))
        fast=code['helper_command']('session-state');normal=code['helper_command']('rpc')
        self.assertNotIn(root+'/scripts/run-component.py',fast)
        self.assertIn(root+'/scripts/run-component.py',normal)
        self.assertIn('AUGMENTOR_PROOF_SOURCE='+'3'*40,fast)
        self.assertIn('AUGMENTOR_PROOF_UID=1001',fast)
        self.assertEqual(fast[-2:],[root,'session-state'])

    def test_refusal_receipt_keeps_actual_owner_state_and_transport_time(self):
        code=functions(ROOT/'scripts/vm-desktop-proof.py',('require_current_session','require_unlocked_session'))
        record=self.record();record.update(admitted=False,error='Actual lock is active')
        record['screensaver']=dict(self.screensaver,active=True)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'guard.jsonl'
            transport=Mock(return_value=json.dumps(record))
            code.update(time=time,session_id='250',session_guard_path=path,remote=transport,
                        helper_command=Mock(return_value=['fast-guard']),a=SimpleNamespace(guest_uid=1001))
            with self.assertRaisesRegex(ValueError,'Actual lock is active'):
                code['require_current_session']('send-key')
            receipt=json.loads(path.read_text())
            self.assertFalse(receipt['admitted']);self.assertEqual(receipt['sessionState']['screensaver'],record['screensaver'])
            self.assertEqual(receipt['operation'],'send-key');self.assertGreaterEqual(receipt['transportSeconds'],0)
            transport.assert_called_once_with(['fast-guard'],timeout=15)


if __name__=='__main__':unittest.main()
