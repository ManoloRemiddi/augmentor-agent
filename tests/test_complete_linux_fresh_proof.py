# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One-shot fresh Mint proof fences, distinct from actual VM acceptance."""
import copy
from contextlib import ExitStack
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
spec = importlib.util.spec_from_file_location('fresh_complete_proof', ROOT/'release/prove-complete-linux.py')
proof = importlib.util.module_from_spec(spec); spec.loader.exec_module(proof)


def binding():
    return {'format': 'augmentor-owned-mint-fresh-emulated/1', 'sourceCommit': proof.FRESH_SOURCE,
            'artifactId': proof.FRESH_ARTIFACT, 'bundleManifestSha256': proof.FRESH_MANIFEST_SHA,
            'setupSha256': proof.FRESH_SETUP_SHA, 'target': 'linuxmint22.3-amd64',
            'uid': 1002, 'gid': 1002, 'user': 'augmentor-corrected-proof', 'home': str(proof.FRESH_HOME),
            'markerSha256': hashlib.sha256(proof.POST_MARKER_TEXT.encode()).hexdigest(),
            'proofScriptSha256': proof.PROOF_SHA256, 'bootArgvSha256': proof.FRESH_BOOT_ARGV_SHA,
            'startupDirectory': '/owned/recorded/startup',
            'startupBudgetSeconds': 120, 'turnBudgetSeconds': 60, 'qemuName': 'augmentor-mint223-cinnamon-iso',
            'qemuPid': 2494740, 'runToken': 'ab'*16, 'modelApiPort': 36187, 'dshPort': 41603}


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux fixture fences')
class FreshAdmission(unittest.TestCase):
    def test_exact_binding_refuses_old_artifact_user_budget_or_adoption_before_host_reads(self):
        fixture = binding(); proof.fresh_binding(fixture)
        for key, value in [('sourceCommit', proof.POST_SOURCE), ('artifactId', 'same-version-other-build'),
                           ('uid', 1001), ('uid', True), ('gid', 1000), ('home', str(proof.POST_HOME)),
                           ('setupSha256', '0'*64), ('startupBudgetSeconds', 60), ('turnBudgetSeconds', 120)]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                proof.fresh_host_preflight({**fixture, key: value})
        for fields in ({'runToken': 'token'}, {'modelApiPort': fixture['dshPort']}, {'priorFailure': {}}, {'settings': {}}):
            with self.assertRaises(ValueError): proof.fresh_binding({**fixture, **fields})

    def test_each_preexisting_settings_application_or_journal_refuses_before_native_or_bind(self):
        for name in ('.local/share/augmentor', '.config/augmentor', '.local/state/augmentor-install', '.local/state/augmentor', '.dsh', proof.FRESH_RUN_DIRECTORY):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                home = Path(directory); path = home/name; path.parent.mkdir(parents=True, exist_ok=True); path.mkdir()
                with patch.object(proof, 'FRESH_HOME', home), patch.object(proof, 'fresh_vm_identity'), \
                     patch.object(proof, 'fresh_native_bundle') as native, patch.object(proof, 'require_ports_idle') as ports:
                    with self.assertRaisesRegex(ValueError, 'absent application'): proof.validate_fresh_fixture(home, binding())
                    native.assert_not_called(); ports.assert_not_called()

    def test_exclusive_current_token_journal_never_adopts_another_run_even_same_source(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(proof, 'FRESH_HOME', Path(directory)):
            fixture = binding(); root, record = proof.begin_fresh_run(fixture); raw = (root/'run.json').read_bytes()
            with self.assertRaisesRegex(ValueError, 'one-shot journal exists'):
                proof.begin_fresh_run({**fixture, 'runToken': 'cd'*16})
            self.assertEqual((root/'run.json').read_bytes(), raw)
            self.assertEqual(record['run'], fixture['runToken'])

    def test_external_audit_requires_same_proof_and_entire_fixture_before_lease_readback(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(proof, 'FRESH_HOME', Path(directory)):
            fixture = binding(); root, record = proof.begin_fresh_run(fixture)
            proof.fresh_audit_record(record, fixture)
            for field, value in [('proofScriptSha256', '0'*64), ('fixtureSha256', '1'*64), ('run', 'cd'*16),
                                 ('bundleManifestSha256', '2'*64)]:
                with self.assertRaisesRegex(ValueError, 'journal/tool/fixture'):
                    proof.fresh_audit_record({**record, field: value}, fixture)
            for extra in ({'dshPort': 41604}, {'hostPreflightSha256': '3'*64}, {'qemuDisk': '/changed-owned-disk'}):
                with self.assertRaisesRegex(ValueError, 'journal/tool/fixture'):
                    proof.fresh_audit_record(record, {**fixture, **extra})
            with self.assertRaises(ValueError): proof.fresh_binding({**fixture, 'proofScriptSha256': '4'*64})

    def test_one_shot_setup_response_loss_retains_pending_without_an_installer_retry(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(proof, 'FRESH_HOME', Path(directory)):
            root, record = proof.begin_fresh_run(binding()); installer = Mock(side_effect=OSError('lost setup outcome'))
            with self.assertRaisesRegex(OSError, 'lost setup'): proof.fresh_once(root, record, 'setup.initial', installer)
            with self.assertRaisesRegex(ValueError, 'never retried'): proof.fresh_once(root, record, 'setup.initial', installer)
            installer.assert_called_once(); self.assertEqual(record['pendingRequest'], {'action': 'setup.initial'})
            self.assertEqual(record['completedActions'], [])

    def test_daemon_relative_launch_uses_bound_startup_and_open_fd_not_current_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); proc = root/'2494740'; (proc/'fd').mkdir(parents=True); (proc/'net').mkdir()
            disk = root/'guest.qcow2'; disk.write_bytes(b'owned synthetic disk'); (proc/'fd/4').symlink_to(disk)
            endpoint = root/'qmp.sock'; stat_text = '1 (qemu fixture) '+' '.join(['0']*19+['73'])
            (proc/'cwd').symlink_to('/')
            with socket.socket(socket.AF_UNIX) as qmp:
                qmp.bind(str(endpoint)); qmp.listen(2)
                args = [b'/usr/bin/qemu-system-x86_64', b'-name', b'augmentor-mint223-cinnamon-iso',
                        b'-drive', b'file=guest.qcow2,format=qcow2,if=virtio', b'-qmp', b'unix:qmp.sock,server=on,wait=off', b'-daemonize']
                (proc/'cmdline').write_bytes(b'\0'.join(args)+b'\0'); (proc/'stat').write_text(stat_text)
                (proc/'fd/7').symlink_to('/proc/self/fd/'+str(qmp.fileno()))
                (proc/'net/unix').write_text(Path('/proc/net/unix').read_text())
                normalized = [os.fsdecode(v) for v in args]; normalized[0] = Path(normalized[0]).name
                digest = hashlib.sha256(json.dumps(normalized,separators=(',',':')).encode()).hexdigest()
                fixture = {**binding(), 'startupDirectory': str(root), 'qemuDisk': str(disk), 'qmpSocket': str(endpoint),
                           'guestBootId': 'owned-boot', 'bootArgvSha256': digest}
                real_path = Path; real_readlink = os.readlink
                sock_link = real_readlink('/proc/self/fd/'+str(qmp.fileno()))
                def paths(value): return root if str(value) == '/proc' else real_path(value)
                def links(value): return sock_link if Path(value) == proc/'fd/7' else real_readlink(value)
                with patch.object(proof, 'Path', side_effect=paths), patch.object(proof, 'FRESH_BOOT_ARGV_SHA', digest), \
                     patch.object(proof.os, 'readlink', side_effect=links), patch.object(proof, 'fresh_qmp_peer') as peer:
                    peer.return_value = {'pid': 2494740, 'uid': os.getuid(), 'gid': os.getgid(), 'protocolBytesSent': 0}
                    result = proof.fresh_host_preflight(fixture)
                    self.assertTrue(result['noHostDevicesOrMounts']); self.assertEqual(result['qemuStart'], '73')
                    self.assertEqual(result['startupDirectory'], str(root)); peer.assert_called_once_with(endpoint,2494740)
                    (proc/'cmdline').write_bytes(b'\0'.join(args+[b'-device', b'vfio-pci,host=00:01.0'])+b'\0')
                    with self.assertRaisesRegex(ValueError, 'no-host-device'): proof.fresh_host_preflight(fixture)
                    (proc/'cmdline').write_bytes(b'\0'.join(args)+b'\0')
                    (proc/'fd/4').unlink()
                    with self.assertRaisesRegex(ValueError, 'process/disk changed'): proof.fresh_host_preflight(fixture)
                    (proc/'fd/4').symlink_to(disk)
                    def replacement(*args):
                        (proc/'stat').write_text(stat_text[:-2]+'74'); return peer.return_value
                    peer.side_effect = replacement
                    with self.assertRaisesRegex(ValueError, 'start/owner changed after'): proof.fresh_host_preflight(fixture)

    def test_parser_accepts_same_dir_absolute_paths_but_rejects_wrong_parent_traversal_and_ambiguity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); disk = root/'guest.qcow2'; disk.write_bytes(b'owned disk'); endpoint = root/'qmp.sock'
            with socket.socket(socket.AF_UNIX) as qmp:
                qmp.bind(str(endpoint)); fixture = {'startupDirectory': str(root), 'qemuDisk': str(disk), 'qmpSocket': str(endpoint)}
                def args(drive, address): return [b'qemu-system-x86_64', b'-drive', drive.encode(), b'-qmp', address.encode()]
                correct = args('file='+str(disk)+',format=qcow2,if=virtio', 'unix:'+str(endpoint)+',server=on,wait=off')
                self.assertEqual(proof.fresh_qemu_paths(correct,fixture), (disk,endpoint,str(endpoint)))
                for drive in ('file=../guest.qcow2,format=qcow2,if=virtio', 'file=/wrong/guest.qcow2,format=qcow2,if=virtio',
                              'file=guest.qcow2,file=guest.qcow2,format=qcow2,if=virtio'):
                    with self.assertRaises(ValueError): proof.fresh_qemu_paths(args(drive,'unix:qmp.sock,server=on,wait=off'),fixture)
                for address in ('unix:../qmp.sock,server=on,wait=off','unix:/wrong/qmp.sock,server=on,wait=off',
                                'unix:qmp.sock,server=on,server=on,wait=off'):
                    with self.assertRaises(ValueError): proof.fresh_qemu_paths(args('file=guest.qcow2,format=qcow2,if=virtio',address),fixture)
                for extra in ([b'-drive', b'file=guest.qcow2,format=qcow2,if=virtio'], [b'-qmp', b'unix:qmp.sock,server=on,wait=off']):
                    with self.assertRaisesRegex(ValueError, 'ambiguous'): proof.fresh_qemu_paths(correct+extra,fixture)
                with self.assertRaises(ValueError): proof.fresh_qemu_paths(correct,{**fixture,'startupDirectory': str(root.parent)})

    def test_real_unix_peer_attribution_sends_zero_protocol_bytes_and_closes_even_for_foreign_pid(self):
        with tempfile.TemporaryDirectory() as directory, socket.socket(socket.AF_UNIX) as server:
            endpoint = Path(directory)/'qmp.sock'; server.bind(str(endpoint)); server.listen(2); server.settimeout(2)
            result = proof.fresh_qmp_peer(endpoint, os.getpid())
            self.assertEqual(result['protocolBytesSent'], 0); self.assertEqual(result['uid'], os.getuid())
            peer, _ = server.accept()
            with peer: peer.settimeout(2); self.assertEqual(peer.recv(1), b'')
            captured = []; real_open = os.open
            def opened(*args, **kwargs):
                fd = real_open(*args, **kwargs); captured.append(fd); return fd
            with patch.object(proof.os, 'open', side_effect=opened), self.assertRaisesRegex(ValueError, 'foreign peer'):
                proof.fresh_qmp_peer(endpoint, os.getpid()+1)
            self.assertEqual(len(captured),1)
            with self.assertRaises(OSError): os.fstat(captured[0])
            peer, _ = server.accept()
            with peer: peer.settimeout(2); self.assertEqual(peer.recv(1), b'')

    def test_real_long_parent_uses_local_fd_anchor_without_chdir_or_fd_leak(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/('a'*70)/('b'*70); root.mkdir(parents=True, mode=0o700)
            endpoint = root/'qmp.sock'; self.assertGreater(len(str(endpoint).encode()), 108)
            before = Path.cwd(); bind_directory = os.open(root, os.O_RDONLY|os.O_DIRECTORY)
            with socket.socket(socket.AF_UNIX) as server:
                try: server.bind('/proc/self/fd/'+str(bind_directory)+'/qmp.sock')
                finally: os.close(bind_directory)
                server.listen(2); server.settimeout(2); captured = []; real_open = os.open
                def opened(*args, **kwargs):
                    fd = real_open(*args, **kwargs); captured.append(fd); return fd
                with patch.object(proof.os, 'open', side_effect=opened): result = proof.fresh_qmp_peer(endpoint,os.getpid())
                self.assertEqual(Path.cwd(), before); self.assertEqual(result['protocolBytesSent'], 0)
                self.assertEqual(len(captured), 1)
                with self.assertRaises(OSError): os.fstat(captured[0])
                peer, _ = server.accept()
                with peer: peer.settimeout(2); self.assertEqual(peer.recv(1), b'')

    def test_directory_socket_or_mode_replacement_refuses_and_closes_both_descriptors(self):
        for replacement in ('directory', 'socket', 'mode'):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as directory:
                base = Path(directory); root = base/'startup'; root.mkdir(mode=0o700); endpoint = root/'qmp.sock'
                with socket.socket(socket.AF_UNIX) as server, socket.socket(socket.AF_UNIX) as other:
                    server.bind(str(endpoint)); server.listen(2); server.settimeout(2)
                    real_socket = socket.socket; real_open = os.open; captured = []; clients = []
                    class Peer:
                        def __init__(self, *args, **kwargs): self.inner=real_socket(*args,**kwargs); clients.append(self.inner)
                        def settimeout(self, value): self.inner.settimeout(value)
                        def connect(self, value): self.inner.connect(value)
                        def getsockopt(self, *args):
                            value = self.inner.getsockopt(*args)
                            if replacement == 'directory': root.rename(base/'retired'); root.mkdir(mode=0o700)
                            elif replacement == 'socket': endpoint.rename(root/'retired.sock'); other.bind(str(endpoint))
                            else: endpoint.chmod(0o700)
                            return value
                        def close(self): self.inner.close()
                    def opened(*args, **kwargs):
                        fd = real_open(*args, **kwargs); captured.append(fd); return fd
                    with patch.object(proof.os, 'open', side_effect=opened), patch.object(proof.socket, 'socket', side_effect=Peer), \
                         self.assertRaisesRegex(ValueError, 'replaced or changed'):
                        proof.fresh_qmp_peer(endpoint,os.getpid())
                    self.assertEqual(len(captured),1)
                    with self.assertRaises(OSError): os.fstat(captured[0])
                    self.assertEqual(clients[0].fileno(), -1)
                    peer, _ = server.accept()
                    with peer: peer.settimeout(2); self.assertEqual(peer.recv(1), b'')

    def test_native_manifest_substitution_refuses_before_import_or_package_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory); (bundle/'bundle.json').write_text('{}')
            with patch.object(proof, 'proof_module') as importer, self.assertRaisesRegex(ValueError, 'manifest differs'):
                proof.fresh_native_bundle(bundle, binding())
            importer.assert_not_called()

    def test_wrong_root_marker_refuses_before_distro_checks_or_any_installer(self):
        fixture = binding()
        entry = SimpleNamespace(pw_name=fixture['user'], pw_dir=fixture['home'], pw_uid=1002, pw_gid=1002)
        marker = SimpleNamespace(lstat=lambda: SimpleNamespace(st_mode=0o100644, st_uid=0, st_nlink=1),
                                 read_text=lambda: 'different VM marker\n')
        with patch.dict(os.environ, {'HOME': str(proof.FRESH_HOME)}, clear=True), \
             patch.object(proof.os, 'getuid', return_value=1002), patch.object(proof.os, 'geteuid', return_value=1002), \
             patch.object(proof.os, 'getgid', return_value=1002), patch.object(proof.os, 'getgroups', return_value=[1002]), \
             patch.object(Path, 'home', return_value=proof.FRESH_HOME), patch('pwd.getpwuid', return_value=entry), \
             patch.object(proof, 'POST_MARKER', marker), patch.object(proof.subprocess, 'check_output') as native:
            with self.assertRaisesRegex(ValueError, 'marker differs'): proof.fresh_vm_identity(fixture)
            native.assert_not_called()

    def test_foreign_effective_uid_refuses_before_marker_or_native_reads(self):
        with patch.object(proof.os, 'getuid', return_value=1002), patch.object(proof.os, 'geteuid', return_value=0), \
             patch.object(proof, 'POST_MARKER') as marker:
            with self.assertRaisesRegex(ValueError, 'ordinary fresh Mint account'): proof.fresh_vm_identity(binding())
            marker.lstat.assert_not_called()

    def test_missing_installed_receipt_does_not_allow_idempotent_setup(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(proof, 'FRESH_HOME', Path(directory)):
            path = Path(directory)/'.local/state/augmentor-install'; path.mkdir(parents=True)
            (path/'installation.json').write_text(json.dumps({'status': 'preparing', 'bundle': proof.FRESH_ARTIFACT, 'target': 'linuxmint22.3-amd64'}))
            (path/'installation.json').chmod(0o600)
            with self.assertRaisesRegex(ValueError, 'known successful exact receipt'):
                proof.fresh_installed_selection({'target': 'linuxmint22.3-amd64'}, binding())


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux finite proof')
class FreshExecution(unittest.TestCase):
    def execution(self, directory, *, host_delay=0, turn_read_delay=0, lost=False, changed=False, repeat_changed=False, history_changed=False, stalled=False, turn_stalled=False, setup_lost=False):
        home = Path(directory)/'fresh'; home.mkdir(mode=0o700); app = Path(directory)/'app'; app.mkdir()
        fixture = binding(); fixture['home'] = str(home); clock = SimpleNamespace(now=0, reads=0)
        desktop = {'python': str(app/'python'), 'dshService': 'augmentor-dsh.service'}
        manifest = {'version': '0.2.13', 'target': 'linuxmint22.3-amd64', 'artifactId': proof.FRESH_ARTIFACT}
        processes = []; mutations = []; requests = []; histories = {}; setup_calls = []
        def run(command, **kwargs):
            self.assertEqual(kwargs['cwd'], str(home))
            if '--preview' in command:
                Path(command[-1]).write_bytes(b'owned synthetic pixels'*1000); return
            self.assertEqual(Path(command[2]).name, 'setup.py'); self.assertIn('--skip-packages', command); self.assertIn('--no-services', command)
            setup_calls.append(command)
            if setup_lost: raise OSError('setup child outcome unavailable')
            for name in proof.POST_SETTINGS:
                path = home/name; path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists(): path.write_text('unchanged fixture '+name); path.chmod(0o600)
            data = home/'.local/share/augmentor'
            for path in (home/'.config/autostart/com.augmentor.Agent.desktop', home/'.local/share/applications/com.augmentor.Agent.secondary.desktop',
                         home/'.config/chromium/NativeMessagingHosts/com.augmentor.agent.json', data/'browser/0.2.13/voice.mjs'):
                path.parent.mkdir(parents=True, exist_ok=True); path.touch()
            for plugin in ('dsh-resonant-voice', 'dsh-adaptive-reasoning', 'dsh-model-picker-augmented'):
                path = data/'dsh-home/profiles/web/node_modules'/plugin/'package.json'; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('{}')
            workspace = data/'dsh-home/storages/workspace.json'; workspace.parent.mkdir(parents=True, exist_ok=True)
            workspace.write_text(json.dumps({'tables': {'workspaces': {}}})); workspace.chmod(0o600)
            if repeat_changed and len(setup_calls) == 2:
                path = home/'.config/augmentor/harnesses.json'; path.write_text(path.read_text()+'  ')
        def make_process(*args, **kwargs):
            self.assertEqual(kwargs['cwd'], str(home)); p = Mock(); p.poll.return_value = None; p.wait.return_value = 0; processes.append(p); return p
        def call(method, payload=None):
            payload = payload or {}; sid = payload.get('sessionId')
            if method == 'host.describe':
                clock.reads += 1
                if stalled: raise ValueError('not ready')
                clock.now += host_delay; return {}
            if method == 'session.list': return {'items': [{'sessionId': sid, 'running': turn_stalled} for sid in histories]}
            if method == 'session.history':
                clock.now += turn_read_delay
                result = copy.deepcopy(histories[sid])
                if len(processes) > 1 and history_changed: result['events'].append({'unexpected': True})
                return result
            mutations.append((method, sid))
            if method == 'session.create': histories[sid] = {'header': {'id': sid}, 'events': []}
            if method == 'session.prompt':
                requests.append({'session': sid})
                if not turn_stalled: histories[sid]['events'].append({'text': 'LINUX DISTRO FIXTURE VERIFIED'})
                if changed:
                    path = home/'.local/share/augmentor/dsh-home/settings.yaml'; path.write_text(path.read_text()+'  ')
                if lost: raise OSError('lost prompt response')
            return {}
        adapter = SimpleNamespace(product=True, call=call); server = Mock(); companion = SimpleNamespace(attempted=False, record={})
        def finish():
            self.assertFalse(companion.attempted); companion.attempted = True; companion.record = {'status': 'pass', 'companionStarted': False}; return companion.record
        companion.finish = Mock(side_effect=finish)
        def model_server(values, port):
            self.assertEqual(port, fixture['modelApiPort'])
            def dispatch(method, payload=None):
                before = len(requests)
                try: return call(method, payload)
                finally: values.extend(requests[before:])
            adapter.call = dispatch; return server
        fake = ModuleType('augmentor_linux.adapters.dsh'); fake.DshAdapter = lambda: adapter
        stack = ExitStack(); stack.enter_context(patch.dict(os.environ, {'PATH': os.defpath}, clear=True))
        stack.enter_context(patch.object(proof, 'FRESH_HOME', home)); stack.enter_context(patch.object(proof, 'POST_APP', app))
        stack.enter_context(patch.object(proof, 'validate_fresh_fixture', return_value=manifest))
        stack.enter_context(patch.object(proof, 'fresh_installed_selection', return_value=(desktop, {'PATH': os.defpath})))
        stack.enter_context(patch.object(proof, 'fixture_model_server', side_effect=model_server))
        stack.enter_context(patch.object(proof, 'memory_companion', return_value=companion))
        stack.enter_context(patch.object(proof, 'run', side_effect=run))
        stack.enter_context(patch.object(proof.threading, 'Thread', return_value=Mock()))
        stack.enter_context(patch.object(proof.time, 'monotonic', side_effect=lambda: clock.now))
        stack.enter_context(patch.object(proof.time, 'sleep', side_effect=lambda amount: setattr(clock, 'now', clock.now+amount)))
        stack.enter_context(patch.dict(sys.modules, {'augmentor_linux.adapters.dsh': fake}))
        stack.enter_context(patch('platform_adapters.processes.OwnedProcess', side_effect=make_process))
        return SimpleNamespace(stack=stack, home=home, fixture=fixture, clock=clock, processes=processes, mutations=mutations,
                               server=server, companion=companion, setup_calls=setup_calls)

    def record(self, fixture): return json.loads((fixture.home/proof.FRESH_RUN_DIRECTORY/'run.json').read_text())

    def test_success_uses_exact_installer_twice_then_two_run_bound_roles_strict_restart_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            x = self.execution(directory, host_delay=75)
            with x.stack: report = proof.fresh_emulated_proof(Path(directory)/'bundle', x.fixture)
            self.assertEqual(len(x.setup_calls), 2); self.assertEqual(len(x.processes), 2)
            self.assertEqual([m for m, s in x.mutations].count('session.prompt'), 2)
            self.assertTrue(all(x.fixture['runToken'] in sid for m, sid in x.mutations))
            self.assertEqual([row['elapsedSeconds'] for row in report['startupObservations']], [75, 75])
            self.assertTrue(report['savedSettingsPreserved']); self.assertFalse(report['originalPublic60FullProofPass'])
            self.assertEqual(report['startupBudgetSeconds'], 120); self.assertEqual(report['turnBudgetSeconds'], 60)
            self.assertTrue(report['externalLeaseAuditRequired']); self.assertEqual(self.record(x)['status'], 'complete')
            x.companion.finish.assert_called_once(); x.server.shutdown.assert_called_once()
            for p in x.processes: p.terminate.assert_called_once(); p.close.assert_called_once()

    def test_successful_authenticated_read_crossing120_refuses_before_any_sdk_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            x = self.execution(directory, host_delay=121)
            with x.stack, self.assertRaisesRegex(RuntimeError, 'exceeded120seconds'):
                proof.fresh_emulated_proof(Path(directory)/'bundle', x.fixture)
            self.assertEqual(x.clock.reads, 1); self.assertEqual(x.mutations, [])
            record = self.record(x); self.assertEqual(record['status'], 'failed'); self.assertFalse(record['unknownRequestOutcome'])
            self.assertFalse(record['startupObservations'][0]['ready']); self.assertTrue(record['startupObservations'][0]['readinessObserved'])
            x.companion.finish.assert_called_once(); x.processes[0].close.assert_called_once()

    def test_live_child_early_exit_is_recorded_and_never_restarted(self):
        child = Mock(); child.poll.return_value = 17; observations = []; factory = Mock(return_value=child)
        with patch.object(proof.time, 'monotonic', return_value=73), \
             self.assertRaisesRegex(RuntimeError, 'exited; no startup is retried'):
            proof.fresh_start(factory, Mock(), observations)
        factory.assert_called_once(); child.terminate.assert_not_called(); child.close.assert_called_once()
        self.assertEqual(observations, [{'ready': False, 'elapsedSeconds': 0, 'processExit': 17}])

    def test_turn_remains60_after_qualified75_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            x = self.execution(directory, host_delay=75, turn_stalled=True)
            with x.stack, self.assertRaisesRegex(RuntimeError, 'within60seconds'):
                proof.fresh_emulated_proof(Path(directory)/'bundle', x.fixture)
            self.assertGreaterEqual(x.clock.now, 135); self.assertLess(x.clock.now, 135.11)
            self.assertEqual([m for m, s in x.mutations].count('session.prompt'), 1)

    def test_finished_history_returning_past60_refuses_before_browser_or_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            x = self.execution(directory, turn_read_delay=61)
            with x.stack, self.assertRaisesRegex(RuntimeError, 'turn reads exceeded60seconds'):
                proof.fresh_emulated_proof(Path(directory)/'bundle', x.fixture)
            self.assertEqual([m for m, s in x.mutations].count('session.prompt'), 1)
            self.assertEqual(len(x.processes), 1)
            record = self.record(x); observation = record['turnObservations'][0]
            self.assertTrue(observation['completionObserved']); self.assertFalse(observation['withinBudget'])
            self.assertEqual(observation['elapsedSeconds'], 61); self.assertFalse(record['unknownRequestOutcome'])
            self.assertFalse((x.home/proof.FRESH_RUN_DIRECTORY/'report.json').exists())

    def test_unknown_prompt_dispatches_once_retains_pending_and_never_restarts_or_replays(self):
        with tempfile.TemporaryDirectory() as directory:
            x = self.execution(directory, lost=True)
            with x.stack, self.assertRaisesRegex(OSError, 'lost prompt'):
                proof.fresh_emulated_proof(Path(directory)/'bundle', x.fixture)
            self.assertEqual([m for m, s in x.mutations].count('session.prompt'), 1); self.assertEqual(len(x.processes), 1)
            record = self.record(x); self.assertTrue(record['unknownRequestOutcome']); self.assertIn('session.prompt', record['pendingRequest']['action'])
            self.assertTrue(record['settingsPreserved']); x.companion.finish.assert_called_once()

    def test_unknown_setup_outcome_cannot_invoke_idempotence_or_runtime_or_sdk(self):
        with tempfile.TemporaryDirectory() as directory:
            x = self.execution(directory, setup_lost=True)
            with x.stack, self.assertRaisesRegex(OSError, 'setup child outcome'):
                proof.fresh_emulated_proof(Path(directory)/'bundle', x.fixture)
            self.assertEqual(len(x.setup_calls), 1); self.assertEqual(x.processes, []); self.assertEqual(x.mutations, [])
            record = self.record(x); self.assertTrue(record['unknownRequestOutcome']); self.assertEqual(record['pendingRequest']['action'], 'setup.initial')
            x.companion.finish.assert_not_called()

    def test_settings_byte_change_refuses_even_if_yaml_values_remain_same(self):
        with tempfile.TemporaryDirectory() as directory:
            x = self.execution(directory, changed=True)
            with x.stack, self.assertRaisesRegex(ValueError, 'settings changed'):
                proof.fresh_emulated_proof(Path(directory)/'bundle', x.fixture)
            self.assertFalse(self.record(x)['settingsPreserved']); self.assertEqual(len(x.processes), 1)
            self.assertEqual([m for m, s in x.mutations].count('session.prompt'), 1)
            self.assertFalse((x.home/proof.FRESH_RUN_DIRECTORY/'report.json').exists())

    def test_installed_receipt_idempotence_must_preserve_all_five_bytes_before_sdk(self):
        with tempfile.TemporaryDirectory() as directory:
            x = self.execution(directory, repeat_changed=True)
            with x.stack, self.assertRaisesRegex(ValueError, 'settings changed'):
                proof.fresh_emulated_proof(Path(directory)/'bundle', x.fixture)
            self.assertEqual(len(x.setup_calls), 2); self.assertEqual(x.processes, []); self.assertEqual(x.mutations, [])
            self.assertFalse(self.record(x)['settingsPreserved']); x.companion.finish.assert_not_called()

    def test_restart_history_change_is_failure_without_any_prompt_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            x = self.execution(directory, history_changed=True)
            with x.stack, self.assertRaisesRegex(ValueError, 'restart changed history'):
                proof.fresh_emulated_proof(Path(directory)/'bundle', x.fixture)
            self.assertEqual([m for m, s in x.mutations].count('session.prompt'), 2); self.assertEqual(len(x.processes), 2)
            self.assertFalse(self.record(x)['historyPreservedVerified']); x.companion.finish.assert_called_once()

    def test_unknown_companion_commit_is_terminal_and_finally_never_repeats_it(self):
        with tempfile.TemporaryDirectory() as directory:
            x = self.execution(directory)
            def unknown():
                x.companion.attempted = True; x.companion.record = {'status': 'failed', 'pending': 'commit', 'unknownOutcome': True}
                raise OSError('lost companion commit')
            x.companion.finish.side_effect = unknown
            with x.stack, self.assertRaisesRegex(OSError, 'lost companion'):
                proof.fresh_emulated_proof(Path(directory)/'bundle', x.fixture)
            x.companion.finish.assert_called_once(); record = self.record(x)
            self.assertEqual(record['status'], 'failed'); self.assertTrue(record['companionCleanup']['unknownOutcome'])
            self.assertFalse((x.home/proof.FRESH_RUN_DIRECTORY/'report.json').exists())

    def test_provider_cleanup_failure_keeps_failed_journal_and_no_pass_report_after_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            x = self.execution(directory); x.server.server_close.side_effect = OSError('owned provider close failed')
            with x.stack, self.assertRaisesRegex(OSError, 'provider close failed'):
                proof.fresh_emulated_proof(Path(directory)/'bundle', x.fixture)
            self.assertEqual([m for m, s in x.mutations].count('session.prompt'), 2)
            self.assertEqual(self.record(x)['status'], 'failed'); self.assertTrue(self.record(x)['settingsPreserved'])
            x.companion.finish.assert_called_once(); x.server.server_close.assert_called_once()
            self.assertFalse((x.home/proof.FRESH_RUN_DIRECTORY/'report.json').exists())


if __name__ == '__main__': unittest.main()
