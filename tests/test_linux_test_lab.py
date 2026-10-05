# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

if not sys.platform.startswith('linux'):
    raise unittest.SkipTest('The persistent test-lab host tool is Linux-only.')

MODULE = Path(__file__).resolve().parents[1] / 'scripts/linux-test-lab.py'
SPEC = importlib.util.spec_from_file_location('linux_test_lab', MODULE)
lab = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lab)


class AdmissionTests(unittest.TestCase):
    def test_memory_floor_and_existing_guest(self):
        for memory, running in [(14 * lab.GIB, []), (40 * lab.GIB, ['augmentor-lab-other'])]:
            with self.assertRaises(ValueError):
                lab.resource_admission(6144, memory, 10 * lab.GIB, 100 * lab.GIB, running)
        lab.resource_admission(6144, 16 * lab.GIB, 10 * lab.GIB, 100 * lab.GIB, [])

    def test_disk_floor(self):
        for root, data in [(3 * lab.GIB, 100 * lab.GIB), (10 * lab.GIB, 19 * lab.GIB)]:
            with self.assertRaises(ValueError):
                lab.resource_admission(4096, 40 * lab.GIB, root, data, [])

    def test_unsafe_name(self):
        for name in ['../guest', '/root', 'name with spaces', 'UPPER']:
            with self.assertRaises(ValueError): lab.token(name)

    def test_operation_journal_keeps_prior_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            lab.operation_record(folder, 'shutdown', 'dispatch', {'exitCode': 1})
            lab.operation_record(folder, 'shutdown', 'dispatch', {'exitCode': 0})
            events = [json.loads(path.read_text()) for path in (folder / 'events').glob('*.json')]
            self.assertEqual(sorted(row['exitCode'] for row in events), [0, 1])
            self.assertEqual(json.loads((folder / 'last-shutdown-dispatch.json').read_text())['exitCode'], 0)

    def test_interrupted_transition_refuses_actions(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner = lab.Lab(temporary)
            folder = Path(temporary) / 'guest'; folder.mkdir()
            (folder / 'pending-generation.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'interrupted'):
                owner.entry('guest')

    def test_saved_memory_refuses_disk_switch(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner = lab.Lab(temporary)
            result = subprocess.CompletedProcess([], 0, '<domain/>', '')
            with patch.object(lab, 'virsh', return_value=result):
                with self.assertRaisesRegex(ValueError, 'Saved guest memory'):
                    owner.no_saved_memory({'name': 'guest'})

    def test_shutdown_timeout_never_forces(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner = lab.Lab(temporary)
            result = subprocess.CompletedProcess([], 0, 'running\n', '')
            with patch.object(owner, 'entry', return_value=(Path(temporary), {'name': 'guest'})), \
                 patch.object(owner, 'validate_domain'), patch.object(lab, 'virsh', return_value=result) as calls:
                with self.assertRaisesRegex(ValueError, 'no forced stop'):
                    owner.shutdown('guest', 0)
            self.assertEqual(calls.call_args_list[-1].args, ('shutdown', 'augmentor-lab-guest', '--mode', 'acpi'))

    def test_ssh_shutdown_disconnect_observes_stop_without_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner = lab.Lab(temporary)
            spec = {'name': 'guest', 'shutdownMethod': 'ssh', 'guestUser': 'owned-fixture',
                    'sshHostKeyAlias': '[127.0.0.1]:22491', 'sshPort': 22601,
                    'sshKey': '/private/key', 'knownHosts': '/private/known', 'assetSha256': {}}
            states = [subprocess.CompletedProcess([], 0, state, '') for state in ['running', 'shut off']]
            disconnected = subprocess.CompletedProcess([], 255, '', 'Connection closed')
            with patch.object(owner, 'entry', return_value=(Path(temporary), spec)), \
                 patch.object(owner, 'validate_domain'), patch.object(lab, 'virsh', side_effect=states) as native, \
                 patch.object(lab, 'run', return_value=disconnected) as remote:
                result = owner.shutdown('guest', 2)
            self.assertEqual(result['state'], 'shut off'); self.assertFalse(result['forced'])
            remote.assert_called_once()
            self.assertEqual(remote.call_args.args[0][-4:], ['sudo', '-n', 'systemctl', 'poweroff'])
            self.assertTrue(all(call.args[0] != 'shutdown' for call in native.call_args_list))


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.spec = {'name': 'guest', 'uuid': 'ae0c6128-f604-4a81-b332-c3637290e209',
                     'memoryMiB': 4096, 'cpus': 2, 'cpuModel': 'Nehalem', 'sshPort': 22604}
        self.xml = lab.domain_xml(self.spec, Path('/private/run'))

    def test_disk_redirect_changes_contract(self):
        redirected = self.xml.replace('/private/run/disk.qcow2', '/private/original.qcow2')
        self.assertNotEqual(lab.domain_contract(self.xml), lab.domain_contract(redirected))

    def test_loopback_forward_cannot_become_public(self):
        public = self.xml.replace('address="127.0.0.1"', 'address="0.0.0.0"')
        self.assertNotEqual(lab.domain_contract(self.xml), lab.domain_contract(public))

    def test_host_mount_refused(self):
        mount = self.xml.replace('<devices>', '<devices><filesystem type="mount"/>')
        with self.assertRaises(ValueError): lab.domain_contract(mount)

    def test_libvirt_whitespace_and_assigned_vnc_port(self):
        generated = self.xml.replace('autoport="yes"', 'port="5901" autoport="yes"').replace('\n  ', '\n    ')
        self.assertEqual(lab.domain_contract(self.xml), lab.domain_contract(generated))

    def test_existing_domain_redirect_refuses_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner = lab.Lab(temporary)
            spec = {**self.spec, 'currentGeneration': '/private/run'}
            altered = self.xml.replace('/private/run/disk.qcow2', '/private/original.qcow2')
            result = subprocess.CompletedProcess([], 0, altered, '')
            with patch.object(lab, 'virsh', return_value=result):
                with self.assertRaisesRegex(ValueError, 'definition differs'):
                    owner.validate_domain(spec)

    def test_checkpoint_refuses_changed_generation_before_conversion(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner = lab.Lab(temporary)
            spec = {**self.spec, 'currentGeneration': '/private/run'}
            with patch.object(owner, 'entry', return_value=(Path(temporary), spec)), \
                 patch.object(owner, 'inactive'), patch.object(owner, 'validate_domain'), \
                 patch.object(owner, 'no_saved_memory'), \
                 patch.object(owner, 'verify_generation', side_effect=ValueError('immutable checkpoint hash differs')), \
                 patch.object(owner, 'checkpoint_disk') as converted:
                with self.assertRaisesRegex(ValueError, 'hash differs'):
                    owner.checkpoint('guest', 'new')
                converted.assert_not_called()

    def test_start_rechecks_memory_after_disk_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner = lab.Lab(temporary)
            spec = {**self.spec, 'currentGeneration': '/private/run', 'assetSha256': {}}
            result = subprocess.CompletedProcess([], 0, '', '')
            with patch.object(owner, 'entry', return_value=(Path(temporary), spec)), \
                 patch.object(owner, 'inactive'), patch.object(owner, 'validate_domain'), \
                 patch.object(owner, 'no_saved_memory'), patch.object(owner, 'check', return_value={'passed': True}), \
                 patch.object(lab, 'available_memory', side_effect=[40 * lab.GIB, 5 * lab.GIB]), \
                 patch.object(lab.shutil, 'disk_usage', return_value=shutil._ntuple_diskusage(100 * lab.GIB, 0, 100 * lab.GIB)), \
                 patch.object(lab, 'virsh', return_value=result) as commands:
                with self.assertRaisesRegex(ValueError, 'Insufficient available RAM'):
                    owner.start('guest')
                self.assertTrue(all(call.args[0] != 'start' for call in commands.call_args_list))

    def test_reconcile_recovers_exact_old_definition(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner = lab.Lab(temporary); folder = Path(temporary) / 'guest'; folder.mkdir()
            committed = {**self.spec, 'currentGeneration': '/private/old'}
            prepared = {**self.spec, 'currentGeneration': '/private/new', 'checkpoint': 'new'}
            lab.write_json(folder / 'machine.json', committed)
            lab.write_json(folder / 'pending-generation.json', prepared)
            def native(*args, **kwargs):
                text = 'augmentor-lab-guest\n' if args[0] == 'list' else lab.domain_xml(committed, Path('/private/old'))
                return subprocess.CompletedProcess([], 0, text, '')
            with patch.object(lab, 'virsh', side_effect=native) as calls, \
                 patch.object(owner, 'inactive'), patch.object(owner, 'no_saved_memory'), \
                 patch.object(owner, 'validate_domain'), patch.object(owner, 'verify_generation', return_value={}):
                self.assertTrue(owner.reconcile('guest')['reconciled'])
                self.assertTrue(any(call.args[0] == 'define' for call in calls.call_args_list))
                self.assertFalse((folder / 'pending-generation.json').exists())
                self.assertEqual(json.loads((folder / 'machine.json').read_text())['currentGeneration'], '/private/new')


@unittest.skipUnless(shutil.which('qemu-img') and shutil.which('qemu-io'), 'QEMU image tools required')
class ActualDiskTests(unittest.TestCase):
    def test_flatten_preserves_chain_and_guest_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = root / 'source.qcow2'; overlay = root / 'working.qcow2'
            lab.run(['qemu-img', 'create', '-f', 'qcow2', base, '8M'])
            lab.run(['qemu-io', '-f', 'qcow2', '-c', 'write -P 0x37 0 4096', base])
            lab.run(['qemu-img', 'create', '-f', 'qcow2', '-F', 'qcow2', '-b', base, overlay])
            lab.run(['qemu-io', '-f', 'qcow2', '-c', 'write -P 0x65 4096 4096', overlay])
            before = {p.name: lab.sha(p) for p in [base, overlay]}
            owner = lab.Lab(root / 'lab'); output = owner.root / 'checkpoint'; output.mkdir()
            with patch.object(lab.shutil, 'disk_usage', return_value=shutil._ntuple_diskusage(100 * lab.GIB, 0, 100 * lab.GIB)):
                owner.checkpoint_disk(overlay, output)
            self.assertEqual(before, {p.name: lab.sha(p) for p in [base, overlay]})
            self.assertEqual(lab.image_chain(output / 'base.qcow2'), [output / 'base.qcow2'])
            lab.run(['qemu-io', '-r', '-f', 'qcow2', '-c', 'read -P 0x37 0 4096', output / 'base.qcow2'])
            lab.run(['qemu-io', '-r', '-f', 'qcow2', '-c', 'read -P 0x65 4096 4096', output / 'base.qcow2'])
            self.assertTrue(json.loads((output / 'checkpoint.json').read_text())['logicalDiskComparePassed'])

    def test_failed_disk_check_never_converts_or_repairs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root / 'source.qcow2'; source.write_bytes(b'corrupt')
            owner = lab.Lab(root / 'lab'); output = owner.root / 'checkpoint'; output.mkdir()
            with patch.object(lab, 'image_chain', return_value=[source]), \
                 patch.object(lab, 'check_image', return_value={'exitCode': 2}) as checked, \
                 patch.object(lab, 'run') as commands:
                with self.assertRaisesRegex(ValueError, 'source disk check failed'):
                    owner.checkpoint_disk(source, output)
                commands.assert_not_called(); checked.assert_called_once_with(source)
            self.assertEqual(source.read_bytes(), b'corrupt')


if __name__ == '__main__':
    unittest.main()
