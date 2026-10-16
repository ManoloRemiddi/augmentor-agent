# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authored Docker transport/engine source; real hashes, patch, files and HTTP checks.

This does not claim a live Docker or actual Hindsight installation.
"""
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_hindsight_setup as fixtures
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services'))
from memory import engine_install, hindsight_backport


def tar_bytes(name, value):
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode='w') as archive:
        row = tarfile.TarInfo(name); row.size = len(value); archive.addfile(row, io.BytesIO(value))
    return out.getvalue()


class DockerPeer:
    def __init__(self, setup):
        self.setup, self.containers, self.commands, self.serial = setup, {}, [], 0
        self.real_run = setup.subprocess.run
        self.source = b'VALUE = 1\n'; self.backup = tar_bytes('.pg0/authored-data', b'authored-bank-and-document-identity')
        self.fail_backup = False; self.inspect_error = False; self.source_owner_change = False
        self.lose_creation_acknowledgement = False

    def __call__(self, command, **options):
        if command[0] != 'docker': return self.real_run(command, **options)
        self.commands.append(command[:]); args = command[1:]
        def result(value='', code=0, error=''):
            if not options.get('text'):
                value = value.encode() if isinstance(value, str) else value
                error = error.encode() if isinstance(error, str) else error
            return SimpleNamespace(returncode=code, stdout=value, stderr=error)
        def find(name):
            return next((c for n, c in self.containers.items() if n == name or c['Id'] == name), None)
        if args[0] == 'inspect':
            if self.inspect_error: return result(code=1, error='Cannot connect to the authored Docker peer')
            value = find(args[1]); return result(json.dumps([value])) if value else result(code=1, error='Error: No such object: ' + args[1])
        if args[:2] == ['image', 'inspect']:
            return result(json.dumps([{'Id': 'sha256:' + self.setup.IMAGE.split('sha256:')[1]}]))
        if args[0] in ('create', 'run'):
            name = args[args.index('--name') + 1]; self.serial += 1
            identity = 'authored-instance-' + str(self.serial); labels, env, mounts = {}, [], []
            for i, arg in enumerate(args):
                if arg == '--label': key, value = args[i + 1].split('=', 1); labels[key] = value
                if arg == '-e':
                    value = args[i + 1]; env.append(value if '=' in value else value + '=' + options['env'][value])
                if arg == '-v':
                    source, destination, *mode = args[i + 1].split(':')
                    volume = not Path(source).is_absolute()
                    mounts.append({'Type': 'volume' if volume else 'bind', 'Name' if volume else 'Source': source, 'Destination': destination, 'RW': mode != ['ro']})
            restart = args[args.index('--restart') + 1] if '--restart' in args else 'no'
            self.containers[name] = {'Id': identity, 'Config': {'Image': self.setup.IMAGE, 'Env': env, 'Labels': labels},
                                     'State': {'Running': args[0] == 'run'}, 'Mounts': mounts, 'HostConfig': {'RestartPolicy': {'Name': restart}}}
            return result(identity, code=1 if args[0] == 'run' and self.lose_creation_acknowledgement else 0)
        if args[0] == 'cp':
            identity, source = args[1].split(':', 1); value = find(identity)
            if source == '/home/hindsight/.pg0':
                options['stdout'].write(self.backup)
                return result(code=1 if self.fail_backup else 0)
            if self.source_owner_change: value['Config']['Labels']['org.augmentor.memory.source'] = 'changed-owner'
            return result(tar_bytes('memory_engine.py', self.source))
        if args[0] == 'rm':
            for n, c in list(self.containers.items()):
                if c['Id'] == args[-1]: del self.containers[n]
            return result()
        if args[0] in ('start', 'stop', 'update'):
            value = find(args[-1]); self.assert_known(value)
            if args[0] != 'update': value['State']['Running'] = args[0] == 'start'
            else: value['HostConfig']['RestartPolicy']['Name'] = 'no'
            return result()
        if args[0] == 'rename':
            for n, c in list(self.containers.items()):
                if c['Id'] == args[1]: del self.containers[n]; self.containers[args[2]] = c; return result()
        raise AssertionError('Unexpected authored Docker command: ' + repr(command))

    def assert_known(self, value):
        if value is None: raise AssertionError('A mutation did not target a known exact instance')


class InstallationTests(unittest.TestCase):
    def setUp(self):
        fixtures.HindsightSetupTests.setUp(self)
        self.peer = DockerPeer(self.setup)
        self.vendor = self.data / 'authored-public-vendor'; self.vendor.mkdir()
        source, changed = b'VALUE = 1\n', b'VALUE = 2\n'
        patch_bytes = b'--- a/memory_engine.py\n+++ b/memory_engine.py\n@@ -1 +1 @@\n-VALUE = 1\n+VALUE = 2\n'
        license_bytes = b'Independently authored test source, MIT fixture.\n'
        for name, value in [('LICENSE', license_bytes), ('refresh-budget.patch', patch_bytes)]: (self.vendor / name).write_bytes(value)
        digest = lambda v: hashlib.sha256(v).hexdigest()
        self.manifest = {'baseImage': self.setup.IMAGE, 'baseSha256': digest(source), 'resultSha256': digest(changed),
                         'patchSha256': digest(patch_bytes), 'licenseSha256': digest(license_bytes), 'containerPath': '/app/api/hindsight_api/engine/memory_engine.py', 'upstreamFixRef': 'authored-test-source'}
        (self.vendor / 'SOURCE.json').write_text(json.dumps(self.manifest))

    def run_setup(self, options=()):
        with patch.dict(os.environ, {'AUGMENTOR_SHARED_DATA': str(self.data)}), patch('sys.argv', [*self.argv, *options]), \
                patch.object(self.setup.subprocess, 'run', side_effect=self.peer), patch.object(hindsight_backport, 'VENDOR', self.vendor), redirect_stdout(io.StringIO()):
            self.setup.main()
        return json.loads((self.data / 'hindsight.json').read_text())

    def fresh(self):
        # Three independent ports, no daemon autostart, offline authored cache.
        cache = self.data / 'public-cache'; cache.mkdir()
        for name in engine_install.CACHE_MODELS: (cache / name).mkdir()
        (cache / engine_install.CACHE_MODELS[0] / 'weights').write_bytes(b'authored-public-model')
        port = next(p for p in (18442, 18444, 18446) if p not in (self.port, self.gateway))
        return self.run_setup(['--refresh-budget-backport', '--llama-cpp-thinking', 'off', '--restart', 'no', '--postgres-port', str(port), '--public-model-cache', str(cache)])

    def test_fresh_backport_install_pins_source_mounts_and_privacy_without_model_work(self):
        saved = self.fresh(); current = self.peer.containers['synthetic-controlled']
        self.assertTrue(saved['refreshBudgetBackport']); self.assertEqual(saved['engineSourceSha256'], self.manifest['resultSha256'])
        self.assertEqual(saved['llamaCppThinking'], 'off'); self.assertEqual(saved['restartPolicy'], 'no')
        self.assertEqual(current['Id'], saved['containerId']); self.assertEqual(current['Config']['Labels'][engine_install.OWNER_LABEL], saved['installationId'])
        env = dict(row.split('=', 1) for row in current['Config']['Env'])
        self.assertEqual(env['HINDSIGHT_API_DATABASE_URL'], 'pg0://hindsight:' + str(saved['postgresPort']))
        for key in ('HF_HUB_DISABLE_TELEMETRY', 'DO_NOT_TRACK', 'HF_HUB_OFFLINE'): self.assertEqual(env[key], '1')
        self.assertEqual(env['OTEL_SDK_DISABLED'], 'true'); self.assertEqual(env['HINDSIGHT_API_WORKER_ENABLED'], 'false')
        mounted = next(m for m in current['Mounts'] if m['Destination'] == self.manifest['containerPath'])
        self.assertFalse(mounted['RW']); self.assertEqual(Path(mounted['Source']).read_bytes(), b'VALUE = 2\n')
        self.assertEqual((Path(mounted['Source']).parents[1] / 'LICENSE').read_bytes(), (self.vendor / 'LICENSE').read_bytes())
        self.assertEqual((self.data / 'hindsight.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual(set(self.peer.containers), {'synthetic-controlled'}, 'owned never-started source container joins cleanup')
        self.assertEqual(self.requests, ['/openapi.json', '/health', '/ext/augmentor/policy'])

    def test_omission_reuses_source_cache_ports_policy_and_exact_stopped_instance(self):
        saved = self.fresh(); before = (self.data / 'hindsight.json').read_bytes(); self.peer.commands.clear()
        self.run_setup(); self.assertEqual((self.data / 'hindsight.json').read_bytes(), before)
        self.assertTrue(all(c[1] == 'inspect' for c in self.peer.commands))
        self.peer.commands.clear(); self.peer.containers['synthetic-controlled']['State']['Running'] = False
        again = self.run_setup(); self.assertEqual(again, saved)
        starts = [c for c in self.peer.commands if c[1] == 'start']; self.assertEqual(starts, [['docker', 'start', saved['containerId']]])
        self.assertFalse(any(c[1] in ('run', 'create', 'pull', 'rename') for c in self.peer.commands))

    def test_changed_source_choice_refuses_running_engine_then_backs_up_stopped_identity(self):
        saved = self.fresh(); before = (self.data / 'hindsight.json').read_bytes(); self.peer.commands.clear()
        with self.assertRaisesRegex(SystemExit, 'Existing engine differs'): self.run_setup(['--no-refresh-budget-backport', '--replace-stopped'])
        self.assertEqual((self.data / 'hindsight.json').read_bytes(), before); self.assertTrue(all(c[1] == 'inspect' for c in self.peer.commands))
        self.peer.containers['synthetic-controlled']['State']['Running'] = False
        changed = self.run_setup(['--no-refresh-budget-backport', '--replace-stopped'])
        self.assertFalse(changed['refreshBudgetBackport']); self.assertNotEqual(changed['containerId'], saved['containerId']); self.assertEqual(changed['installationId'], saved['installationId'])
        receipt = json.loads((self.data / 'hindsight-installation.json').read_text())
        self.assertEqual(receipt['backupContainerId'], saved['containerId']); self.assertEqual(Path(receipt['backup']).read_bytes(), self.peer.backup)
        private_backup = json.loads(Path(receipt['backup']).with_suffix('.json').read_text())
        self.assertEqual(private_backup['configuration'], json.loads(before), 'rollback retains the previous configuration, including credentials and source choice')
        self.assertEqual(Path(receipt['backup']).with_suffix('.json').stat().st_mode & 0o777, 0o600)
        old = self.peer.containers[receipt['backupContainer']]; self.assertFalse(old['State']['Running']); self.assertEqual(old['HostConfig']['RestartPolicy']['Name'], 'no')
        volume = lambda c: next(m['Name'] for m in c['Mounts'] if m['Type'] == 'volume')
        self.assertEqual(volume(old), volume(self.peer.containers['synthetic-controlled']))

    def test_failed_or_invalid_backup_preserves_the_stopped_instance_name_and_configuration(self):
        self.fresh(); before = (self.data / 'hindsight.json').read_bytes(); current = self.peer.containers['synthetic-controlled']; current['State']['Running'] = False
        for failure, backup in [(True, self.peer.backup), (False, b'not-an-archive')]:
            self.peer.fail_backup = failure; self.peer.backup = backup; self.peer.commands.clear()
            with self.assertRaises((ValueError, tarfile.ReadError)): self.run_setup(['--no-refresh-budget-backport', '--replace-stopped'])
            self.assertIs(self.peer.containers['synthetic-controlled'], current); self.assertEqual((self.data / 'hindsight.json').read_bytes(), before)
            self.assertEqual(sum(c[1] == 'cp' for c in self.peer.commands), 1)
            self.assertFalse(any(c[1] in ('rename', 'update', 'run', 'start') for c in self.peer.commands))

    def test_unknown_daemon_error_or_changed_container_identity_never_grants_mutation(self):
        self.peer.inspect_error = True
        with self.assertRaisesRegex(ValueError, 'inspection'): self.run_setup()
        self.assertTrue(all(c[1] == 'inspect' for c in self.peer.commands)); self.peer.inspect_error = False
        self.fresh(); before = (self.data / 'hindsight.json').read_bytes(); self.peer.containers['synthetic-controlled']['Id'] = 'foreign-replacement'; self.peer.commands.clear()
        with self.assertRaisesRegex(ValueError, 'identity changed'): self.run_setup(['--replace-stopped'])
        self.assertEqual((self.data / 'hindsight.json').read_bytes(), before); self.assertTrue(all(c[1] == 'inspect' for c in self.peer.commands))

    def test_wrong_public_source_joins_its_owned_container_without_installing_an_engine(self):
        self.peer.source = b'UNKNOWN = True\n'
        with self.assertRaisesRegex(ValueError, 'pinned base'): self.fresh()
        self.assertEqual(self.peer.containers, {}); self.assertFalse((self.data / 'hindsight.json').exists())
        self.assertFalse(any(c[1] == 'run' for c in self.peer.commands))
        owners = list((self.data / 'memory-engine').rglob('source-owner.json')); self.assertEqual(len(owners), 1)
        self.assertTrue(json.loads(owners[0].read_text())['terminal'])

    def test_lost_creation_acknowledgement_recovers_the_recorded_instance_without_another_creation(self):
        self.peer.lose_creation_acknowledgement = True
        with self.assertRaisesRegex(ValueError, 'nothing was replayed'): self.fresh()
        self.assertFalse((self.data / 'hindsight.json').exists()); current = self.peer.containers['synthetic-controlled']; self.peer.commands.clear()
        with self.assertRaisesRegex(ValueError, 'unconfirmed'): self.run_setup()
        self.assertEqual(self.peer.commands, [])
        saved = self.run_setup(['--recover-pending'])
        self.assertEqual(saved['containerId'], current['Id']); self.assertEqual(saved['llamaCppThinking'], 'off'); self.assertTrue(saved['refreshBudgetBackport'])
        self.assertTrue(all(c[1] == 'inspect' for c in self.peer.commands))
        self.assertEqual(len(self.peer.containers), 1)

    def test_changed_cached_overlay_refuses_without_repair_or_docker_start(self):
        self.fresh(); c = self.peer.containers['synthetic-controlled']; source = Path(next(m['Source'] for m in c['Mounts'] if m['Destination'] == self.manifest['containerPath']))
        source.chmod(0o644); source.write_bytes(b'CHANGED = True\n'); self.peer.commands.clear()
        with self.assertRaisesRegex(ValueError, 'artifact changed'): self.run_setup()
        self.assertEqual(source.read_bytes(), b'CHANGED = True\n'); self.assertTrue(all(c[1] == 'inspect' for c in self.peer.commands))
