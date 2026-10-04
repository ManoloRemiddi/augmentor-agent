# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services'))
from platform_adapters import recipient_runtime_markers as markers

spec = importlib.util.spec_from_file_location('recipient_preference_tests', ROOT / 'services/voice/preferences.py')
preferences = importlib.util.module_from_spec(spec); spec.loader.exec_module(preferences)


@unittest.skipUnless(sys.platform == 'linux' and os.geteuid() != 0, 'Ordinary Linux diagnostics')
class MarkerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name); self.directory.chmod(0o700)
        self.scope = self.directory / 'scope.json'
        self.parent = markers.process_identity(os.getppid())
        self.token = 'a' * 64
        self.value = {'format': 'augmentor-recipient-preferences-proof/1', 'token': self.token,
                      'appRoot': str(ROOT.resolve()), 'parentPid': self.parent['pid'],
                      'parentStartTicks': self.parent['startTicks']}
        self.scope.write_text(json.dumps(self.value)); self.scope.chmod(0o600)
        self.env = {markers.DIRECTORY: str(self.directory), markers.TOKEN: self.token}
        # No test may contact the real speech service or read actual preferences.
        self.addCleanup(patch.stopall)
        self.rpc = patch.object(preferences, 'voice_request', return_value={'synthetic': True}).start()
        self.pref = patch.object(preferences, 'Preferences', return_value=SimpleNamespace(
            values={'voice_mode': 'manual', 'voice_pause_ms': 800, 'resonant_voice': False}, save=lambda:None)).start()

    def test_disabled_hook_does_not_collect_or_write_and_keeps_normal_result(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(markers, 'collect') as collect:
            result = preferences.request({'action':'get'})
        collect.assert_not_called(); self.rpc.assert_called_once_with('preferences')
        self.assertEqual(result, {'synthetic':True, 'mode':'manual', 'pauseMs':800, 'enabled':False})
        self.assertFalse((self.directory / markers.OUTPUT).exists())

    def test_opted_in_actual_preference_function_publishes_only_diagnostics(self):
        evidence = {'format':'synthetic-markers', 'pid':os.getpid(), 'markers':{'core':None}}
        with patch.dict(os.environ, self.env), patch.object(markers, 'collect', return_value=evidence) as collect:
            result = preferences.request({'action':'get'})
        collect.assert_called_once_with(); self.rpc.assert_called_once_with('preferences')
        output = self.directory / markers.OUTPUT
        self.assertEqual(json.loads(output.read_text()), evidence)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('synthetic', json.loads(output.read_text())); self.assertTrue(result['synthetic'])

    def test_normal_save_keeps_existing_rpc_and_saved_configuration_without_diagnostics(self):
        settings = {'mode':'hands-free', 'pauseMs':900, 'enabled':True,
                    'voiceId':'synthetic', 'speed':1, 'volume':0.5}
        self.pref.return_value.save = save = unittest.mock.Mock()
        with patch.dict(os.environ, {}, clear=True), patch.object(markers,'collect') as collect:
            result = preferences.request({'action':'save', 'settings':settings})
        self.rpc.assert_called_once_with('preferences', {'values':{'voiceId':'synthetic','speed':1,'volume':0.5}})
        save.assert_called_once_with(); collect.assert_not_called()
        self.assertEqual((result['mode'], result['pauseMs'], result['enabled']), ('hands-free',900,True))

    def test_save_partial_optin_and_malformed_token_refuse_before_preferences_rpc(self):
        for env, action in ((self.env, 'save'), ({markers.TOKEN:self.token}, 'get'),
                            ({markers.DIRECTORY:str(self.directory)}, 'get'),
                            ({**self.env, markers.TOKEN:'foreign'}, 'get')):
            with self.subTest(env=env, action=action), patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ValueError): preferences.request({'action':action})
        self.rpc.assert_not_called(); self.pref.assert_not_called()

    def test_opted_in_get_requires_exact_fields_before_rpc(self):
        for value in ({}, {'action':'get', 'settings':{'private':'omit'}}):
            with patch.dict(os.environ, self.env), self.assertRaisesRegex(ValueError, 'explicit get'):
                preferences.request(value)
        self.rpc.assert_not_called(); self.pref.assert_not_called()

    def test_source_token_parent_and_extra_scope_mismatches_refuse_before_rpc(self):
        for key, value in (('appRoot', '/foreign'), ('token', 'b'*64),
                           ('parentPid', self.parent['pid'] + 1),
                           ('parentStartTicks', self.parent['startTicks'] + 1), ('extra', True)):
            self.scope.write_text(json.dumps({**self.value, key:value}))
            with self.subTest(key=key), patch.dict(os.environ, self.env):
                with self.assertRaisesRegex(ValueError, 'scope differs'): preferences.request({'action':'get'})
        self.rpc.assert_not_called()

    def test_existing_regular_and_symlink_output_refuse_before_rpc_and_are_preserved(self):
        output = self.directory / markers.OUTPUT
        for symlink in (False, True):
            if symlink: output.symlink_to(self.scope)
            else: output.write_bytes(b'preserved')
            with patch.dict(os.environ, self.env), self.assertRaisesRegex(ValueError, 'already exists'):
                preferences.request({'action':'get'})
            self.assertEqual(output.read_bytes(), self.scope.read_bytes() if symlink else b'preserved')
            output.unlink()
        self.rpc.assert_not_called()

    def test_unsafe_directory_scope_symlink_hardlink_and_duplicate_keys_refuse(self):
        with patch.dict(os.environ, self.env):
            self.directory.chmod(0o755)
            with self.assertRaisesRegex(ValueError, 'private'): preferences.request({'action':'get'})
            self.directory.chmod(0o700)
            self.scope.chmod(0o644)
            with self.assertRaisesRegex(ValueError, 'file identity'): preferences.request({'action':'get'})
            self.scope.chmod(0o600)
            other = self.directory / 'other'; self.scope.rename(other); self.scope.symlink_to(other)
            with self.assertRaises(OSError): preferences.request({'action':'get'})
            self.scope.unlink(); os.link(other, self.scope)
            with self.assertRaisesRegex(ValueError, 'file identity'): preferences.request({'action':'get'})
            self.scope.unlink(); other.rename(self.scope)
            self.scope.write_text('{"token":"a","token":"b"}')
            with self.assertRaisesRegex(ValueError, 'Duplicate'): preferences.request({'action':'get'})
        self.rpc.assert_not_called()

    def test_symlink_directory_alias_refuses_before_rpc(self):
        alias = self.directory / 'alias'; alias.symlink_to(self.directory, target_is_directory=True)
        with patch.dict(os.environ, {**self.env, markers.DIRECTORY:str(alias)}), self.assertRaisesRegex(ValueError,'unlinked'):
            preferences.request({'action':'get'})
        self.rpc.assert_not_called()

    def test_failed_normal_read_emits_no_diagnostics_and_never_retries_rpc(self):
        self.rpc.side_effect = RuntimeError('synthetic failed read')
        with patch.dict(os.environ, self.env), patch.object(markers, 'collect') as collect:
            with self.assertRaisesRegex(RuntimeError, 'failed read'): preferences.request({'action':'get'})
        self.rpc.assert_called_once(); collect.assert_not_called()
        self.assertFalse((self.directory / markers.OUTPUT).exists())

    def test_parent_or_scope_substitution_during_collection_refuses_publication(self):
        def replaced():
            new = self.directory / 'new'; new.write_bytes(self.scope.read_bytes()); new.chmod(0o600)
            new.replace(self.scope)
            return {'markers': {}}
        with patch.object(markers, 'collect', side_effect=replaced):
            with markers.preference_proof(ROOT, 'get', self.env) as emit:
                with self.assertRaisesRegex(ValueError, 'changed'): emit()
        self.assertFalse((self.directory / markers.OUTPUT).exists())
        with markers.preference_proof(ROOT, 'get', self.env) as emit:
            with patch.object(markers, 'collect', return_value={}), patch.object(markers, 'process_identity', return_value={**self.parent,'startTicks':0}):
                with self.assertRaisesRegex(ValueError, 'changed'): emit()

    def test_durable_failure_retains_output_and_emit_never_replays(self):
        with markers.preference_proof(ROOT, 'get', self.env) as emit, patch.object(markers,'collect',return_value={}) as collect:
            with patch.object(markers.os, 'fsync', side_effect=OSError('synthetic flush failed')):
                with self.assertRaisesRegex(OSError,'flush failed'): emit()
            self.assertTrue((self.directory / markers.OUTPUT).exists())
            with self.assertRaisesRegex(ValueError, 'no replay'): emit()
            collect.assert_called_once()

    def test_closed_scope_callback_refuses_before_collection_and_closes_descriptor(self):
        before = set(os.listdir('/proc/self/fd'))
        with markers.preference_proof(ROOT, 'get', self.env) as emit:
            self.assertEqual(len(set(os.listdir('/proc/self/fd'))), len(before) + 1)
        self.assertEqual(set(os.listdir('/proc/self/fd')), before)
        with patch.object(markers,'collect') as collect, self.assertRaisesRegex(ValueError,'closed'):
            emit()
        collect.assert_not_called()

    def test_actual_local_qt_process_markers_hash_loaded_native_bytes(self):
        with patch.dict(os.environ, {}, clear=True): report = markers.collect()
        self.assertEqual(report['pid'], os.getpid()); self.assertEqual(report['uid'], os.getuid())
        self.assertEqual(report['startTicks'], markers.process_identity(os.getpid())['startTicks'])
        self.assertEqual(report['markers'], {'core':None, 'pyside':None, 'shiboken':None})
        self.assertFalse(report['compiledSourceMappingComplete']); self.assertFalse(report['completeNativeScopeObserved'])
        self.assertTrue(any('libQt6Core.so' in row['path'] for row in report['loadedNativeFiles']))
        for row in report['loadedNativeFiles']:
            path = Path(row['path']); self.assertEqual(path.stat().st_ino, row['inode'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row['sha256'])

    def test_changed_map_file_inode_and_unknown_marker_refuse(self):
        from PySide6 import QtCore
        real = markers.native_maps()
        with patch.object(markers, 'native_maps', side_effect=[real, {}]):
            with self.assertRaisesRegex(ValueError, 'changed'): markers.collect()
        wrong = {name:{**row,'inode':row['inode'] + 1} for name,row in real.items()}
        with patch.object(markers, 'native_maps', return_value=wrong):
            with self.assertRaisesRegex(ValueError, 'loaded map'): markers.collect()
        with patch.object(QtCore, '__augmentor_recipient_pyside__', 'unknown-private-value', create=True):
            with self.assertRaisesRegex(ValueError, 'Unrecognized') as error: markers.collect()
            self.assertNotIn('unknown-private-value', str(error.exception))

    def test_known_three_markers_are_observed_from_actual_modules(self):
        from PySide6 import QtCore
        from shiboken6 import Shiboken
        with patch.object(QtCore.QLibraryInfo, 'build', return_value='Qt fixture ' + markers.MARKERS['core']),\
             patch.object(QtCore, '__augmentor_recipient_pyside__', markers.MARKERS['pyside'], create=True),\
             patch.object(Shiboken, '__augmentor_recipient_shiboken__', markers.MARKERS['shiboken'], create=True):
            report = markers.collect()
        self.assertEqual(report['markers'], markers.MARKERS)
        self.assertNotIn('Qt fixture', json.dumps(report))

    def test_maps_parser_rejects_deleted_conflicting_and_oversize_records(self):
        def run(raw):
            with patch('builtins.open', return_value=io.BytesIO(raw)): return markers.native_maps()
        for raw in (b'100-200 r-xp 0 00:01 12 /prefix/libQt6Core.so (deleted)\n',
                    b'100-200 r-xp 0 00:01 12 /prefix/libQt6Core.so\n200-300 r-xp 0 00:01 13 /prefix/libQt6Core.so\n',
                    b'x'*(2*1024*1024 + 1)):
            with self.subTest(size=len(raw)), self.assertRaises(ValueError): run(raw)
        parsed = run(b'100-200 r-xp 0 00:01 12 /private directory/libQt6Core.so\n')
        self.assertEqual(parsed, {'/private directory/libQt6Core.so':{'device':1,'inode':12}})

    def test_regular_reader_refuses_fifo_and_changed_bytes_without_blocking(self):
        fifo = self.directory / 'fifo'; os.mkfifo(fifo, 0o600)
        with self.assertRaisesRegex(ValueError, 'file identity'): markers.read_regular(fifo, 100)
        original = os.read
        def changed(fd, amount):
            raw = original(fd, amount)
            if raw: self.scope.write_bytes(b'changed')
            return raw
        with patch.object(markers.os, 'read', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed'): markers.read_regular(self.scope, 8192)

    def test_output_creation_race_and_directory_permission_change_are_terminal(self):
        output = self.directory / markers.OUTPUT
        def raced():
            output.write_bytes(b'preserve race')
            return {}
        with markers.preference_proof(ROOT, 'get', self.env) as emit, patch.object(markers,'collect',side_effect=raced):
            with self.assertRaises(FileExistsError): emit()
            with self.assertRaisesRegex(ValueError,'no replay'): emit()
        self.assertEqual(output.read_bytes(), b'preserve race'); output.unlink()
        def permissions():
            self.directory.chmod(0o755)
            return {}
        with markers.preference_proof(ROOT, 'get', self.env) as emit, patch.object(markers,'collect',side_effect=permissions):
            with self.assertRaisesRegex(ValueError,'changed'): emit()
        self.assertFalse(output.exists())


if __name__ == '__main__': unittest.main()
