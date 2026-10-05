#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Preserve offline Linux test guests and manage private libvirt session domains.

Never repairs, commits into, or boots an imported source disk. Checkpoints are
standalone qcow2 images; each working generation has its own overlay and NVRAM.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET

GIB = 1024 ** 3
URI = 'qemu:///session'
PREFIX = 'augmentor-lab-'
SYS_BLOCK_DEVICES = Path('/sys/dev/block')


def run(args, *, timeout=120, allowed=(0,)):
    result = subprocess.run([str(arg) for arg in args], capture_output=True,
                            text=True, timeout=timeout, env={**os.environ, 'LC_ALL': 'C'})
    if result.returncode not in allowed:
        raise ValueError(f'{args[0]} exited {result.returncode}: {result.stderr.strip()}')
    return result


def virsh(*args, **kwargs):
    return run(['virsh', '--connect', URI, *args], **kwargs)


def token(value):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', value):
        raise ValueError('Use a short lowercase name containing letters, digits and hyphens.')
    return value


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    with temporary.open('x', encoding='utf-8') as stream:
        os.chmod(temporary, 0o600)
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    sync_directory(path.parent)


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def sync_file(path):
    with Path(path).open('rb') as stream:
        os.fsync(stream.fileno())


def copy_verified(source, destination, mode=0o600):
    source = regular(source)
    before = identity(source)
    digest = sha(source)
    shutil.copy2(source, destination)
    os.chmod(destination, mode)
    sync_file(destination)
    sync_directory(Path(destination).parent)
    if identity(source) != before or sha(destination) != digest:
        raise ValueError('A copied launch asset differs or its source changed.')


def operation_record(folder, action, phase, value):
    """Retain every operation receipt; a last-value file is only a convenience."""
    journal = folder / 'events'
    journal.mkdir(mode=0o700, exist_ok=True)
    filename = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex + '-' + action + '-' + phase + '.json'
    write_json(journal / filename, value)
    sync_directory(folder)
    write_json(folder / ('last-' + action + '-' + phase + '.json'), value)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def identity(path):
    stat = Path(path).stat()
    return [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns,
            stat.st_ctime_ns, stat.st_mode, stat.st_uid]


def regular(path):
    path = Path(path).absolute()
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Expected an existing regular file: {path}')
    return path


def block_device_leaves(device, sysfs_root=SYS_BLOCK_DEVICES):
    """Resolve a filesystem device number to its physical block-device leaves."""
    entry = Path(sysfs_root) / f'{os.major(device)}:{os.minor(device)}'
    try:
        node = entry.resolve(strict=True)
    except OSError as error:
        raise ValueError('Cannot prove which physical device stores this path.') from error

    def leaves(current, active):
        current = current.resolve(strict=True)
        key = str(current)
        if key in active:
            raise ValueError('The physical storage device graph contains a cycle.')
        dev_file = current / 'dev'
        if not dev_file.is_file():
            raise ValueError('Cannot prove which physical device stores this path.')
        active = {*active, key}
        slaves = current / 'slaves'
        if slaves.is_dir():
            rows = list(slaves.iterdir())
            if rows:
                result = set()
                for slave in rows:
                    result.update(leaves(slave, active))
                return result
        if (current / 'partition').exists():
            parent = current.parent
            if not (parent / 'dev').is_file():
                raise ValueError('Cannot resolve a partition to its physical device.')
            return leaves(parent, active)
        return {dev_file.read_text().strip()}

    result = leaves(node, set())
    if not result or any(not re.fullmatch(r'\d+:\d+', item) for item in result):
        raise ValueError('Cannot prove which physical device stores this path.')
    return frozenset(result)


def physical_devices(path):
    device = Path(path).stat().st_dev
    return block_device_leaves(device)


def image_chain(path):
    data = json.loads(run(['qemu-img', 'info', '--backing-chain', '--output=json',
                          regular(path)]).stdout)
    if not data or any(item['format'] != 'qcow2' for item in data):
        raise ValueError('Only explicit qcow2 disk chains are supported.')
    return [regular(item['filename']) for item in data]


def check_image(path):
    # No -r and no -U: preserve faults and respect the image write lock.
    result = run(['qemu-img', 'check', '--output=json', '-f', 'qcow2', path],
                 timeout=900, allowed=(0, 1, 2, 3, 63))
    return {'exitCode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}


def available_memory():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1]) * 1024
    raise ValueError('Host memory availability is unknown.')


def resource_admission(memory_mib, available, root_free, data_free, running):
    if running:
        raise ValueError('Another lab VM is active. The default is one VM at a time.')
    required = memory_mib * 1024 ** 2 + 8 * GIB + GIB
    if available < required:
        raise ValueError('Insufficient available RAM for this guest plus the 8 GiB host reserve and 1 GiB overhead.')
    if root_free < 4 * GIB or data_free < 20 * GIB:
        raise ValueError('Keep at least 4 GiB free on the host root and 20 GiB on lab storage.')


def domain_xml(spec, generation):
    root = ET.Element('domain', {'type': 'qemu'})  # Preserve TCG; KVM is a separate qualification.
    def add(parent, tag, text=None, **attrs):
        node = ET.SubElement(parent, tag, attrs)
        node.text = str(text) if text is not None else None
        return node
    add(root, 'name', PREFIX + spec['name'])
    add(root, 'uuid', spec['uuid'])
    add(root, 'description', spec.get('description', 'Private Augmentor Linux test guest'))
    add(root, 'memory', spec['memoryMiB'], unit='MiB')
    add(root, 'currentMemory', spec['memoryMiB'], unit='MiB')
    add(root, 'vcpu', spec['cpus'], placement='static')
    # libvirt's unprivileged session driver rejects memtune at start. Admission
    # reserves host headroom; it is not a cgroup hard limit on later host load.
    system = add(root, 'os')
    add(system, 'type', 'hvm', arch='x86_64', machine='pc-q35-10.0')
    if spec.get('firmwareCode'):
        add(system, 'loader', spec['firmwareCode'], readonly='yes', type='pflash')
        add(system, 'nvram', str(generation / 'nvram.fd'))
    add(system, 'boot', dev='hd')
    features = add(root, 'features')
    add(features, 'acpi'); add(features, 'apic')
    if spec['cpuModel'] == 'max':
        add(root, 'cpu', mode='maximum', migratable='on')
    else:
        cpu = add(root, 'cpu', mode='custom', match='exact', check='full')
        add(cpu, 'model', spec['cpuModel'], fallback='forbid')
        add(cpu, 'feature', policy='require', name='hypervisor')
    add(root, 'on_poweroff', 'destroy')
    add(root, 'on_reboot', 'restart')
    # A crash must not automatically repeat an action with an unknown outcome.
    add(root, 'on_crash', 'preserve')
    devices = add(root, 'devices')
    add(devices, 'emulator', '/usr/bin/qemu-system-x86_64')
    disk = add(devices, 'disk', type='file', device='disk')
    add(disk, 'driver', name='qemu', type='qcow2', cache='writethrough', error_policy='stop')
    add(disk, 'source', file=str(generation / 'disk.qcow2'))
    add(disk, 'target', dev='vda', bus='virtio')
    if spec.get('seed'):
        cd = add(devices, 'disk', type='file', device='cdrom')
        add(cd, 'driver', name='qemu', type='raw')
        add(cd, 'source', file=spec['seed'])
        add(cd, 'target', dev='sda', bus='sata'); add(cd, 'readonly')
    network = add(devices, 'interface', type='user')
    add(network, 'mac', address=spec.get('mac', '52:54:00:12:34:56'))
    add(network, 'model', type='virtio')
    add(network, 'backend', type='passt')
    add(network, 'ip', family='ipv4', address='10.0.2.15', prefix='24')
    forward = add(network, 'portForward', proto='tcp', address='127.0.0.1')
    add(forward, 'range', start=str(spec['sshPort']), to='22')
    add(devices, 'controller', type='usb', model='qemu-xhci')
    add(devices, 'input', type='tablet', bus='usb')
    video = add(devices, 'video'); add(video, 'model', type='virtio', primary='yes')
    add(devices, 'graphics', type='vnc', autoport='yes', listen='127.0.0.1')
    serial = add(devices, 'serial', type='file')
    add(serial, 'source', path=str(generation / 'serial.log'))
    add(serial, 'target', port='0')
    ET.indent(root)
    return ET.tostring(root, encoding='unicode') + '\n'


def domain_contract(xml):
    """Compare owned paths/devices without libvirt-generated PCI addresses."""
    root = ET.fromstring(xml)
    if root.findall('./devices/hostdev') or root.findall('./devices/filesystem') or any('commandline' in n.tag for n in root):
        raise ValueError('Host attachments or additional QEMU commands are not allowed.')
    def text(path):
        node = root.find(path)
        return node.text.strip() if node is not None and node.text else None
    def attrs(path, names):
        node = root.find(path)
        return {key: node.get(key) for key in names} if node is not None else None
    memory = root.find('memory')
    units = {'KiB': 1024, 'MiB': 1024 ** 2, 'GiB': GIB}
    return {'type': root.get('type'), 'name': text('name'), 'uuid': text('uuid'),
            'memoryBytes': int(memory.text) * units[memory.get('unit', 'KiB')],
            'cpus': text('vcpu'), 'cpuMode': attrs('cpu', ['mode']), 'cpuModel': text('cpu/model'),
            'cpuFeatures': sorted((n.get('name'), n.get('policy')) for n in root.findall('cpu/feature')),
            'os': attrs('os/type', ['arch', 'machine']), 'loader': text('os/loader'),
            'loaderMode': attrs('os/loader', ['readonly', 'type']), 'nvram': text('os/nvram'),
            'emulator': text('devices/emulator'),
            'disks': [{'device': disk.get('device'), 'type': disk.get('type'),
                       'source': disk.find('source').get('file'),
                       'driver': {key: disk.find('driver').get(key) for key in ['type', 'cache', 'error_policy']},
                       'bus': disk.find('target').get('bus'), 'readonly': disk.find('readonly') is not None}
                      for disk in root.findall('devices/disk')],
            'interfaces': [{'type': interface.get('type'),
                            'forwards': [{'attributes': dict(forward.attrib),
                                          'ranges': [dict(n.attrib) for n in forward.findall('range')]}
                                         for forward in interface.findall('portForward')],
                            'backend': dict(interface.find('backend').attrib),
                            'mac': dict(interface.find('mac').attrib),
                            'model': dict(interface.find('model').attrib),
                            'ip': [dict(n.attrib) for n in interface.findall('ip')]}
                           for interface in root.findall('devices/interface')],
            'graphics': [{key: node.get(key) for key in ['type', 'autoport', 'listen']}
                         for node in root.findall('devices/graphics')],
            'serial': [node.find('source').get('path') for node in root.findall('devices/serial')],
            'poweroff': text('on_poweroff'), 'reboot': text('on_reboot'), 'crash': text('on_crash')}


class Lab:
    def __init__(self, directory):
        self.root = Path(directory).absolute()
        if self.root.is_symlink():
            raise ValueError('The lab directory must not be a symlink.')
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.root.stat().st_uid != os.getuid() or self.root.stat().st_mode & 0o077:
            raise ValueError('Lab storage must belong to this user and have mode 0700.')

    @contextlib.contextmanager
    def locked(self):
        with (self.root / '.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def entry(self, name):
        folder = self.root / token(name)
        if (folder / 'pending-generation.json').exists():
            raise ValueError('An interrupted generation transition needs review; no lifecycle action was performed.')
        return folder, json.loads((folder / 'machine.json').read_text())

    def validate_domain(self, spec):
        actual = virsh('dumpxml', '--inactive', PREFIX + spec['name']).stdout
        expected = domain_xml(spec, Path(spec['currentGeneration']))
        if domain_contract(actual) != domain_contract(expected):
            raise ValueError('Persistent domain definition differs from the private lab catalog. No action was performed.')

    def verify_generation(self, folder, spec):
        disk = Path(spec['currentGeneration']) / 'disk.qcow2'
        baseline = folder / 'checkpoints' / token(spec['checkpoint'])
        manifest = json.loads((baseline / 'checkpoint.json').read_text())
        if image_chain(disk) != [disk, baseline / 'base.qcow2'] or sha(baseline / 'base.qcow2') != manifest['sha256']:
            raise ValueError('The working disk backing chain or immutable checkpoint hash differs.')
        if spec.get('firmwareCode') and sha(baseline / 'nvram.fd') != manifest['nvramSha256']:
            raise ValueError('The checkpoint firmware variables differ.')
        if any(sha(path) != digest for path, digest in spec['assetSha256'].items()):
            raise ValueError('An imported launch asset changed.')
        return {str(p): check_image(p) for p in image_chain(disk)}

    def inactive(self, spec):
        state = virsh('domstate', PREFIX + spec['name']).stdout.strip()
        if state != 'shut off':
            raise ValueError(f'The guest must be shut off; actual state: {state}')

    def no_saved_memory(self, spec):
        result = virsh('managedsave-dumpxml', PREFIX + spec['name'], allowed=(0, 1))
        if result.returncode == 0:
            raise ValueError('Saved guest memory exists. Resume and shut down normally before changing disks.')
        if 'does not have managed save' not in result.stderr.lower():
            raise ValueError('Could not establish absence of saved guest memory: ' + result.stderr.strip())

    def checkpoint_disk(self, source, destination):
        chain = image_chain(source)
        before = {str(path): identity(path) for path in chain}
        checks = {str(path): check_image(path) for path in chain}
        write_json(destination / 'source-checks.json', checks)
        if any(row['exitCode'] != 0 for row in checks.values()):
            raise ValueError('A source disk check failed; originals are preserved. Repair only a separate copy after review.')
        size = json.loads(run(['qemu-img', 'info', '--output=json', source]).stdout)['virtual-size']
        if shutil.disk_usage(destination).free < size + 20 * GIB:
            raise ValueError('Insufficient space for a conservative full checkpoint plus 20 GiB reserve.')
        target = destination / 'base.qcow2'
        if target.exists():
            raise ValueError('Checkpoint output already exists; use a fresh label.')
        run(['qemu-img', 'convert', '-f', 'qcow2', '-O', 'qcow2', '-o',
             'compat=1.1,lazy_refcounts=off', source, target], timeout=3600)
        run(['qemu-img', 'compare', '-f', 'qcow2', '-F', 'qcow2', source, target], timeout=3600)
        result = check_image(target)
        if result['exitCode'] != 0:
            raise ValueError('The new checkpoint did not pass its offline consistency check.')
        if image_chain(target) != [target] or before != {str(p): identity(p) for p in chain}:
            raise ValueError('Unexpected backing dependency or source mutation.')
        os.chmod(target, 0o400)
        sync_file(target)
        write_json(destination / 'checkpoint.json', {
            'format': 'augmentor-test-lab-checkpoint/1', 'source': str(source),
            'sourceChainIdentity': before, 'logicalDiskComparePassed': True,
            'standalone': True, 'sha256': sha(target), 'imageCheck': result,
            'guestFilesystemRecoveryTested': False,
            'createdUTC': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})

    def define_generation(self, folder, spec, checkpoint):
        baseline = folder / 'checkpoints' / token(checkpoint)
        if sha(baseline / 'base.qcow2') != json.loads((baseline / 'checkpoint.json').read_text())['sha256']:
            raise ValueError('Checkpoint hash differs.')
        generation = folder / 'runs' / (time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:8])
        generation.mkdir(parents=True, mode=0o700)
        sync_directory(folder); sync_directory(generation.parent)
        run(['qemu-img', 'create', '-f', 'qcow2', '-F', 'qcow2', '-b',
             baseline / 'base.qcow2', '-o', 'lazy_refcounts=off', generation / 'disk.qcow2'])
        if spec.get('firmwareCode'):
            manifest = json.loads((baseline / 'checkpoint.json').read_text())
            if sha(baseline / 'nvram.fd') != manifest['nvramSha256']:
                raise ValueError('Checkpoint firmware variables differ.')
            copy_verified(baseline / 'nvram.fd', generation / 'nvram.fd')
        xml = generation / 'domain.xml'
        xml.write_text(domain_xml(spec, generation))
        os.chmod(xml, 0o600)
        sync_file(xml); sync_file(generation / 'disk.qcow2')
        sync_directory(generation); sync_directory(generation.parent)
        prepared = {**spec, 'currentGeneration': str(generation), 'checkpoint': checkpoint}
        write_json(folder / 'pending-generation.json', prepared)
        # Schema/driver validation and persistent registration; no VM is started.
        virsh('define', '--validate', xml)
        virsh('autostart', '--disable', PREFIX + spec['name'])
        spec.update(prepared)
        self.validate_domain(spec)
        write_json(folder / 'machine.json', spec)
        (folder / 'pending-generation.json').unlink()
        sync_directory(folder)
        return {'name': spec['name'], 'domain': PREFIX + spec['name'],
                'checkpoint': checkpoint, 'generation': str(generation), 'started': False}

    def import_machine(self, source_spec, label):
        spec = dict(source_spec)
        token(spec['name']); token(label)
        if not 1024 <= spec['sshPort'] <= 65535 or not 1024 <= spec['memoryMiB'] <= 32768 or not 1 <= spec['cpus'] <= 16:
            raise ValueError('Invalid port, memory or CPU count.')
        for existing in self.root.glob('*/machine.json'):
            if json.loads(existing.read_text())['sshPort'] == spec['sshPort']:
                raise ValueError('SSH forwarding port already belongs to another lab guest.')
        if PREFIX + spec['name'] in virsh('list', '--all', '--name').stdout.splitlines():
            raise ValueError('A domain with this name already exists; it was not replaced.')
        folder = self.root / spec['name']
        folder.mkdir(mode=0o700)  # Partial/refused imports are preserved, not overwritten.
        sync_directory(self.root)
        baseline = folder / 'checkpoints' / label
        baseline.mkdir(parents=True, mode=0o700)
        sync_directory(folder); sync_directory(baseline.parent)
        spec['uuid'] = str(uuid.uuid4())
        spec['originalSourceDisk'] = str(regular(spec.pop('disk')))
        self.checkpoint_disk(spec['originalSourceDisk'], baseline)
        assets = folder / 'assets'; assets.mkdir(mode=0o700)
        for field, filename in [('seed', 'seed.iso'), ('sshKey', 'id_ed25519'), ('knownHosts', 'known_hosts'),
                                ('loginSecret', 'test-login-secret'),
                                ('firmwareCode', 'firmware-code.fd')]:
            if spec.get(field):
                copy_verified(spec[field], assets / filename)
                spec[field] = str(assets / filename)
        if spec.get('firmwareCode'):
            copy_verified(spec.pop('firmwareVars'), baseline / 'nvram.fd', 0o400)
            manifest = json.loads((baseline / 'checkpoint.json').read_text())
            write_json(baseline / 'checkpoint.json', {**manifest, 'nvramSha256': sha(baseline / 'nvram.fd')})
        spec['assetSha256'] = {str(path): sha(path) for path in assets.iterdir()}
        write_json(folder / 'machine.json', spec)
        return self.define_generation(folder, spec, label)

    def check(self, name):
        folder, spec = self.entry(name); self.inactive(spec); self.validate_domain(spec)
        checks = self.verify_generation(folder, spec)
        result = {'name': name, 'passed': all(row['exitCode'] == 0 for row in checks.values()), 'checks': checks}
        write_json(folder / 'last-check.json', result)
        return result

    def start(self, name):
        folder, spec = self.entry(name); self.inactive(spec); self.validate_domain(spec); self.no_saved_memory(spec)
        active = virsh('list', '--name').stdout.splitlines()
        resource_admission(spec['memoryMiB'], available_memory(), shutil.disk_usage('/').free,
                           shutil.disk_usage(self.root).free, [x for x in active if x.startswith(PREFIX)])
        if not self.check(name)['passed']:
            raise ValueError('Disk consistency check failed. No boot or automatic repair was attempted.')
        # Hashing a large checkpoint can take time; repeat admission at dispatch.
        self.inactive(spec); self.validate_domain(spec); self.no_saved_memory(spec)
        active = virsh('list', '--name').stdout.splitlines()
        resource_admission(spec['memoryMiB'], available_memory(), shutil.disk_usage('/').free,
                           shutil.disk_usage(self.root).free, [x for x in active if x.startswith(PREFIX)])
        operation_record(folder, 'start', 'intent', {'name': name, 'outcome': 'unknown-until-observed',
                   'hostBootId': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                   'toolSha256': sha(Path(__file__)),
                   'automaticTestReplay': False, 'generation': spec['currentGeneration']})
        virsh('start', PREFIX + name, timeout=120)
        result = {'name': name, 'state': virsh('domstate', PREFIX + name).stdout.strip(),
                  'desktopAcceptanceTested': False}
        operation_record(folder, 'start', 'outcome', result)
        return result

    def shutdown(self, name, wait):
        folder, spec = self.entry(name); self.validate_domain(spec)
        if virsh('domstate', PREFIX + name).stdout.strip() == 'shut off':
            return {'name': name, 'state': 'shut off', 'alreadyStopped': True}
        method = spec.get('shutdownMethod', 'acpi')
        if method not in ('acpi', 'ssh'):
            raise ValueError('Unsupported configured shutdown method.')
        if method == 'ssh':
            if not re.fullmatch(r'[a-z_][a-z0-9_-]*', spec['guestUser']) or not re.fullmatch(r'\[127\.0\.0\.1\]:[0-9]+', spec['sshHostKeyAlias']):
                raise ValueError('Invalid owned guest SSH identity.')
            if any(sha(path) != digest for path, digest in spec['assetSha256'].items()):
                raise ValueError('An imported SSH asset differs.')
            command = ['ssh', '-p', str(spec['sshPort']), '-i', spec['sshKey'],
                       '-o', 'UserKnownHostsFile=' + spec['knownHosts'],
                       '-o', 'HostKeyAlias=' + spec['sshHostKeyAlias'],
                       '-o', 'StrictHostKeyChecking=yes', '-o', 'IdentitiesOnly=yes',
                       '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
                       spec['guestUser'] + '@127.0.0.1', 'sudo', '-n', 'systemctl', 'poweroff']
            operation_record(folder, 'shutdown', 'intent', {'method': 'normal-guest-systemctl-via-ssh',
                       'outcome': 'unknown-until-observed', 'forced': False})
            # Disconnect can accompany successful poweroff. Observe libvirt rather
            # than repeat a request or fall back to another shutdown method.
            result = run(command, timeout=30, allowed=(0, 1, 255))
            operation_record(folder, 'shutdown', 'dispatch', {'exitCode': result.returncode,
                       'stdout': result.stdout, 'stderr': result.stderr, 'automaticFallback': False})
            if result.returncode == 1:
                raise ValueError('The normal guest shutdown command refused. No retry, fallback or forced stop was sent.')
        else:
            operation_record(folder, 'shutdown', 'intent', {'method': 'acpi', 'forced': False,
                             'outcome': 'unknown-until-observed'})
            virsh('shutdown', PREFIX + name, '--mode', 'acpi')
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            if virsh('domstate', PREFIX + name).stdout.strip() == 'shut off':
                result = {'name': name, 'state': 'shut off', 'forced': False}
                operation_record(folder, 'shutdown', 'outcome', result)
                return result
            time.sleep(1)
        raise ValueError('Normal shutdown did not finish; no forced stop was sent. Do not reboot the host yet.')

    def checkpoint(self, name, label):
        folder, spec = self.entry(name); self.inactive(spec); self.validate_domain(spec); self.no_saved_memory(spec)
        if any(row['exitCode'] != 0 for row in self.verify_generation(folder, spec).values()):
            raise ValueError('Working generation failed its disk checks.')
        destination = folder / 'checkpoints' / token(label)
        destination.mkdir(mode=0o700)
        sync_directory(destination.parent)
        self.checkpoint_disk(Path(spec['currentGeneration']) / 'disk.qcow2', destination)
        if spec.get('firmwareCode'):
            copy_verified(Path(spec['currentGeneration']) / 'nvram.fd', destination / 'nvram.fd', 0o400)
            manifest = json.loads((destination / 'checkpoint.json').read_text())
            write_json(destination / 'checkpoint.json', {**manifest, 'nvramSha256': sha(destination / 'nvram.fd')})
        return {'name': name, 'checkpoint': label, 'selectedGenerationUnchanged': True}

    def reset(self, name, label):
        folder, spec = self.entry(name); self.inactive(spec); self.validate_domain(spec); self.no_saved_memory(spec)
        return self.define_generation(folder, spec, label)

    def reconcile(self, name):
        """Finish an interrupted registration only when its prepared files match."""
        folder = self.root / token(name)
        pending = folder / 'pending-generation.json'
        spec = json.loads(regular(pending).read_text())
        if spec['name'] != name:
            raise ValueError('Pending machine name differs.')
        domain = PREFIX + name
        exists = domain in virsh('list', '--all', '--name').stdout.splitlines()
        if exists:
            self.inactive(spec); self.no_saved_memory(spec)
            actual = domain_contract(virsh('dumpxml', '--inactive', domain).stdout)
            prepared = domain_contract(domain_xml(spec, Path(spec['currentGeneration'])))
            if actual != prepared:
                committed = json.loads((folder / 'machine.json').read_text())
                if not committed.get('currentGeneration') or actual != domain_contract(domain_xml(committed, Path(committed['currentGeneration']))):
                    raise ValueError('Neither the committed nor prepared domain matches; manual review is required.')
                # Exact old generation is the only existing definition we may replace.
                exists = False
        checks = self.verify_generation(folder, spec)
        if any(row['exitCode'] != 0 for row in checks.values()):
            raise ValueError('Prepared generation failed its disk checks.')
        if not exists:
            virsh('define', '--validate', Path(spec['currentGeneration']) / 'domain.xml')
            self.validate_domain(spec)
        virsh('autostart', '--disable', domain)
        write_json(folder / 'machine.json', spec)
        pending.rename(folder / ('completed-transition-' + uuid.uuid4().hex + '.json'))
        sync_directory(folder)
        return {'name': name, 'reconciled': True, 'started': False}

    def backup(self, name, destination):
        folder, spec = self.entry(name); self.inactive(spec); self.validate_domain(spec); self.no_saved_memory(spec)
        if any(row['exitCode'] != 0 for row in self.verify_generation(folder, spec).values()):
            raise ValueError('Working generation failed its disk checks.')
        destination = Path(destination).absolute()
        ancestor = destination
        while not ancestor.exists():
            parent = ancestor.parent
            if parent == ancestor:
                raise ValueError('Backup destination has no existing parent directory.')
            ancestor = parent
        if not ancestor.is_dir():
            raise ValueError('Backup destination parent must be a directory.')
        lab_devices = physical_devices(self.root)
        if physical_devices(ancestor) & lab_devices:
            raise ValueError('Choose storage on a different physical device for an independent backup.')
        destination.mkdir(parents=True, mode=0o700, exist_ok=True)
        if physical_devices(destination) & lab_devices:
            raise ValueError('Backup destination resolves to the lab physical device.')
        output = destination / (name + '-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
        output.mkdir(mode=0o700)
        sync_directory(destination)
        self.checkpoint_disk(Path(spec['currentGeneration']) / 'disk.qcow2', output)
        exported = {key: spec[key] for key in ['name', 'description', 'memoryMiB', 'cpus', 'cpuModel', 'sshPort',
                                             'guestUser', 'sshHostKeyAlias', 'shutdownMethod', 'mac'] if key in spec}
        exported['disk'] = str(output / 'base.qcow2')
        if spec.get('firmwareCode'):
            copy_verified(Path(spec['currentGeneration']) / 'nvram.fd', output / 'nvram.fd', 0o400)
            exported['firmwareVars'] = str(output / 'nvram.fd')
        for field in ['firmwareCode', 'seed', 'sshKey', 'knownHosts', 'loginSecret']:
            if spec.get(field):
                target = output / Path(spec[field]).name
                copy_verified(spec[field], target)
                exported[field] = str(target)
        write_json(output / 'import-spec.json', exported)
        write_json(output / 'backup-files.json', {p.name: sha(p) for p in output.iterdir() if p.is_file()})
        return {'name': name, 'backup': str(output), 'independentDevice': True}

    def status(self):
        rows = []
        for path in sorted(self.root.glob('*/machine.json')):
            spec = json.loads(path.read_text())
            state = virsh('domstate', PREFIX + spec['name'], allowed=(0, 1))
            rows.append({'name': spec['name'], 'domain': PREFIX + spec['name'],
                         'state': state.stdout.strip() if state.returncode == 0 else 'not-defined',
                         'memoryMiB': spec['memoryMiB'], 'sshPort': spec['sshPort'],
                         'checkpoint': spec.get('checkpoint'),
                         'transitionPending': (path.parent / 'pending-generation.json').exists()})
        return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    imported = sub.add_parser('import'); imported.add_argument('--spec', type=Path, required=True)
    imported.add_argument('--label', required=True)
    sub.add_parser('status')
    for action in ('check', 'start', 'shutdown', 'checkpoint', 'reset', 'reconcile', 'backup'):
        command = sub.add_parser(action); command.add_argument('name')
        if action in ('checkpoint', 'reset'): command.add_argument('--label', required=True)
        if action == 'shutdown': command.add_argument('--wait', type=int, default=180)
        if action == 'backup': command.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    if os.getuid() == 0:
        parser.error('Use your ordinary account and its private libvirt session.')
    lab = Lab(args.directory)
    try:
        with lab.locked():
            if args.action == 'import': result = lab.import_machine(json.loads(args.spec.read_text()), args.label)
            elif args.action == 'status': result = lab.status()
            elif args.action == 'check': result = lab.check(args.name)
            elif args.action == 'start': result = lab.start(args.name)
            elif args.action == 'shutdown': result = lab.shutdown(args.name, args.wait)
            elif args.action == 'checkpoint': result = lab.checkpoint(args.name, args.label)
            elif args.action == 'reset': result = lab.reset(args.name, args.label)
            elif args.action == 'reconcile': result = lab.reconcile(args.name)
            elif args.action == 'backup': result = lab.backup(args.name, args.destination)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, subprocess.TimeoutExpired, KeyError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
