# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned proof trigger boundary; no native GUI, consent or input is exercised."""
import importlib.util
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

spec=importlib.util.spec_from_file_location('owned_gnome_input_probe',Path(__file__).resolve().parents[1]/'release/probe-gnome-input.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
try:
    import gi
    gi.require_version('Gst','1.0')
    from gi.repository import Gst
except (ImportError,ValueError):Gst=None


class NativeTimeout(RuntimeError):
    domain='g-io-error-quark';code=24


class GnomeInputIdleWatchTraceTests(unittest.TestCase):
    def rpc(self,proxy,method='GetNameOwner',bound=1000):
        parameters=Mock();parameters.unpack.return_value=('org.gnome.Shell',)
        arguments=('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus',method,
            parameters,object(),object(),bound,object())
        return arguments,proxy.call_sync(*arguments)

    def test_owner_rpc_arguments_return_and_bound_forward_once_with_elapsed(self):
        bus=Mock();trace=module.IdleWatchTrace();proxy=module.IdleWatchBus(bus,'verify',trace)
        with patch.object(module.time,'monotonic',side_effect=(5.0,5.125)):
            arguments,result=self.rpc(proxy)
        self.assertIs(result,bus.call_sync.return_value);bus.call_sync.assert_called_once_with(*arguments)
        row=trace.snapshot()['calls'][0]
        self.assertEqual((row['stage'],row['method'],row['lookupName'],row['timeoutMs'],row['elapsedSeconds']),
            ('verify','GetNameOwner','org.gnome.Shell',1000,.125))
        self.assertNotIn('parameters',row);self.assertNotIn('reply',row);self.assertIsNone(trace.snapshot()['firstError'])

    def test_native_timeout_object_and_original_call_survive_trace(self):
        error=NativeTimeout('Timeout was reached');bus=Mock();bus.call_sync.side_effect=error
        trace=module.IdleWatchTrace();proxy=module.IdleWatchBus(bus,'read',trace)
        arguments=(':1.7','/com/augmentor/GnomeObserver','com.augmentor.GnomeObserver','Read',None,None,4,1000,None)
        with patch.object(module.time,'monotonic',side_effect=(5.0,6.01)):
            with self.assertRaises(NativeTimeout) as caught:proxy.call_sync(*arguments)
        self.assertIs(caught.exception,error);bus.call_sync.assert_called_once_with(*arguments)
        first=trace.snapshot()['firstError'];self.assertEqual(first['error']['code'],24)
        self.assertEqual(first['error']['domain'],'g-io-error-quark');self.assertAlmostEqual(first['elapsedSeconds'],1.01)

    def test_public_alias_is_read_before_native_call_consumes_parameters(self):
        class Parameters:
            consumed=False
            def unpack(self):
                if self.consumed:raise RuntimeError('Native call consumed the parameters.')
                return ('org.gnome.Shell',)
        parameters=Parameters();bus=Mock();reply=object()
        def called(*args):self.assertIs(args[4],parameters);parameters.consumed=True;return reply
        bus.call_sync.side_effect=called;trace=module.IdleWatchTrace();proxy=module.IdleWatchBus(bus,'read',trace)
        self.assertIs(proxy.call_sync('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus',
            'GetNameOwner',parameters,None,4,500,None),reply)
        self.assertEqual(trace.snapshot()['calls'][0]['lookupName'],'org.gnome.Shell')
        self.assertEqual(trace.snapshot()['recordingFailures'],0);bus.call_sync.assert_called_once()

    def test_first_error_is_retained_after_bounded_rollover_and_snapshot_is_detached(self):
        trace=module.IdleWatchTrace(limit=2)
        trace.record({'outcome':'error','error':{'code':24},'method':'Read'})
        for _ in range(3):trace.record({'outcome':'reply','method':'GetNameOwner'})
        trace.record({'outcome':'error','error':{'code':19},'method':'GetNameOwner'})
        snapshot=trace.snapshot();self.assertEqual(len(snapshot['calls']),2);self.assertEqual(snapshot['droppedCalls'],3)
        self.assertEqual(snapshot['firstError']['sequence'],1);self.assertEqual(snapshot['firstError']['error']['code'],24)
        snapshot['firstError']['error']['code']=0;self.assertEqual(trace.snapshot()['firstError']['error']['code'],24)

    def test_cleanup_and_other_connection_methods_delegate_without_tracing(self):
        bus=Mock();trace=module.IdleWatchTrace();proxy=module.IdleWatchBus(bus,'verify',trace)
        arguments=(':1.54','/owned/session','org.freedesktop.portal.Session','Close',None,None,4,1000,None)
        self.assertIs(proxy.call_sync(*arguments),bus.call_sync.return_value)
        bus.call_sync.assert_called_once_with(*arguments);proxy.close_sync(None);bus.close_sync.assert_called_once_with(None)
        self.assertEqual(trace.snapshot()['totalCalls'],0)

    def test_recording_failure_never_masks_reply_or_native_error_or_retries(self):
        for native_error in (None,NativeTimeout('Timeout was reached')):
            bus=Mock();bus.call_sync.side_effect=native_error;trace=Mock();trace.record.side_effect=RuntimeError('diagnostic sink failed')
            proxy=module.IdleWatchBus(bus,'verify',trace)
            if native_error is None:self.assertIs(self.rpc(proxy)[1],bus.call_sync.return_value)
            else:
                with self.assertRaises(NativeTimeout) as caught:self.rpc(proxy)
                self.assertIs(caught.exception,native_error)
            self.assertEqual(bus.call_sync.call_count,1);trace.lost.assert_called_once()

    def test_delegate_terminal_result_restores_connections_without_reattaching_disposed_objects(self):
        consent=SimpleNamespace(bus=Mock());native=SimpleNamespace(bus=Mock());original=(consent.bus,native.bus)
        cancelled=threading.Event();terminal=object();argument=object()
        class Base:
            def watch_session(self,*args):
                self.received=args
                if not isinstance(consent.bus,module.IdleWatchBus) or not isinstance(native.bus,module.IdleWatchBus):raise AssertionError('Trace not scoped to delegate.')
                cancelled.set();self.consent=None;self.kwin=None;return terminal
        value=module.traced_controller(Base,module.IdleWatchTrace())();value.consent=consent;value.kwin=SimpleNamespace(native=native)
        self.assertIs(value.watch_session(argument),terminal);self.assertEqual(value.received,(argument,))
        self.assertTrue(cancelled.is_set());self.assertIsNone(value.consent);self.assertIsNone(value.kwin)
        self.assertIs(consent.bus,original[0]);self.assertIs(native.bus,original[1])


@unittest.skipUnless(sys.platform.startswith('linux') and Gst is not None,
    'Candidate import regression requires Linux GStreamer introspection.')
class GnomeInputCandidateImportTests(unittest.TestCase):
    def test_real_idle_watch_keeps_verify_and_read_timeouts_terminal_at_existing_bounds(self):
        from gi.repository import Gio,GLib
        desktop=Path(__file__).resolve().parents[1]/'services/desktop'
        sys.path.insert(0,str(desktop))
        try:
            from gnome_control import GnomeControl
            from gnome import GnomeObserver
            from portal_session import ConsentSession,OWNERS
        finally:sys.path.pop(0)
        for phase in ('verify','read'):
            with self.subTest(phase=phase):
                trace=module.IdleWatchTrace();Control=module.traced_controller(GnomeControl,trace);value=Control.__new__(Control)
                session=ConsentSession.__new__(ConsentSession);session.thread=threading.get_ident()
                session.cancel=threading.Event();session.mutex=threading.Lock();session.generation=0;session.closed=False
                session.rpc_cancel=Gio.Cancellable();session.stop_reason=None;session.on_stopped=None
                session.owners=dict(zip(OWNERS,(':1.54',':1.63',':1.7')));session.bus=Mock()
                error=NativeTimeout('Timeout was reached')
                if phase=='verify':session.bus.call_sync.side_effect=error
                else:session.bus.call_sync.side_effect=lambda *args:GLib.Variant('(s)',(session.owners[args[4].unpack()[0]],))
                observer=GnomeObserver.__new__(GnomeObserver);observer.bus=Mock();observer.Gio=Gio;observer.GLib=GLib
                observer.owner=':1.7';observer.epoch='01234567-89ab-cdef-0123-456789abcdef'
                def observed(*args):
                    if args[3]=='Read':raise error
                    return GLib.Variant('(s)',(':1.7',))
                observer.bus.call_sync.side_effect=observed;original=(session.bus,observer.bus)
                value.consent=session;value.cancel=session.cancel;value.kwin=SimpleNamespace(native=observer);value.last_failure=None
                def stopped():session.request_stop();value.consent=None;value.kwin=None
                value.stop=Mock(side_effect=stopped)
                self.assertEqual(value.watch_session(),GLib.SOURCE_REMOVE);value.stop.assert_called_once()
                self.assertTrue(session.cancel.is_set());self.assertTrue(session.rpc_cancel.is_cancelled())
                self.assertEqual(value.last_failure['phase'],'idle-watch');self.assertEqual(value.last_failure['message'],'Timeout was reached')
                first=trace.snapshot()['firstError'];self.assertEqual(first['stage'],phase);self.assertEqual(first['timeoutMs'],1000)
                self.assertEqual(first['method'],'GetNameOwner' if phase=='verify' else 'Read')
                self.assertEqual(first['error']['code'],24);self.assertIs(session.bus,original[0]);self.assertIs(observer.bus,original[1])
                if phase=='verify':observer.bus.call_sync.assert_not_called();self.assertEqual(session.bus.call_sync.call_count,1)
                else:
                    self.assertEqual([row['timeoutMs'] for row in trace.snapshot()['calls']],[1000,1000,1000,500,1000])
                    self.assertEqual(observer.bus.call_sync.call_count,2)

    def test_eleven_file_candidate_resolves_real_installed_dependency_before_controller_import(self):
        repo=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            candidate=Path(temporary)/'candidate';candidate.mkdir()
            installed=Path(temporary)/'installed';desktop=installed/'services/desktop';desktop.mkdir(parents=True)
            # Use actual maintained modules in the same eleven-file staging
            # shape. KWin is deliberately installed only; no GUI is created.
            for name in ('worker','gnome_control','gnome','portal','portal_session',
                    'capture_stream','scene','a11y_helper','a11y_service'):
                shutil.copy2(repo/'services/desktop'/(name+'.py'),candidate)
            for name in ('probe-gnome-input.py','probe-gnome-input-target.py'):
                shutil.copy2(repo/'release'/name,candidate)
            shutil.copy2(repo/'services/desktop/kwin.py',desktop)
            for name in ('worker','gnome_control','portal'):
                (desktop/(name+'.py')).write_text('raise RuntimeError("Installed controller must not replace the candidate")\n')
            code='''
import importlib.util,json,sys
from pathlib import Path
candidate=Path(sys.argv[1]);installed=Path(sys.argv[2])
spec=importlib.util.spec_from_file_location('import_only_probe',candidate/'probe-gnome-input.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
Worker,GnomeControl=probe.candidate_controller(candidate,installed)
import worker,gnome_control,portal,kwin
assert Worker is worker.Worker and GnomeControl is gnome_control.GnomeControl
assert Path(worker.__file__).parent==candidate and Path(gnome_control.__file__).parent==candidate
assert Path(portal.__file__).parent==candidate and Path(kwin.__file__).parent==installed/'services/desktop'
assert portal.KWin is kwin.KWin
print(json.dumps({'realCandidateModules':True,'installedDependencyResolved':True}))
'''
            result=subprocess.run([sys.executable,'-I','-B','-c',code,str(candidate),str(installed)],
                capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout),{'realCandidateModules':True,'installedDependencyResolved':True})


@unittest.skipUnless(sys.platform.startswith('linux'), 'Owned GNOME input proof requires Linux file ownership and native runtime paths.')
class GnomeInputTriggerTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name);self.path=self.root/'trigger.input.json'

    def write(self,text):self.path.write_text(text);self.path.chmod(0o600)

    def test_private_explicit_synthetic_action_is_read_without_mutating_trigger(self):
        text='{"operation":"action","params":{"kind":"type","text":"synthetic"}}'
        self.write(text);value=module.private_json(self.path)
        self.assertEqual(value['params']['text'],'synthetic');self.assertEqual(self.path.read_text(),text)

    def test_public_permissions_symlink_and_oversized_trigger_refuse(self):
        self.write('{}');self.path.chmod(0o644)
        with self.assertRaisesRegex(RuntimeError,'private bounded'):module.private_json(self.path)
        self.path.chmod(0o600);link=self.root/'link.json';link.symlink_to(self.path)
        with self.assertRaisesRegex(RuntimeError,'private bounded'):module.private_json(link)
        self.write('{"padding":"'+'x'*8192+'"}')
        with self.assertRaisesRegex(RuntimeError,'private bounded'):module.private_json(self.path)

    def test_duplicate_fields_nonfinite_and_nonobject_trigger_refuse(self):
        for text in ('{"operation":"capture","operation":"action"}','{"value":NaN}','{"value":Infinity}','[]'):
            self.write(text)
            with self.subTest(text=text),self.assertRaises((RuntimeError,ValueError)):module.private_json(self.path)


@unittest.skipUnless(sys.platform.startswith('linux'), 'Owned GNOME input proof requires Linux file ownership and native runtime paths.')
class GnomeInputSelectedArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.home=Path(self.temporary.name)/'home';self.data=self.home/'.local/share/augmentor'
        self.root=self.data/'releases'/'owned-release';self.root.mkdir(parents=True,mode=0o700)
        self.native=Path(self.temporary.name)/'native';self.native.mkdir()
        self.source='a'*40;self.native_source='b'*40
        self.release={'source':{'commit':self.source,'dirty':False},'target':'fedora44-x86_64','version':'0.2.13'}
        self.native_release={**self.release,'source':{'commit':self.native_source,'dirty':False}}
        (self.root/'release.json').write_text(json.dumps(self.release))
        (self.native/'release.json').write_text(json.dumps(self.native_release))
        (self.root/'payload.py').write_text('synthetic payload\n')
        self.files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()}
        self.sha=hashlib.sha256(json.dumps(self.files,sort_keys=True).encode()).hexdigest()
        self.selection={'root':str(self.root),'python':'/usr/bin/python3','node':str(self.root/'node/bin/node'),
            'sourceRef':self.source,'artifactSha256':self.sha,'version':'0.2.13','releaseId':'owned-release'}
        self.receipt={'deployment':dict(self.selection),'files':self.files,'artifactSha256':self.sha}
        self.selection_path=self.data/'desktop.json';self.receipt_path=self.root/'desktop-release.json'
        self.write_selection();self.write_receipt()
        # Execute the normal maintained read-only inventory verifier, never a
        # fake success verifier or selected application module.
        self.verifier=self.data/'desktop-deployment.py'
        self.verifier.write_bytes((Path(__file__).resolve().parents[1]/'scripts/desktop-deployment.py').read_bytes());self.verifier.chmod(0o700)
        facade=Mock(side_effect=lambda value:self.native if str(value)=='/usr/lib/augmentor' else Path(value))
        facade.home.return_value=self.home
        patcher=patch.object(module,'Path',facade);patcher.start();self.addCleanup(patcher.stop)
        for patcher in (patch.dict(module.os.environ,{},clear=True),patch.object(module.sys,'executable','/usr/bin/python3'),
                patch.object(module.sys,'prefix','/usr'),patch.object(module.sys,'base_prefix','/usr')):
            patcher.start();self.addCleanup(patcher.stop)
        self.audit=Mock(returncode=0,stdout='',stderr='')
        patcher=patch.object(module.subprocess,'run',return_value=self.audit)
        self.run=patcher.start();self.addCleanup(patcher.stop)

    def write_selection(self):self.selection_path.write_text(json.dumps(self.selection));self.selection_path.chmod(0o600)
    def write_receipt(self):self.receipt_path.write_text(json.dumps(self.receipt));self.receipt_path.chmod(0o600)
    def admitted(self):return module.selected_artifact(self.source,self.sha,self.native_source)

    def test_real_inventory_verifier_admits_exact_distinct_selected_and_native_sources(self):
        before=self.selection_path.read_bytes();result=self.admitted()
        self.assertEqual(result['selection'],self.selection)
        self.assertEqual(result['nativeSource'],self.native_source);self.assertNotEqual(self.source,self.native_source)
        self.assertTrue(result['managedInventoryVerified']);self.assertTrue(result['deploymentReceiptMatchesSelection'])
        self.assertEqual(result['deploymentVerifierSha256'],hashlib.sha256(self.verifier.read_bytes()).hexdigest())
        self.assertEqual(self.selection_path.read_bytes(),before)
        self.run.assert_called_once_with(['rpm','-V','augmentor-agent'],capture_output=True,text=True,timeout=30)

    def test_selected_source_and_explicit_artifact_hash_mismatch_refuse_before_audit(self):
        for key,bad in (('sourceRef','c'*40),('artifactSha256','c'*64)):
            original=self.selection[key];self.selection[key]=bad;self.write_selection()
            with self.subTest(key=key),self.assertRaisesRegex(RuntimeError,'source or artifact hash differs'):self.admitted()
            self.run.assert_not_called();self.selection[key]=original

    def test_selected_native_wrong_source_target_dirty_or_version_refuse(self):
        cases=((self.root,self.release,'target','ubuntu24.04-amd64'),
            (self.native,self.native_release,'target','fedora43-x86_64'),
            (self.root,self.release,'source',{'commit':self.source,'dirty':True}),
            (self.native,self.native_release,'source',{'commit':'c'*40,'dirty':False}),
            (self.native,self.native_release,'version','0.2.14'))
        for directory,original,key,bad in cases:
            (directory/'release.json').write_text(json.dumps({**original,key:bad}))
            with self.subTest(directory=directory,key=key),self.assertRaisesRegex(RuntimeError,'source/target|versions differ'):self.admitted()
            self.run.assert_not_called();(directory/'release.json').write_text(json.dumps(original))

    def test_changed_or_added_payload_refuses_real_normal_inventory(self):
        (self.root/'payload.py').write_text('changed bytes\n')
        with self.assertRaisesRegex(ValueError,'Release files changed after staging'):self.admitted()
        (self.root/'payload.py').write_text('synthetic payload\n');(self.root/'extra.py').write_text('unrecorded bytes\n')
        with self.assertRaisesRegex(ValueError,'Release files changed after staging'):self.admitted()

    def test_forged_inventory_digest_or_stale_deployment_receipt_refuse(self):
        self.receipt['artifactSha256']='c'*64;self.write_receipt()
        with self.assertRaisesRegex(ValueError,'inventory identity does not match'):self.admitted()
        self.receipt['artifactSha256']=self.sha;self.receipt['deployment']['node']='/unrelated/node';self.write_receipt()
        with self.assertRaisesRegex(RuntimeError,'receipt differs from the exact selection'):self.admitted()

    def test_selected_venv_and_managed_or_source_qt_policy_refuse(self):
        self.selection['python']=str(self.root/'venv/bin/python');self.write_selection()
        with self.assertRaisesRegex(RuntimeError,'selected interpreter differs'):self.admitted()
        self.selection['python']='/usr/bin/python3';self.write_selection()
        for directory in (self.root,self.native):
            policy=directory/'linux-python-runtime.json';policy.symlink_to(directory/'missing-policy')
            with self.subTest(directory=directory),self.assertRaisesRegex(RuntimeError,'managed or source Qt'):self.admitted()
            policy.unlink()
        self.run.assert_not_called()

    def test_actual_interpreter_venv_and_inherited_loader_overrides_refuse(self):
        with patch.object(module.sys,'executable','/unrelated/python'):
            with self.assertRaisesRegex(RuntimeError,'approved native'):self.admitted()
        with patch.object(module.sys,'prefix','/venv'):
            with self.assertRaisesRegex(RuntimeError,'approved native'):self.admitted()
        for name in ('LD_PRELOAD','LD_AUDIT','LD_LIBRARY_PATH','QT_PLUGIN_PATH','PYTHONPATH','PYTHONHOME','VIRTUAL_ENV'):
            with self.subTest(name=name),patch.dict(module.os.environ,{name:'/unrelated'}):
                with self.assertRaisesRegex(RuntimeError,'inherited loader'):self.admitted()
        with patch.dict(module.os.environ,{'AUGMENTOR_PYTHON':'/unrelated/python'}):
            with self.assertRaisesRegex(RuntimeError,'requested interpreter differs'):self.admitted()
        self.run.assert_not_called()

    def test_native_rpm_change_nonzero_or_diagnostic_output_refuse(self):
        for code,stdout,stderr in ((1,'',''),(0,'changed native member',''),(0,'','warning')):
            self.audit.returncode=code;self.audit.stdout=stdout;self.audit.stderr=stderr
            with self.subTest(code=code,stdout=stdout,stderr=stderr),self.assertRaisesRegex(RuntimeError,'RPM audit is not clean'):self.admitted()

    def test_public_selection_or_external_managed_root_refuse(self):
        self.selection_path.chmod(0o644)
        with self.assertRaisesRegex(RuntimeError,'private bounded'):self.admitted()
        self.selection_path.chmod(0o600);self.selection['root']=str(self.native);self.write_selection()
        with self.assertRaisesRegex(RuntimeError,'canonical managed release'):self.admitted()
        self.run.assert_not_called()

    def test_shared_writable_or_symlink_deployment_verifier_refuse(self):
        self.verifier.chmod(0o722)
        with self.assertRaisesRegex(RuntimeError,'normal owned deployment verifier'):self.admitted()
        moved=self.verifier.with_suffix('.saved');self.verifier.rename(moved);self.verifier.symlink_to(moved)
        with self.assertRaisesRegex(RuntimeError,'normal owned deployment verifier'):self.admitted()


if __name__=='__main__':unittest.main()
