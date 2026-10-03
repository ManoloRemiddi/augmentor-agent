# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Native AT-SPI service fences in a separate owned Fedora container/session.

Each case uses a private dbus-run-session/runtime directory and native Fedora
launcher/registry. Synthetic exporter tree; no GNOME compositor, application,
input, host mounts/devices, shared buses or owner services. Do not infer live
GNOME service restart or product input acceptance from these isolated cases.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

MARKER = 'Owned Augmentor Fedora native accessibility service fixture; no application installation\n'
NATIVE = {'/usr/libexec/at-spi-bus-launcher': '9c14ce427c18c5dcfa303db57d22b6277deb48bb154e385b8cceb572fd309c24',
          '/usr/libexec/at-spi2-registryd': 'fba13406b5e8ebe67c6eea1aa99f61d2b67a2620ba01bac74ce2772261dd9324'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def proof_module():
    path = Path(__file__).with_name('probe-gnome-a11y-owner.py')
    spec = importlib.util.spec_from_file_location('owned_exporter', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def run_inside(root, case):
    from gi.repository import Gio, GLib
    sys.path.insert(0, str(Path(__file__).parent))
    from a11y_helper import AccessibilityHelper, process_start
    owned = proof_module(); processes = []; helpers = []; bus_pid = None; bus_start = None
    report = {'format': 'augmentor-isolated-native-a11y-service-fence/1', 'case': case,
        'treeSynthetic': True, 'realGnomeSession': False, 'inputSent': False,
        'nativeServiceFenceQualified': False, 'sourceSha256': {p.name: digest(p) for p in
            (Path(__file__), Path(__file__).with_name('probe-gnome-a11y-owner.py'),
             Path(__file__).with_name('a11y_helper.py'), Path(__file__).with_name('a11y_service.py'))},
        'nativeBinarySha256': NATIVE, 'parentAtspiImported': False, 'events': []}
    def spawn(argv, label, env=None):
        with (root / (label + '.log')).open('xb') as log:
            process = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        start = process_start(process.pid); processes.append((process, start, label))
        report['events'].append({'operation': 'spawn', 'label': label, 'pid': process.pid, 'start': start, 'argv': argv}); return process
    def alive(process):
        row = next(r for r in processes if r[0] is process)
        if process.poll() is not None or process_start(process.pid) != row[1]: raise RuntimeError('Owned native process identity changed.')
    def stop(process):
        if process.poll() is not None: return
        alive(process); process.terminate()
        try: process.wait(timeout=1)
        except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=1)
    flags = Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION
    def connection(address):
        bus = Gio.DBusConnection.new_for_address_sync(address, flags, None, None); bus.set_exit_on_close(False); return bus
    def call(bus, name, path, interface, method, signature=None, arguments=()):
        return bus.call_sync(name, path, interface, method, GLib.Variant(signature, arguments) if signature else None,
            None, Gio.DBusCallFlags.NO_AUTO_START, 500, None).unpack()[0]
    def daemon(bus, method, name=None):
        return call(bus, 'org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus', method,
            '(s)' if name else None, (name,) if name else ())
    def await_owner(bus, name, process):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            alive(process)
            try:
                owner = daemon(bus, 'GetNameOwner', name)
                if daemon(bus, 'GetConnectionUnixProcessID', owner) != process.pid: raise RuntimeError('Different native daemon owns name.')
                return owner
            except GLib.Error: time.sleep(.05)
        raise RuntimeError('Native service readiness deadline.')
    session = connection(os.environ['DBUS_SESSION_BUS_ADDRESS']); a11y = None
    def start_services(suffix):
        nonlocal a11y, bus_pid, bus_start
        launcher = spawn(['/usr/libexec/at-spi-bus-launcher', '--launch-immediately', '--a11y=1', '--screen-reader=0'], 'launcher-' + suffix)
        launcher_owner = await_owner(session, 'org.a11y.Bus', launcher)
        address = call(session, launcher_owner, '/org/a11y/bus', 'org.a11y.Bus', 'GetAddress')
        a11y = connection(address); bus_pid = daemon(a11y, 'GetConnectionUnixProcessID', 'org.freedesktop.DBus'); bus_start = process_start(bus_pid)
        stat = (Path('/proc') / str(bus_pid) / 'stat').read_text().rsplit(')', 1)[1].split()
        if int(stat[1]) != launcher.pid or Path('/proc', str(bus_pid), 'exe').resolve() != Path('/usr/bin/dbus-daemon'):
            raise RuntimeError('Accessibility bus is not the owned native launcher child.')
        env = dict(os.environ, AT_SPI_BUS_ADDRESS=address)
        registry = spawn(['/usr/libexec/at-spi2-registryd'], 'registry-' + suffix, env)
        registry_owner = await_owner(a11y, 'org.a11y.atspi.Registry', registry)
        pins = {'sessionBusId': daemon(session, 'GetId'), 'launcherOwner': launcher_owner,
            'accessibilityBusId': daemon(a11y, 'GetId'), 'registryOwner': registry_owner,
            'accessibilityBusPid': bus_pid, 'accessibilityBusStart': bus_start}
        return launcher, registry, pins
    def exporter(suffix):
        directory = root / ('exporter-' + suffix); directory.mkdir(mode=0o700)
        process = spawn([sys.executable, '-I', str(Path(__file__)), '--exporter', '--root', str(directory), '--case', case], 'exporter-' + suffix)
        def state(predicate):
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                alive(process); path = directory / 'owner-exporter-state.json'
                if path.exists():
                    value = json.loads(path.read_text())
                    if value['pid'] != process.pid: raise RuntimeError('Different exporter reply identity.')
                    if predicate(value): return value
                time.sleep(.05)
            raise RuntimeError('Synthetic exporter readiness deadline.')
        initial = state(lambda r: r['connectionOpen'])
        def command(operation):
            nonce = uuid.uuid4().hex; owned.save(directory / 'owner-exporter-command.json', {'operation': operation, 'nonce': nonce})
            return state(lambda r: r.get('lastCommand') == nonce)
        return process, initial, command
    def helper_focus(target):
        helper = AccessibilityHelper(target.pid); helpers.append(helper)
        for _ in range(4):
            reply = helper.request('focus')
            report['events'].append({'operation': 'focus', 'reply': reply})
            if reply['complete']: return helper, reply
            time.sleep(.3)
        raise RuntimeError('Isolated synthetic tree discovery incomplete.')
    try:
        launcher, registry, before = start_services('first'); report['before'] = before
        target, initial, command = exporter('first'); helper, first = helper_focus(target)
        if first['selectedOwner'] != initial['owner']: raise RuntimeError('Different selected exporter owner.')
        if case == 'registry': stop(registry)
        elif case == 'launcher-bus': stop(launcher)
        else:
            if process_start(bus_pid) != bus_start: raise RuntimeError('Owned bus identity changed.')
            os.kill(bus_pid, signal.SIGTERM)
        alive(target); report['targetAliveImmediatelyAfterLoss'] = True
        started = time.monotonic()
        try: helper.request('status')
        except RuntimeError as error:
            report['refusal'] = {'kind': type(error).__name__, 'message': str(error), 'durationSeconds': time.monotonic() - started, 'helperClosed': helper.closed}
            if 'native owner changed' not in str(error) or not helper.closed: raise
        else: raise RuntimeError('Lost native service unexpectedly accepted.')
        alive(target); report['supervisorPingAfterLoss'] = command('ping')
        try: helper.request('focus')
        except RuntimeError as error:
            if str(error) != 'Accessibility helper is closed.': raise
            report['oldHelperRearmRefused'] = True
        else: raise RuntimeError('Retired helper unexpectedly resumed.')
        if case == 'registry':
            alive(launcher)
            if daemon(a11y, 'GetNameOwner', initial['owner']) != initial['owner']: raise RuntimeError('Target owner changed during registry-only proof.')
            report['selectedOwnerUnchangedDuringRegistryLoss'] = True
            registry = spawn(['/usr/libexec/at-spi2-registryd'], 'registry-second', dict(os.environ, AT_SPI_BUS_ADDRESS=call(session, before['launcherOwner'], '/org/a11y/bus', 'org.a11y.Bus', 'GetAddress')))
            new_registry = await_owner(a11y, 'org.a11y.atspi.Registry', registry)
            if new_registry == before['registryOwner']: raise RuntimeError('Registry owner did not change.')
            command('close'); restored = command('reconnect')
            report['restoredExporter'] = restored; fresh, reply = helper_focus(target)
            if reply['pins']['registryOwner'] != new_registry: raise RuntimeError('Fresh helper failed to pin new registry.')
            for key in ('sessionBusId', 'launcherOwner', 'accessibilityBusId'):
                if reply['pins'][key] != before[key]: raise RuntimeError('Registry-only case changed another native identity.')
        else:
            report['coupledLauncherAndAccessibilityBusLoss'] = True
            stop(registry); stop(launcher); stop(target)
            if a11y and not a11y.is_closed(): a11y.close_sync(None)
            launcher, registry, after = start_services('second'); report['after'] = after
            if after['sessionBusId'] != before['sessionBusId'] or after['launcherOwner'] == before['launcherOwner'] or after['accessibilityBusId'] == before['accessibilityBusId']:
                raise RuntimeError('Fresh native service identities do not reflect coupled replacement.')
            fresh_target, restored, command2 = exporter('second'); fresh, reply = helper_focus(fresh_target)
            if any(reply['pins'][k] != after[k] for k in ('sessionBusId', 'launcherOwner', 'accessibilityBusId', 'registryOwner')):
                raise RuntimeError('Fresh helper failed to pin replacement service set.')
        report['nativeServiceFenceQualified'] = True
    except Exception as error:
        report['failure'] = {'kind': type(error).__name__, 'message': str(error)}; raise
    finally:
        for helper in helpers: helper.close()
        for process, _, _ in reversed(processes): stop(process)
        if a11y and not a11y.is_closed(): a11y.close_sync(None)
        if not session.is_closed(): session.close_sync(None)
        report['ownedPids'] = [{'pid': p.pid, 'start': start, 'label': label, 'exit': p.poll()} for p, start, label in processes]
        report['allOwnedSpawnedProcessesReaped'] = all(p.poll() is not None for p, _, _ in processes)
        report['allHelpersDisposed'] = all(h.closed and h.process.poll() is not None for h in helpers)
        report['parentAtspiImported'] = 'gi.repository.Atspi' in sys.modules
        owned.save(root / 'service-replacement-result.json', report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--case', choices=('registry', 'launcher-bus', 'accessibility-bus'), required=True)
    parser.add_argument('--inside', action='store_true'); parser.add_argument('--exporter', action='store_true'); args = parser.parse_args()
    if (os.getuid() != 1000 or os.environ.get('USER') != 'augmentor-proof' or not Path('/.dockerenv').is_file()
            or Path('/etc/augmentor-a11y-service-fixture').read_text() != MARKER):
        raise RuntimeError('Use only the separate owned Fedora native-service container.')
    for path, checksum in NATIVE.items():
        if digest(path) != checksum: raise RuntimeError('Different native daemon binary.')
    root = args.root
    if not root.is_absolute() or not root.is_relative_to('/work') or '..' in root.parts or root.is_symlink(): raise ValueError('Use a fresh owned /work proof root.')
    os.umask(0o077)
    if args.inside or args.exporter:
        if not root.is_dir() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077: raise ValueError('Invalid private proof root.')
        runtime = Path(os.environ['XDG_RUNTIME_DIR'])
        if not runtime.is_dir() or runtime.stat().st_uid != os.getuid() or runtime.stat().st_mode & 0o077 or runtime.is_symlink(): raise ValueError('Invalid isolated runtime.')
        if any(os.environ.get(key) for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'AT_SPI_BUS_ADDRESS', 'DBUS_STARTER_ADDRESS', 'DBUS_STARTER_BUS_TYPE')):
            raise RuntimeError('Shared desktop environment leaked into isolated proof.')
        if args.exporter: proof_module().exporter(root)
        else: run_inside(root, args.case)
        return
    if root.exists(): raise ValueError('Preserve prior proof; use a new root.')
    root.mkdir(mode=0o700); runtime = Path('/tmp') / ('aa-' + uuid.uuid4().hex[:12]); runtime.mkdir(mode=0o700)
    env = {k: v for k, v in os.environ.items() if k in ('HOME', 'USER', 'LOGNAME', 'PATH', 'LANG', 'LC_ALL')}
    env.update(XDG_RUNTIME_DIR=str(runtime), GSETTINGS_BACKEND='memory', ATSPI_DBUS_IMPLEMENTATION='dbus-daemon')
    with (root / 'wrapper.log').open('xb') as output:
        result = subprocess.run(['dbus-run-session', '--', sys.executable, '-I', str(Path(__file__)),
            '--inside', '--root', str(root), '--case', args.case], env=env, stdout=output, stderr=subprocess.STDOUT, timeout=45)
    if result.returncode: raise RuntimeError('Isolated native-service proof failed; preserve its owned logs.')
    print((root / 'service-replacement-result.json').read_text())


if __name__ == '__main__': main()
