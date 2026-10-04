#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Finite marked Qt6.8.2/PySide6.8.2.1 build controls; not a product proof.

prepare authenticates retained public inputs and writes a NEW control/command
plan. It never starts a daemon, imports an image, extracts sources or builds.
builder is for a subsequently approved, separately provisioned private Docker
fixture. Frozen tools stay byte-identical. Failed paths are never resumed.
Desktop/Browser replacement, source/notice completeness and legal review remain
separate gates, including when every command here succeeds.
"""
import argparse
import ast
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import socket
import stat
import struct
import subprocess
import sys
import tarfile
import types

GIB = 1024 ** 3
RESERVE = 25 * GIB  # Conservative allowance; measured build peak is still unknown.
FLOOR = 4 * GIB
SECONDARY = Path('/media/manolo/DATA/augmentor-linux-rollout-retained-20261003')
MANIFEST = '0770ed3ccab87552b65c5c43fab77118f889f2019ef70a68ef076a43296d2229'
PLAN = '1ec7cbaaec7c52f402c5d98ad46ab9480b5c295b9e9b4cfe8ac21cdaa0401f0f'
POLICY = '969dca5093394282eef5517ade6e0bcb31d1a9ceb1b22513d213aa9ef434196e'
INVENTORY = 'bc6cd4560d3d984dc11e2b2faceb1b1b2fcf73440fad5a4d9c6a8f76a594b7b3'
BASE = 'sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3'
BASE_TAR = 'e6dc7a492df0dd9ff255d22e887cc07b32a8874360990b3ebe2cb30ee96f6207'
TOOLS = {
    'build-linux-lgpl-runtime.py': '9594c4439638cccb8f3bb91b34848cb95169d075aa61ab614171fd066c41dac7',
    'stage-source-qt-runtime.py': '3dc1cd88387cdb0afa49ef9a68f44e4a0591fac80860a4f5c78adf6c27fd9049',
    'derive-source-pyside-wheel.py': '50c2ec4720dd784a0a408845a934bc622ed679c7404a6668d997e0710cf7b7eb',
    'collect-source-qt-notices.py': '38b58e8c29b658fa3b5fec8f8b177fc5027436531e4db44cb3fd7ca8f88cde1f',
    'verify-ubuntu-base-archive.py': 'f8eff4c75bccacd3db07191dd9b30f79ea6c9dbd3c82eee2e355983aa11eed35',
    'acquire-ubuntu-toolchain.py': 'bafb64db71aa312c3e2f9e5bfe0d77e33640a886128ddbe2bfeb3fbc8c2dce40',
    'acquire-ubuntu-toolchain-sources.py': '0d098d6cdaba46718057e7886dbebafd70aba5ca67ac9531457cb8a0d6238791',
    'qt-source-runtime-recipient-builder.Dockerfile': '9f256bf7043c0c0d44e8bc5ff2208df5e2260ae8c903864d6fd80694de14c20a',
}
SOURCE_LOCK = '76d303297daed229aa5350d6e81e47d29184a290d036023d2653a5d7ae14e102'
BINARY_LOCK = 'ee6c3fb58c36563be35466ac6e8c0dfdef3889a7e4f9663d6483f60b623166d2'
PATCHES = {
    'qtbase-core-marker-v1.patch': 'faf49c9af6b4693c2fe2d7d9c6e790542696dbb962294af3cbe4e03a729e114a',
    'pyside-shiboken-markers-v1.patch': '8b05c23ec7b358952f79f54cd3afc9c084123019e2e57d0f6146e323ff5b8de2',
}
ORDER = ['qtbase', 'qtshadertools', 'qtsvg', 'qtimageformats', 'qtdeclarative', 'qtwayland', 'pyside-setup']
ENV_LINE = "    env={**os.environ,'CMAKE_BUILD_PARALLEL_LEVEL':'2','LLVM_INSTALL_DIR':'/usr/lib/llvm-18'}\n"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked(root, name, expected=None):
    relative = PurePosixPath(name)
    if not name or str(relative) != name or relative.is_absolute() or '..' in relative.parts or '\\' in name:
        raise ValueError('Unsafe input path.')
    for count in range(1, len(relative.parts) + 1):
        if (root / Path(*relative.parts[:count])).is_symlink():
            raise ValueError('Input path contains a link.')
    path = root / name
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError('Use ordinary single-link retained inputs.')
    if expected is not None and sha(path) != expected:
        raise ValueError('Changed pinned input: ' + name)
    return path


def load_tool(root, name):
    path = checked(root, name, TOOLS[name])
    # Execute the verified source bytes, never an unbound .pyc for this module.
    module = types.ModuleType('marked_' + name.replace('-', '_'))
    module.__file__ = str(path)
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    finally:
        sys.dont_write_bytecode = old
    return module


def write_new(path, data):
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_DIRECTORY | os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def new_json(path, value):
    write_new(path, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())


def budget(root_free, secondary_free):
    if root_free < FLOOR or secondary_free < RESERVE + FLOOR:
        raise ValueError('Require root4GiB and secondary25GiB reserve plus4GiB floor.')
    return {'rootAvailableBytes': root_free, 'secondaryAvailableBytes': secondary_free,
            'conservativeBuildReserveBytes': RESERVE, 'floorBytes': FLOOR,
            'measuredPeakBytes': None}


def measure_budget():
    root = os.statvfs('/'); secondary = os.statvfs(SECONDARY)
    if os.stat('/').st_dev == SECONDARY.stat().st_dev:
        raise ValueError('Secondary build storage must be a separate filesystem.')
    value = budget(root.f_bavail * root.f_frsize, secondary.f_bavail * secondary.f_frsize)
    fields = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    available = fields['MemAvailable'].split()
    if len(available) != 2 or available[1] != 'kB':
        raise ValueError('Cannot measure actual host memory available.')
    value.update(memory_budget(int(available[0]) * 1024))
    value.update(measuredUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 rootPath='/', secondaryPath=str(SECONDARY),
                 rootStatvfs=[root.f_bavail, root.f_frsize],
                 secondaryStatvfs=[secondary.f_bavail, secondary.f_frsize])
    return value


def memory_budget(available):
    if available < 10 * GIB:
        raise ValueError('Require8GiB builder limit plus2GiB actual host MemAvailable margin.')
    return {'hostMemoryAvailableBytes': available, 'builderMaxMemoryBytes': 8 * GIB,
            'requiredHostMemoryMarginBytes': 2 * GIB}


def apply_patch_bytes(before, patch):
    """One complete pinned file, unified hunks only; refuse fuzzy application."""
    lines = before.decode().splitlines(True); changes = patch.decode().splitlines(True)
    if len(changes) < 3 or not changes[0].startswith('--- a/') or not changes[1].startswith('+++ b/'):
        raise ValueError('Invalid marked patch header.')
    output = []; cursor = 0; index = 2
    while index < len(changes):
        match = re.fullmatch(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n', changes[index])
        if match is None:
            raise ValueError('Unsupported patch hunk.')
        start = int(match[1]) - 1; removed = []; added = []; index += 1
        if start < cursor:
            raise ValueError('Overlapping patch hunks.')
        while index < len(changes) and not changes[index].startswith('@@ '):
            line = changes[index]; index += 1
            if line[:1] not in (' ', '-', '+'):
                raise ValueError('Unsupported patch line.')
            if line[0] != '+':
                removed.append(line[1:])
            if line[0] != '-':
                added.append(line[1:])
        if len(removed) != int(match[2]) or len(added) != int(match[4]) or lines[start:start + len(removed)] != removed:
            raise ValueError('Patch does not match exact original lines.')
        output += lines[cursor:start] + added; cursor = start + len(removed)
    return ''.join(output + lines[cursor:]).encode()


def split_patches(raw):
    return [b'--- a/' + part for part in raw.split(b'--- a/')[1:]]


def marked_sources(inputs, root):
    plan = json.loads(checked(inputs, 'marked-plan.json', PLAN).read_text())
    patches = []
    for name, expected in PATCHES.items():
        patches += split_patches(checked(inputs, name, expected).read_bytes())
    rows = plan['sourceMembers']
    if len(rows) != 3 or len(patches) != 3:
        raise ValueError('Expected exactly three marked source members.')
    result = []
    # Validate all originals/results before changing any source file.
    pending = []
    for row, patch in zip(rows, patches):
        path = checked(root / 'sources', row['member'], row['beforeSha256'])
        if patch.splitlines()[1][6:].decode() != row['member'].split('/', 1)[1]:
            raise ValueError('Patch member differs from source binding.')
        after = apply_patch_bytes(path.read_bytes(), patch)
        if digest(after) != row['afterSha256']:
            raise ValueError('Marked source result differs from reviewed hash.')
        pending.append((path, after)); result.append(row)
    new_json(root / 'marked-source-intent.json', {'sourceMembers': result, 'completed': False})
    for path, after in pending:
        with path.open('wb') as stream:
            stream.write(after); stream.flush(); os.fsync(stream.fileno())
    new_json(root / 'marked-sources.json', {'sourceMembers': result, 'completed': True})


def derived_builder(original, wrapper_sha):
    if digest(original) != TOOLS['build-linux-lgpl-runtime.py'] or original.count(ENV_LINE.encode()) != 1:
        raise ValueError('Frozen build control changed.')
    hook = ("    import importlib.util\n"
            "    marked_path=inputs/'marked-wrapper.py'\n"
            f"    assert sha(marked_path)=={wrapper_sha!r}\n"
            "    marked_spec=importlib.util.spec_from_file_location('marked_controls',marked_path)\n"
            "    marked=importlib.util.module_from_spec(marked_spec);marked_spec.loader.exec_module(marked)\n"
            "    marked.marked_sources(inputs,root)\n"
            "    env={**os.environ,'CMAKE_BUILD_PARALLEL_LEVEL':'2','LLVM_INSTALL_DIR':'/usr/lib/llvm-18',\n"
            "        'CMAKE_EXPORT_COMPILE_COMMANDS':'ON'}\n")
    value = original.replace(ENV_LINE.encode(), hook.encode())
    ast.parse(value)
    return value


def authenticate_kit(kit):
    manifest_path = checked(kit, 'kit-manifest.json', MANIFEST)
    manifest = json.loads(manifest_path.read_text())
    if manifest['format'] != 'augmentor-private-qt-recipient-source-kit/2' or len(manifest['files']) != 1712:
        raise ValueError('Wrong retained kit inventory.')
    names = set()
    for row in manifest['files']:
        if row['path'] in names:
            raise ValueError('Duplicate retained kit member.')
        names.add(row['path']); path = checked(kit, row['path'], row['sha256'])
        if path.stat().st_size != row['bytes']:
            raise ValueError('Changed kit member size.')
    actual = {str(path.relative_to(kit)) for path in kit.rglob('*') if not path.is_dir()}
    if actual != names | {'kit-manifest.json'}:
        raise ValueError('Unbound kit members/caches refused before importing frozen controls.')
    tools = kit / 'release'
    for name, expected in TOOLS.items():
        checked(tools, name, expected)
    policy = json.loads(checked(tools, 'linux-lgpl-runtime-sources.json', POLICY).read_text())
    if policy['buildOrder'] != ORDER or len(policy['sources']) != 7:
        raise ValueError('Wrong seven-archive policy.')
    for row in policy['sources']:
        archive = checked(kit / 'archives', row['file'], row['sha256'])
        checksum = checked(kit / 'archives', row['file'] + '.sha256').read_text().split()
        if not checksum or checksum[0] != sha(archive):
            raise ValueError('Official archive checksum differs.')
    binary = load_tool(tools, 'acquire-ubuntu-toolchain.py')
    lock_path = checked(tools, 'qualification/next-targets/20261002-ubuntu-source-toolchain-lock.json', BINARY_LOCK)
    binaries = binary.authenticate(json.loads(lock_path.read_text()), kit / 'toolchain')
    if len(binaries) != 410:
        raise ValueError('Wrong authenticated compiler/dependency set.')
    for row in binaries:
        path = checked(kit / 'toolchain/debs', PurePosixPath(row['filename']).name, row['sha256'])
        if path.stat().st_size != row['size']:
            raise ValueError('Changed signed binary size.')
    source = load_tool(tools, 'acquire-ubuntu-toolchain-sources.py')
    source_policy = json.loads(checked(kit, 'toolchain/sources/policy.json', SOURCE_LOCK).read_text())
    records = source.authenticate(source_policy, kit / 'toolchain/sources')
    for row in source_policy['objects']:
        path = checked(kit / 'toolchain/sources/objects', row['path'], row['sha256'])
        if path.stat().st_size != row['size']:
            raise ValueError('Changed authenticated source object.')
    if len(source.dsc_crosscheck(records, kit / 'toolchain/sources/objects')) != 180:
        raise ValueError('Missing exact builder/base source versions.')
    base = checked(kit, 'toolchain/public-base-image.tar', BASE_TAR)
    base_report = load_tool(tools, 'verify-ubuntu-base-archive.py').verify(base)
    return {'kitManifestSha256': MANIFEST, 'archives': policy['sources'],
            'authenticatedBinaryCount': 410, 'authenticatedSourceVersions': 180,
            'authenticatedSourceObjects': 565, 'baseArchiveVerification': base_report,
            'freshEmptyDaemonBaseImportQualified': False, 'detachedQtSignaturesVerified': False}


def docker_plan(directory, socket_path):
    """Commands for review only: provisioning is separately authorized/root-owned."""
    if (not directory.is_absolute() or not directory.is_relative_to(SECONDARY) or directory == SECONDARY
            or '..' in directory.parts or not re.fullmatch('[a-z][a-z0-9-]{1,60}', directory.name)):
        raise ValueError('Use new secondary-only daemon/storage/control paths.')
    if (not socket_path.is_absolute() or len(str(socket_path).encode()) > 90
            or socket_path.name != 'docker.sock' or '..' in socket_path.parts):
        raise ValueError('Require a short, separately private daemon socket path.')
    docker = ['/usr/bin/docker', '--config', str(directory / 'client-config'), '--host', 'unix://' + str(socket_path)]
    controls = directory / 'controls'; context = directory / 'context'
    daemon = ['/usr/bin/dockerd', '--config-file=' + str(controls / 'daemon.json'),
                               '--data-root=' + str(directory / 'daemon-data'),
                               '--exec-root=' + str(directory / 'daemon-exec'),
                               '--pidfile=' + str(directory / 'daemon.pid'),
                               '--host=unix://' + str(socket_path), '--bridge=none', '--iptables=false',
                               '--ip-forward=false', '--ip-masq=false', '--userland-proxy=false', '--storage-driver=vfs']
    return {
        'expectedDaemonArgv': daemon,
        'daemonProvisioning': ['/usr/bin/unshare', '--net', '--', *daemon],
        'daemonEnvironment': {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin',
                              'DOCKER_TMPDIR': str(directory / 'daemon-tmp')},
        'clientEnvironment': {'PATH': '/usr/bin:/bin', 'DOCKER_BUILDKIT': '0',
                              'TMPDIR': str(directory / 'client-tmp')},
        'commands': [
            docker + ['image', 'load', '--input', str(directory / 'public-base-image.tar')],
            docker + ['build', '--network=none', '--pull=false', '--file',
                      str(controls / 'qt-source-runtime-recipient-builder.Dockerfile'),
                      '--tag', 'augmentor-marked-recipient:' + directory.name, str(context)],
            docker + ['create', '--name', directory.name, '--network=none', '--cpus=2', '--memory=8g',
                      '--pids-limit=512', '--cap-drop=ALL', '--security-opt=no-new-privileges',
                      '--user=1001:1001', '--env=CMAKE_EXPORT_COMPILE_COMMANDS=ON',
                      'augmentor-marked-recipient:' + directory.name],
            docker + ['cp', str(directory / 'inputs') + '/.', directory.name + ':/inputs'],
            docker + ['start', directory.name],
            docker + ['exec', '--user=1001:1001', directory.name, '/work/build-python/bin/python', '-B',
                      '/inputs/marked-wrapper.py', 'builder'],
            docker + ['cp', directory.name + ':/work/marked-runtime-build', str(directory / 'retained-build')],
        ],
        'requiredBeforeAnyDaemonCommand': [
            'Root-reviewed fresh namespace, all directories/socket private and empty; no owner daemon.',
            'Exact daemon executable/argv/PID/start/storage/socket SO_PEERCRED and fresh empty image/container/volume maps.',
            'New network namespace with onlylo; no shared containerd or configured host volumes/devices; pinned empty daemon.json.',
            'Exact clean daemon/client environments only; no inherited Docker contexts, TLS, credentials, proxies or shared BuildKit.',
            'Reauthenticate kit/controls; statvfs root4GiB/secondary25GiB+4GiB and actual MemAvailable10GiB before allocations/start.',
            'Copy exact verified public DEBs as context/debs; inputs7 archives+controls; no host bind mounts.',
            'Build original recipe offline at original digest FROM after load; failure is terminal: no retag/pull/rewrite.',
            'Inspect actual builder image and created container: network none, no mounts/devices/capabilities, UID1001 limits.',
            'Record durable intent before each command; unknown/failure terminal, no implicit cleanup/resume/retry.',
            'Retain private daemon and inert running container/work inputs/objects/generated files/outputs; no automatic stop/kill/delete.',
        ],
        'requiredBeforeExport': [
            'Exact build exec knownexit0, completed marked-build result, no pending/unknown build/command intent.',
            'Inspect exact containerID/private daemon/source: PID1 argv sleep infinity, UID1001; no remaining Python/compiler/CMake/Ninja or other children.',
            'Pin stable complete source/object/generated/input/output tree snapshot before and after read-only docker cp, then verify exported bytes/links/metadata.',
            'No automatic stop or signal: retain the inert running container if this idle/stability fence fails or export is uncertain.',
            'A subsequent separately reviewed normal teardown may stop only its exact owned process; never impose stop timeout SIGKILL.',
        ], 'daemonProvisioned': False, 'commandsExecuted': False,
    }


def process_start(pid):
    return Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()[19]


def verify_private_daemon(record, command_plan):
    """Read-only future host fence. Provisioning record must be root-reviewed.

    No caller here dispatches Docker commands. Connecting to its explicit new
    socket only attributes SO_PEERCRED; zero bytes are sent, then close. Bind
    this record's exact hash in the separately reviewed host controller before
    using this function; a caller-chosen PID record alone is not authority.
    """
    pid = record['pid']; start = record['startTicks']
    if type(pid) is not int or pid <= 1 or process_start(pid) != start:
        raise ValueError('Daemon lifetime differs.')
    argv = Path('/proc', str(pid), 'cmdline').read_bytes().split(b'\0')
    argv = [part.decode() for part in argv if part]
    if argv != command_plan['expectedDaemonArgv'] or digest(Path('/proc', str(pid), 'cmdline').read_bytes()) != record['argvSha256']:
        raise ValueError('Daemon arguments differ from separate storage/offline plan.')
    if sha(Path('/proc', str(pid), 'exe')) != record['executableSha256']:
        raise ValueError('Daemon executable changed.')
    environment = Path('/proc', str(pid), 'environ').read_bytes()
    pairs = [part.decode().split('=', 1) for part in environment.split(b'\0') if part]
    if (any(len(part) != 2 for part in pairs) or len(dict(pairs)) != len(pairs)
            or dict(pairs) != command_plan['daemonEnvironment']):
        raise ValueError('Daemon environment differs from the clean private plan.')
    network = Path('/proc', str(pid), 'ns/net').stat().st_ino
    interfaces = sorted(line.split(':', 1)[0].strip() for line in Path('/proc', str(pid), 'net/dev').read_text().splitlines()[2:])
    if (network != record['networkNamespaceInode'] or network == Path('/proc/self/ns/net').stat().st_ino
            or interfaces != ['lo']):
        raise ValueError('Daemon must occupy the new isolated network namespace with onlylo.')
    values = {arg.split('=', 1)[0]: arg.split('=', 1)[1] for arg in argv[1:] if '=' in arg}
    required_paths = {values['--data-root'], values['--exec-root'], command_plan['daemonEnvironment']['DOCKER_TMPDIR'],
                      str(Path(record['socket']).parent), record['socket']}
    if set(record['paths']) != required_paths:
        raise ValueError('Daemon record omits storage/socket topology or adds unrelated paths.')
    if Path(values['--config-file']).read_bytes() != b'{}\n':
        raise ValueError('Daemon must use the exact empty private configuration.')
    before = {}
    for name, row in record['paths'].items():
        path = Path(name)
        if not path.is_absolute() or path.is_symlink():
            raise ValueError('Daemon storage/socket link refused.')
        info = path.lstat()
        metadata = [info.st_dev, info.st_ino, info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)]
        if metadata != row['identity'] or info.st_uid != 0 or info.st_mode & 0o002:
            raise ValueError('Daemon storage/socket ownership changed.')
        expected_kind = 'socket' if name == record['socket'] else 'directory'
        if row['kind'] != expected_kind:
            raise ValueError('Daemon path kind differs from exact storage/socket role.')
        if row['kind'] == 'directory' and (not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o022):
            raise ValueError('Daemon storage must be root-owned immutable-topology directories.')
        if row['kind'] == 'socket' and not stat.S_ISSOCK(info.st_mode):
            raise ValueError('Daemon socket type changed.')
        before[name] = metadata
    sock_path = Path(record['socket'])
    expected_socket = next(arg[7:] for arg in argv if arg.startswith('--host='))
    if expected_socket != 'unix://' + str(sock_path) or str(sock_path) not in before:
        raise ValueError('Daemon socket differs from exact planned address.')
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        connection.settimeout(3); connection.connect(str(sock_path))
        peer_pid, peer_uid, _ = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if (peer_pid, peer_uid) != (pid, 0):
            raise ValueError('Socket peer is not the exact new private daemon.')
    finally:
        connection.close()
    if process_start(pid) != start:
        raise ValueError('Daemon was replaced during socket attribution.')
    if (digest(Path('/proc', str(pid), 'cmdline').read_bytes()) != record['argvSha256']
            or sha(Path('/proc', str(pid), 'exe')) != record['executableSha256']):
        raise ValueError('Daemon executable/arguments changed during attribution.')
    for name, identity in before.items():
        info = Path(name).lstat()
        if [info.st_dev, info.st_ino, info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)] != identity:
            raise ValueError('Daemon directory/socket was replaced.')
    return {'pid': pid, 'startTicks': start, 'argvSha256': record['argvSha256'],
            'peerAttributedWithoutMessages': True, 'dockerCommandsDispatched': False}


def prepare(kit, plan_directory, destination, socket_path):
    # The historical kit root may be an approved relocation alias; bind its
    # actual resolved directory, and reject links inside the signed inventory.
    kit = kit.resolve(strict=True)
    if not destination.is_absolute() or destination.resolve() != destination or not destination.is_relative_to(SECONDARY):
        raise ValueError('Use a final nonlinked secondary output path.')
    if destination.exists() or destination.is_symlink():
        raise ValueError('Use a new exclusive output; never resume a prior preparation.')
    headroom = measure_budget(); report = authenticate_kit(kit)
    plan_path = checked(plan_directory, 'marked-core-bindings-plan-v1.json', PLAN)
    plan = json.loads(plan_path.read_text())
    for row in plan['sourceMembers']:
        with tarfile.open(checked(kit / 'archives', row['archive'], row['archiveSha256'])) as archive:
            member = archive.getmember(row['member'])
            if not member.isfile() or member.size > 2 * 1024**2:
                raise ValueError('Unsafe source marker member.')
            if digest(archive.extractfile(member).read()) != row['beforeSha256']:
                raise ValueError('Marker original does not match actual archive.')
    controls = {name: checked(kit / 'release', name, expected).read_bytes() for name, expected in TOOLS.items()}
    controls['linux-lgpl-runtime-sources.json'] = checked(kit / 'release', 'linux-lgpl-runtime-sources.json', POLICY).read_bytes()
    controls['marked-plan.json'] = plan_path.read_bytes()
    for name, expected in PATCHES.items():
        controls[name] = checked(plan_directory, name, expected).read_bytes()
    controls['marked-wrapper.py'] = Path(__file__).read_bytes()
    controls['marked-builder.py'] = derived_builder(controls['build-linux-lgpl-runtime.py'], digest(controls['marked-wrapper.py']))
    controls['daemon.json'] = b'{}\n'
    command_plan = docker_plan(destination, socket_path)
    # No large inputs are copied here. Recheck immediately before small controls.
    measure_budget(); destination.mkdir(mode=0o700); (destination / 'controls').mkdir(mode=0o700)
    for name, data in controls.items():
        write_new(destination / 'controls' / name, data)
    report.update(format='augmentor-marked-recipient-build-controls/1', toolSha256=sha(Path(__file__)),
                  kitRoot=str(kit), destination=str(destination), controlFiles={name: digest(data) for name, data in controls.items()},
                  budget=headroom, dockerPlan=command_plan, markedSources=plan['sourceMembers'],
                  originalBuildControlUnchanged=True, derivedControlSeparatelyIdentified=True,
                  actualBuildExecuted=False, compiledFileNoticeMappingComplete=False,
                  recipientReplacementTested=False, licenseReviewComplete=False)
    new_json(destination / 'control-plan.json', report)
    return report


def cache_verified(path):
    values = dict(line.split('=', 1) for line in path.read_text().splitlines()
                  if '=' in line and not line.startswith(('#', '//')))
    if values.get('CMAKE_EXPORT_COMPILE_COMMANDS:BOOL') != 'ON' or values.get('CMAKE_GENERATOR:INTERNAL') != 'Ninja':
        raise ValueError('Missing explicit compiler-command export/Ninja configuration.')
    database = path.parent / 'compile_commands.json'
    commands = json.loads(database.read_text())
    if not commands or any(not isinstance(row, dict) or not {'directory', 'file'} <= row.keys()
                           or not ('command' in row or 'arguments' in row) for row in commands):
        raise ValueError('Missing compiler command database.')
    return {'directory': str(path.parent), 'cacheSha256': sha(path),
            'compileCommandsSha256': sha(database), 'translationUnits': len(commands)}


def collect_build_evidence(root):
    caches = sorted(path for path in root.rglob('CMakeCache.txt') if (path.parent / 'build.ninja').is_file())
    qt_roots = {str(root / 'builds' / name) for name in ORDER[:-1]}
    if not qt_roots <= {str(path.parent) for path in caches}:
        raise ValueError('Missing one of six Qt Ninja builds.')
    if not any('pyside-setup' in str(path) for path in caches) or not any('shiboken6' in str(path) for path in caches):
        raise ValueError('Missing PySide/shiboken Ninja build evidence.')
    evidence = root / 'compile-evidence'; evidence.mkdir(mode=0o700)
    rows = []
    for number, cache in enumerate(caches):
        row = cache_verified(cache); row['tools'] = {}
        row['retainedNinjaInputs'] = {name: sha(checked(cache.parent, name))
                                    for name in ('build.ninja', '.ninja_log', '.ninja_deps')}
        for tool in ('targets', 'commands', 'deps', 'graph'):
            output = evidence / (str(number) + '-' + tool + '.txt')
            # Ninja1.11 AFTER_LOGS tools ordinarily open logs for writing;
            # -n suppresses that before read-only evidence collection.
            argv = ['ninja', '-n', '-C', str(cache.parent), '-t', tool]
            if tool == 'targets':
                argv.append('all')
            with output.open('xb') as stream:
                result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, timeout=120)
            if result.returncode:
                raise RuntimeError('Ninja evidence command failed; retain partial evidence.')
            row['tools'][tool] = {'argv': argv, 'sha256': sha(output), 'bytes': output.stat().st_size}
        if {name: sha(checked(cache.parent, name)) for name in row['retainedNinjaInputs']} != row['retainedNinjaInputs']:
            raise ValueError('Ninja evidence collection changed original build inputs/logs.')
        rows.append(row)
    # Sources, build trees, .ninja_deps/.ninja_log, objects, generated files and
    # install manifests remain in the inert container; export needs a separately
    # recorded completed-idle/stable-tree fence. No automatic stop/kill here.
    new_json(evidence / 'index.json', {'builds': rows, 'wholeBuildRootRetained': True,
             'unityGeneratedSourcesMustRemain': True, 'compiledSourceMappingComplete': False})
    return rows


def native_target_candidates(member, root, evidence):
    """Retain actual target queries; basename matches are candidates, not proof."""
    candidates = []
    for number, build in enumerate(evidence):
        targets = checked(root / 'compile-evidence', str(number) + '-targets.txt').read_text().splitlines()
        for line in targets:
            target, separator, rule = line.partition(': ')
            if separator and rule != 'phony' and PurePosixPath(target).name == PurePosixPath(member).name:
                candidates.append({'buildDirectory': build['directory'], 'target': target, 'rule': rule})
    if len(candidates) > 32:
        raise ValueError('Unexpected native-target ambiguity; preserve full build evidence.')
    return candidates


def query_native_targets(rows, root, evidence):
    output = root / 'compile-evidence/native-targets'; output.mkdir(mode=0o700)
    for number, row in enumerate(rows):
        candidates = native_target_candidates(row['path'], root, evidence)
        for choice, candidate in enumerate(candidates):
            path = output / (str(number) + '-' + str(choice) + '-query.txt')
            argv = ['ninja', '-n', '-C', candidate['buildDirectory'], '-t', 'query', candidate['target']]
            with path.open('xb') as stream:
                result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, timeout=30)
            if result.returncode:
                raise RuntimeError('Native target query failed; retain partial attribution evidence.')
            candidate.update(queryArgv=argv, querySha256=sha(path), queryPath=str(path))
        row['ninjaTargetCandidates'] = candidates
        row['targetAttributionComplete'] = False
        row['unresolvedReason'] = 'Candidate targets require object/link/generated-input and notice review.' if candidates else 'No exact native-target basename found; manual finite attribution required.'


def builder():
    inputs = Path('/inputs'); root = Path('/work/marked-runtime-build')
    if os.getuid() != 1001 or os.environ.get('USER') != 'augmentor-proof' or not Path('/.dockerenv').is_file():
        raise ValueError('Use only the separately provisioned private Docker builder.')
    if sha(inputs / 'build-package-versions.txt') != INVENTORY or os.environ.get('CMAKE_EXPORT_COMPILE_COMMANDS') != 'ON':
        raise ValueError('Compiler inventory or instrumentation differs.')
    if any(path.name == '__pycache__' or path.suffix == '.pyc' for path in inputs.rglob('*')):
        raise ValueError('Unbound bytecode caches in build controls refused.')
    for name, expected in TOOLS.items():
        checked(inputs, name, expected)
    original = checked(inputs, 'build-linux-lgpl-runtime.py', TOOLS['build-linux-lgpl-runtime.py']).read_bytes()
    control = checked(inputs, 'marked-builder.py')
    if control.read_bytes() != derived_builder(original, sha(Path(__file__))) or root.exists():
        raise ValueError('Changed derived control or existing build: no resume.')
    result = subprocess.run([sys.executable, '-B', str(control), '--root', str(root)], check=False)
    if result.returncode:
        raise RuntimeError('Marked build failed; retain all partial outputs. No downstream stage.')
    build = json.loads((root / 'build.json').read_text())
    if not build['runtimeBuilt'] or build['dependencyInventorySha256'] != INVENTORY:
        raise ValueError('Build receipt is incomplete or uses a different compiler inventory.')
    evidence = collect_build_evidence(root)
    stage = load_tool(inputs, 'stage-source-qt-runtime.py').stage(root / 'qt-prefix', root / 'qt-runtime')
    derive = load_tool(inputs, 'derive-source-pyside-wheel.py')
    producer = list((root / 'sources').rglob(derive.PRODUCER))
    if len(producer) != 1:
        raise ValueError('Missing or ambiguous actual new PySide producer wheel.')
    producer_hash = sha(producer[0]); derive.read_verified(producer[0], producer_hash)
    wheels = root / 'derived-wheels'; wheels.mkdir(mode=0o700)
    derived = wheels / derive.PRODUCER.replace('-6.8.2-cp37', '-6.8.2augmentormarked1-cp37')
    # Explicit new producer audit; frozen CLI REVIEWED_PRODUCERS remains exact.
    derivation = derive.derive(producer[0], derived, producer_hash)
    pyside_files, _, _ = derive.read_verified(derived, sha(derived))
    shiboken = list((root / 'sources').rglob('shiboken6-6.8.2.1-6.8.2-cp37-abi3-manylinux_2_39_x86_64.whl'))
    if len(shiboken) != 1:
        raise ValueError('Missing or ambiguous actual shiboken wheel.')
    shiboken_files, _, _ = derive.read_verified(shiboken[0], sha(shiboken[0]))
    notices = load_tool(inputs, 'collect-source-qt-notices.py').collect(inputs / 'linux-lgpl-runtime-sources.json', inputs, root / 'original-notices')
    rows = [{'family': 'qt', **row} for row in stage['files'] if 'dynamic' in row]
    for family, files in (('pyside', pyside_files), ('shiboken', shiboken_files)):
        rows += [{'family': family, 'path': name, 'bytes': len(pair[1]), 'sha256': digest(pair[1])}
                 for name, pair in files.items() if pair[1][:4] == b'\x7fELF']
    if [sum(row['family'] == name for row in rows) for name in ('qt', 'pyside', 'shiboken')] != [57, 13, 2]:
        raise ValueError('Native scope differs from finite72 ELF map.')
    # A bounded review queue, never a claim that a basename/notice collection is
    # complete corresponding-source attribution. Whole graphs/objects retained.
    for row in rows:
        row.update(objectLinkSourceMap=None, generatedInputMap=None, applicableOriginalNotices=None,
                   attributionStatus='unresolved', compilationEvidence=str(root / 'compile-evidence/index.json'))
    query_native_targets(rows, root, evidence)
    new_json(root / 'compiled-members.json', {'members': rows, 'compiledFileNoticeMappingComplete': False})
    new_json(root / 'marked-build-result.json', {
        'format': 'augmentor-marked-recipient-build-result/1', 'toolSha256': sha(Path(__file__)),
        'buildReportSha256': sha(root / 'build.json'), 'markedSourcesSha256': sha(root / 'marked-sources.json'),
        'producerSha256': producer_hash, 'derivation': derivation, 'shibokenProducerSha256': sha(shiboken[0]),
        'frozenToolHashes': TOOLS, 'ninjaBuilds': len(evidence), 'nativeMembers': 72,
        'buildEnvironment': dict(sorted(os.environ.items())),
        'originalNoticeFiles': len(notices['files']), 'runtimeBuilt': True,
        'wholeSourceObjectsGeneratedInputsRetained': True, 'compiledFileNoticeMappingComplete': False,
        'recipientReplacementTested': False, 'normalEntrypointsTested': False,
        'licenseReviewComplete': False, 'publicReleaseQualified': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    prepare_parser = sub.add_parser('prepare')
    for name in ('kit', 'plan-directory', 'destination', 'socket-path'):
        prepare_parser.add_argument('--' + name, type=Path, required=True)
    sub.add_parser('builder')
    args = parser.parse_args()
    if args.command == 'builder':
        builder()
    else:
        prepare(args.kit, args.plan_directory, args.destination, args.socket_path)


if __name__ == '__main__':
    main()
