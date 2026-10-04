# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Source-only tests; no daemons, extraction, builds or application execution."""
import unittest
import tempfile
import stat
import struct
from unittest import mock
from types import SimpleNamespace
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('marked_build', ROOT / 'release/probe-recipient-core-bindings-build.py')
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)

def patch(name='source.cpp', old='before', new='after'):
    return f'--- a/{name}\n+++ b/{name}\n@@ -1,1 +1,1 @@\n-{old}\n+{new}\n'.encode()

def source_fixture(tmp_path, monkeypatch):
    inputs = tmp_path / 'inputs'
    inputs.mkdir()
    root = tmp_path / 'build'
    root.mkdir()
    sources = root / 'sources'
    sources.mkdir()
    rows = []
    patches = {}
    for number in range(3):
        name = 'source' + str(number) + '.cpp'
        source = sources / 'archive' / name
        source.parent.mkdir(exist_ok=True)
        source.write_bytes(b'before\n')
        patch_name = 'patch' + str(number) + '.patch'
        raw = patch(name)
        (inputs / patch_name).write_bytes(raw)
        patches[patch_name] = build.digest(raw)
        rows.append({'member': 'archive/' + name, 'beforeSha256': build.digest(b'before\n'), 'afterSha256': build.digest(b'after\n')})
    raw = (json.dumps({'sourceMembers': rows}) + '\n').encode()
    (inputs / 'marked-plan.json').write_bytes(raw)
    monkeypatch.setattr(build, 'PATCHES', patches)
    monkeypatch.setattr(build, 'PLAN', build.digest(raw))
    return (inputs, root)

class RecipientBuildTests(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.tmp_path = Path(folder.name)

    def daemon_fixture(self):
        plan = build.docker_plan(build.SECONDARY / 'marked-private-test', Path('/run/marked-test/docker.sock'))
        raw = b'\0'.join(arg.encode() for arg in plan['expectedDaemonArgv']) + b'\0'
        record = {'pid': 7777, 'startTicks': '900', 'argvSha256': build.digest(raw),
                  'executableSha256': 'a' * 64, 'networkNamespaceInode': 123,
                  'socket': '/run/marked-test/docker.sock', 'paths': {}}
        for number, path in enumerate((str(build.SECONDARY / 'marked-private-test/daemon-data'),
                                       str(build.SECONDARY / 'marked-private-test/daemon-exec'),
                                       str(build.SECONDARY / 'marked-private-test/daemon-tmp'),
                                       '/run/marked-test', '/run/marked-test/docker.sock')):
            socket_path = path.endswith('.sock')
            record['paths'][path] = {'identity': [8, number + 100, 0, 0, 0o660 if socket_path else 0o700],
                                      'kind': 'socket' if socket_path else 'directory'}
        def info(path):
            row = record['paths'][str(path)]; value = row['identity']
            return SimpleNamespace(st_dev=value[0], st_ino=value[1], st_uid=value[2], st_gid=value[3],
                                   st_mode=value[4] | (stat.S_IFSOCK if row['kind'] == 'socket' else stat.S_IFDIR))
        self.enterContext(mock.patch.object(build, 'process_start', return_value='900'))
        self.enterContext(mock.patch.object(build, 'sha', return_value='a' * 64))
        def content(path):
            if str(path).endswith('cmdline'):
                return raw
            if str(path).endswith('environ'):
                return b'\0'.join((key + '=' + value).encode() for key, value in plan['daemonEnvironment'].items()) + b'\0'
            return b'{}\n'
        self.enterContext(mock.patch.object(Path, 'read_bytes', autospec=True, side_effect=content))
        net_read = self.enterContext(mock.patch.object(Path, 'read_text', return_value='header\nheader\n lo: 0 0\n'))
        self.enterContext(mock.patch.object(Path, 'stat', autospec=True,
                                          side_effect=lambda path: SimpleNamespace(st_ino=456 if 'self' in str(path) else 123)))
        self.enterContext(mock.patch.object(Path, 'lstat', autospec=True, side_effect=info))
        self.enterContext(mock.patch.object(Path, 'is_symlink', return_value=False))
        connection = mock.Mock(); connection.getsockopt.return_value = struct.pack('3i', 7777, 0, 0)
        self.enterContext(mock.patch.object(build.socket, 'socket', return_value=connection))
        return plan, record, connection, net_read

    def test_daemon_guard_binds_peer_lifetime_storage_network_without_sending_bytes(self):
        plan, record, connection, _ = self.daemon_fixture()
        value = build.verify_private_daemon(record, plan)
        assert value['peerAttributedWithoutMessages'] and not value['dockerCommandsDispatched']
        connection.connect.assert_called_once_with(record['socket'])
        connection.close.assert_called_once(); connection.send.assert_not_called(); connection.sendall.assert_not_called()

    def test_daemon_foreign_peer_is_closed_and_refused(self):
        plan, record, connection, _ = self.daemon_fixture()
        connection.getsockopt.return_value = struct.pack('3i', 7777, 1000, 1000)
        with self.assertRaisesRegex(ValueError, 'exact new private daemon'):
            build.verify_private_daemon(record, plan)
        connection.close.assert_called_once(); connection.send.assert_not_called()

    def test_daemon_owner_or_storage_argv_change_refuses_before_connect(self):
        plan, record, connection, _ = self.daemon_fixture()
        plan['expectedDaemonArgv'][2] = '--data-root=/var/lib/docker'
        with self.assertRaisesRegex(ValueError, 'arguments differ'):
            build.verify_private_daemon(record, plan)
        connection.connect.assert_not_called()

    def test_daemon_external_interface_refuses_before_connect(self):
        plan, record, connection, net_read = self.daemon_fixture()
        net_read.return_value += ' eth0: 0 0\n'
        with self.assertRaisesRegex(ValueError, 'isolated network'):
            build.verify_private_daemon(record, plan)
        connection.connect.assert_not_called()

    def test_daemon_replacement_after_peer_read_refuses_and_closes(self):
        plan, record, connection, _ = self.daemon_fixture()
        with mock.patch.object(build, 'process_start', side_effect=['900', '901']):
            with self.assertRaisesRegex(ValueError, 'replaced'):
                build.verify_private_daemon(record, plan)
        connection.close.assert_called_once()

    def test_daemon_record_must_include_both_actual_storage_directories(self):
        plan, record, connection, _ = self.daemon_fixture()
        del record['paths'][str(build.SECONDARY / 'marked-private-test/daemon-exec')]
        with self.assertRaisesRegex(ValueError, 'omits storage'):
            build.verify_private_daemon(record, plan)
        connection.connect.assert_not_called()

    def test_daemon_unplanned_proxy_environment_refuses_before_connect(self):
        plan, record, connection, _ = self.daemon_fixture()
        inherited = dict(plan['daemonEnvironment'], HTTP_PROXY='http://unrelated:8080')
        environment = b'\0'.join((key + '=' + value).encode() for key, value in inherited.items()) + b'\0'
        original = Path.read_bytes.mock.side_effect
        Path.read_bytes.mock.side_effect = lambda path: environment if str(path).endswith('environ') else original(path)
        with self.assertRaisesRegex(ValueError, 'environment differs'):
            build.verify_private_daemon(record, plan)
        connection.connect.assert_not_called()

    def test_conservative_whole_build_budget_refuses_before_allocation(self):
        for root, secondary in [(4 * build.GIB - 1, 30 * build.GIB), (5 * build.GIB, 29 * build.GIB - 1)]:
            with self.subTest(root=root, secondary=secondary):
                with self.assertRaisesRegex(ValueError, '25GiB'):
                    build.budget(root, secondary)

    def test_budget_does_not_call_conservative_reserve_measured_peak(self):
        value = build.budget(4 * build.GIB, 29 * build.GIB)
        assert value['measuredPeakBytes'] is None
        assert value['conservativeBuildReserveBytes'] == 25 * build.GIB

    def test_actual_host_memory_must_cover_builder_and_independent_margin(self):
        with self.assertRaisesRegex(ValueError, 'MemAvailable'):
            build.memory_budget(10 * build.GIB - 1)
        value = build.memory_budget(10 * build.GIB)
        assert value['builderMaxMemoryBytes'] == 8 * build.GIB
        assert value['requiredHostMemoryMarginBytes'] == 2 * build.GIB

    def test_frozen_builder_derived_control_is_separate_and_env_reaches_all_commands(self):
        frozen = (ROOT / 'release/build-linux-lgpl-runtime.py').read_bytes()
        original_sha = build.digest(frozen)
        marked = build.derived_builder(frozen, 'a' * 64)
        assert build.digest(frozen) == original_sha == build.TOOLS['build-linux-lgpl-runtime.py']
        assert build.digest(marked) != original_sha
        tree = ast.parse(marked)
        assignments = [n for n in ast.walk(tree) if isinstance(n, ast.Assign) and any((isinstance(t, ast.Name) and t.id == 'env' for t in n.targets))]
        assert len(assignments) == 1
        assert "'CMAKE_EXPORT_COMPILE_COMMANDS':'ON'" in marked.decode()
        source = marked.decode()
        assert source.index('marked.marked_sources(inputs,root)') < source.index('for module in order[:-1]')
        assert 'cwd=cwd,env=env,stdout=stream' in source
        assert "run('pyside-setup','wheel'" in source
        assert (ROOT / 'release/build-linux-lgpl-runtime.py').read_bytes() == frozen

    def test_changed_frozen_build_control_is_refused(self):
        frozen = (ROOT / 'release/build-linux-lgpl-runtime.py').read_bytes()
        with self.assertRaisesRegex(ValueError, 'Frozen'):
            build.derived_builder(frozen + b'\n', 'a' * 64)

    def test_frozen_derivation_cli_allowlist_unchanged(self):
        raw = (ROOT / 'release/derive-source-pyside-wheel.py').read_bytes()
        assert build.digest(raw) == build.TOOLS['derive-source-pyside-wheel.py']
        spec = importlib.util.spec_from_file_location('derivation_readonly', ROOT / 'release/derive-source-pyside-wheel.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert set(module.REVIEWED_PRODUCERS) == {module.PRODUCER_HASH, module.RECIPIENT_HASH}
        assert 'augmentormarked' not in repr(module.REVIEWED_PRODUCERS)

    def test_unified_patch_requires_exact_original_context(self):
        assert build.apply_patch_bytes(b'before\n', patch()) == b'after\n'
        with self.assertRaisesRegex(ValueError, 'exact original'):
            build.apply_patch_bytes(b'foreign\n', patch())

    def test_patch_rejects_overlapping_or_unsupported_hunks(self):
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            build.apply_patch_bytes(b'before\n', patch() + b'@@ -1,1 +1,1 @@\n-after\n+extra\n')
        with self.assertRaisesRegex(ValueError, 'Unsupported patch'):
            build.apply_patch_bytes(b'before\n', b'--- a/source.cpp\n+++ b/source.cpp\n@@ invalid @@\n')

    def test_three_source_before_and_after_hashes_are_applied_and_journalled(self):
        tmp_path = self.tmp_path
        monkeypatch = SimpleNamespace(setattr=lambda obj, name, value: self.enterContext(mock.patch.object(obj, name, value)))
        inputs, root = source_fixture(tmp_path, monkeypatch)
        build.marked_sources(inputs, root)
        assert all((p.read_bytes() == b'after\n' for p in (root / 'sources/archive').iterdir()))
        assert not json.loads((root / 'marked-source-intent.json').read_text())['completed']
        assert json.loads((root / 'marked-sources.json').read_text())['completed']

    def test_third_wrong_source_prevents_all_edits_and_intent(self):
        tmp_path = self.tmp_path
        monkeypatch = SimpleNamespace(setattr=lambda obj, name, value: self.enterContext(mock.patch.object(obj, name, value)))
        inputs, root = source_fixture(tmp_path, monkeypatch)
        (root / 'sources/archive/source2.cpp').write_bytes(b'foreign\n')
        with self.assertRaisesRegex(ValueError, 'Changed pinned'):
            build.marked_sources(inputs, root)
        assert (root / 'sources/archive/source0.cpp').read_bytes() == b'before\n'
        assert (root / 'sources/archive/source1.cpp').read_bytes() == b'before\n'
        assert not (root / 'marked-source-intent.json').exists()

    def test_changed_patch_or_plan_refuses_before_edit(self):
        tmp_path = self.tmp_path
        monkeypatch = SimpleNamespace(setattr=lambda obj, name, value: self.enterContext(mock.patch.object(obj, name, value)))
        inputs, root = source_fixture(tmp_path, monkeypatch)
        (inputs / 'patch1.patch').write_bytes(patch(new='unreviewed'))
        with self.assertRaisesRegex(ValueError, 'Changed pinned'):
            build.marked_sources(inputs, root)
        assert all((p.read_bytes() == b'before\n' for p in (root / 'sources/archive').iterdir()))

    def test_after_hash_mismatch_refuses_without_partial_edit(self):
        tmp_path = self.tmp_path
        monkeypatch = SimpleNamespace(setattr=lambda obj, name, value: self.enterContext(mock.patch.object(obj, name, value)))
        inputs, root = source_fixture(tmp_path, monkeypatch)
        value = json.loads((inputs / 'marked-plan.json').read_text())
        value['sourceMembers'][2]['afterSha256'] = 'f' * 64
        raw = json.dumps(value).encode()
        (inputs / 'marked-plan.json').write_bytes(raw)
        monkeypatch.setattr(build, 'PLAN', build.digest(raw))
        with self.assertRaisesRegex(ValueError, 'result differs'):
            build.marked_sources(inputs, root)
        assert not (root / 'marked-source-intent.json').exists()

    def test_input_path_escape_is_rejected(self):
        tmp_path = self.tmp_path
        for name in ['../escape', '/absolute', 'a/../escape', 'a\\escape']:
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, 'Unsafe'):
                    build.checked(tmp_path, name)

    def test_input_link_and_hardlink_are_refused(self):
        tmp_path = self.tmp_path
        source = tmp_path / 'source'
        source.write_bytes(b'known')
        link = tmp_path / 'link'
        link.symlink_to('source')
        with self.assertRaisesRegex(ValueError, 'link'):
            build.checked(tmp_path, 'link')
        link.unlink()
        link.hardlink_to(source)
        with self.assertRaisesRegex(ValueError, 'single-link'):
            build.checked(tmp_path, 'source')

    def test_private_daemon_plan_does_not_use_owner_socket_network_or_mounts(self):
        directory = build.SECONDARY / 'marked-recipient-review-v1'
        plan = build.docker_plan(directory, Path('/run/augmentor-marked-review/docker.sock'))
        assert plan['daemonProvisioning'][:3] == ['/usr/bin/unshare', '--net', '--']
        assert '--bridge=none' in plan['expectedDaemonArgv']
        assert '--data-root=' + str(directory / 'daemon-data') in plan['expectedDaemonArgv']
        assert '--exec-root=' + str(directory / 'daemon-exec') in plan['expectedDaemonArgv']
        assert all(('/var/run/docker.sock' not in arg for argv in plan['commands'] for arg in argv))
        assert all((arg not in ('--volume', '--mount', '--privileged', '--device') for argv in plan['commands'] for arg in argv))
        assert '--network=none' in plan['commands'][1] and '--pull=false' in plan['commands'][1]
        assert not plan['commandsExecuted'] and (not plan['daemonProvisioned'])
        assert all('stop' not in argv and 'kill' not in argv for argv in plan['commands'])
        assert plan['requiredBeforeExport'] and 'no pending/unknown' in plan['requiredBeforeExport'][0]

    def test_daemon_plan_refuses_unbound_storage_socket_or_long_unix_address(self):
        for directory, socket_path in [(Path('/tmp/build'), Path('/run/owned/docker.sock')), (build.SECONDARY / 'a/../foreign', Path('/run/owned/docker.sock')), (build.SECONDARY / 'new-build', Path('/run/owned/foreign.sock')), (build.SECONDARY / 'new-build', Path('/run/' + 'a' * 100 + '/docker.sock'))]:
            with self.subTest(directory=directory, socket_path=socket_path):
                with self.assertRaises(ValueError):
                    build.docker_plan(directory, socket_path)

    def test_ninja_cache_must_prove_command_export(self):
        tmp_path = self.tmp_path
        cache = tmp_path / 'CMakeCache.txt'
        cache.write_text('CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON\nCMAKE_GENERATOR:INTERNAL=Ninja\n')
        (tmp_path / 'compile_commands.json').write_text('[{"directory":"/work/build", "file":"/work/source/a.cpp", "arguments":["c++", "-c", "a.cpp"]}]')
        assert build.cache_verified(cache)['translationUnits'] == 1
        cache.write_text('CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=OFF\nCMAKE_GENERATOR:INTERNAL=Ninja\n')
        with self.assertRaisesRegex(ValueError, 'export'):
            build.cache_verified(cache)

    def test_ninja_cache_empty_command_database_refuses(self):
        tmp_path = self.tmp_path
        cache = tmp_path / 'CMakeCache.txt'
        cache.write_text('CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON\nCMAKE_GENERATOR:INTERNAL=Ninja\n')
        (tmp_path / 'compile_commands.json').write_text('[]')
        with self.assertRaisesRegex(ValueError, 'database'):
            build.cache_verified(cache)

    def test_native_target_candidate_is_not_falsely_declared_complete_source_mapping(self):
        root = self.tmp_path
        (root / 'compile-evidence').mkdir()
        (root / 'compile-evidence/0-targets.txt').write_text('lib/libQt6Core.so.6.8.2: CXX_SHARED_LIBRARY_LINKER\nQt6Core: phony\n')
        evidence = [{'directory': '/work/builds/qtbase'}]
        candidates = build.native_target_candidates('lib/libQt6Core.so.6.8.2', root, evidence)
        assert len(candidates) == 1 and candidates[0]['target'] == 'lib/libQt6Core.so.6.8.2'
        assert build.native_target_candidates('PySide6/QtCore.abi3.so', root, evidence) == []
        def query(argv, stdout, **kwargs):
            assert argv[0:2] == ['ninja', '-n']
            assert '-t' in argv and 'query' in argv
            stdout.write(b'lib/libQt6Core.so.6.8.2: input: linker\n')
            return SimpleNamespace(returncode=0)
        rows = [{'path': 'lib/libQt6Core.so.6.8.2'}, {'path': 'PySide6/QtCore.abi3.so'}]
        with mock.patch.object(build.subprocess, 'run', side_effect=query) as execute:
            build.query_native_targets(rows, root, evidence)
        execute.assert_called_once()
        assert all(not row['targetAttributionComplete'] for row in rows)
        assert rows[0]['ninjaTargetCandidates'][0]['querySha256']
        assert 'manual finite attribution' in rows[1]['unresolvedReason']

    def test_native_target_ambiguity_is_bounded_without_accepting_a_guessed_match(self):
        (self.tmp_path / 'compile-evidence').mkdir()
        (self.tmp_path / 'compile-evidence/0-targets.txt').write_text(''.join(
            f'copies/{number}/libQt6Core.so.6.8.2: linker\n' for number in range(33)))
        with self.assertRaisesRegex(ValueError, 'ambiguity'):
            build.native_target_candidates('lib/libQt6Core.so.6.8.2', self.tmp_path,
                                           [{'directory': '/work/builds/qtbase'}])

    def test_new_control_publication_refuses_reuse(self):
        tmp_path = self.tmp_path
        path = tmp_path / 'record.json'
        build.new_json(path, {'completed': False})
        with self.assertRaises(FileExistsError):
            build.new_json(path, {'completed': True})
        assert json.loads(path.read_text()) == {'completed': False}

    def test_prepare_and_builder_cli_do_not_execute_host_commands_at_import(self):
        tree = ast.parse((ROOT / 'release/probe-recipient-core-bindings-build.py').read_text())
        prepare = next((node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'prepare'))
        assert not any((isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and (node.func.value.id == 'subprocess') for node in ast.walk(prepare)))
if __name__ == '__main__':
    unittest.main()
