# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned Fedora synthetic exporter owner-loss proof with its process kept alive.

Real native daemon/registry/helper, synthetic two-node accessibility tree. No GTK,
UI events, input, text queries, service restarts or selected application changes.
Only this probe's private exporter connection closes/reconnects. A new ordinary
user candidate directory containing the helper/service is required.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT_PATH = '/org/a11y/atspi/accessible/root'
ENTRY_PATH = '/org/a11y/atspi/accessible/entry'


def save(path, value):
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    with temporary.open('x') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')
    temporary.replace(path)


def exporter(root):
    import gi
    gi.require_version('Atspi', '2.0')
    from gi.repository import Atspi, Gio, GLib
    accessible_xml = '''<node><interface name="org.a11y.atspi.Accessible">
    <property name="ChildCount" type="i" access="read"/>
    <property name="Parent" type="(so)" access="read"/>
    <property name="Name" type="s" access="read"/>
    <property name="Description" type="s" access="read"/>
    <property name="Locale" type="s" access="read"/>
    <property name="AccessibleId" type="s" access="read"/>
    <property name="HelpText" type="s" access="read"/>
    <property name="version" type="u" access="read"/>
    <method name="GetChildAtIndex"><arg type="i" direction="in"/><arg type="(so)" direction="out"/></method>
    <method name="GetChildren"><arg type="a(so)" direction="out"/></method>
    <method name="GetRole"><arg type="u" direction="out"/></method>
    <method name="GetState"><arg type="au" direction="out"/></method>
    <method name="GetInterfaces"><arg type="as" direction="out"/></method>
    <method name="GetApplication"><arg type="(so)" direction="out"/></method>
    <method name="GetIndexInParent"><arg type="i" direction="out"/></method>
    <method name="GetAttributes"><arg type="a{ss}" direction="out"/></method>
    <method name="GetRelationSet"><arg type="a(ua(so))" direction="out"/></method>
    </interface></node>'''
    application_xml = '''<node><interface name="org.a11y.atspi.Application">
    <property name="Id" type="i" access="readwrite"/>
    <property name="ToolkitName" type="s" access="read"/>
    <property name="ToolkitVersion" type="s" access="read"/>
    <property name="Version" type="s" access="read"/>
    <property name="AtspiVersion" type="s" access="read"/>
    <property name="InterfaceVersion" type="u" access="read"/>
    <method name="GetApplicationBusAddress"><arg type="s" direction="out"/></method>
    <method name="GetLocale"><arg type="u" direction="in"/><arg type="s" direction="out"/></method>
    </interface></node>'''
    flags = Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION
    def connect(address):
        bus = Gio.DBusConnection.new_for_address_sync(address, flags, None, None)
        bus.set_exit_on_close(False); return bus
    def call(bus, name, path, interface, method, signature=None, arguments=()):
        return bus.call_sync(name, path, interface, method,
            GLib.Variant(signature, arguments) if signature else None, None,
            Gio.DBusCallFlags.NO_AUTO_START, 1000, None).unpack()[0]
    def daemon(bus, method, name=None):
        return call(bus, 'org.freedesktop.DBus', '/org/freedesktop/DBus',
            'org.freedesktop.DBus', method, '(s)' if name else None, (name,) if name else ())
    session = connect(Gio.dbus_address_get_for_bus_sync(Gio.BusType.SESSION, None))
    launcher = daemon(session, 'GetNameOwner', 'org.a11y.Bus')
    address = call(session, launcher, '/org/a11y/bus', 'org.a11y.Bus', 'GetAddress')
    state = {'pid': os.getpid(), 'generation': 0, 'connectionOpen': False, 'applicationId': 0,
        'sessionBusId': daemon(session, 'GetId'), 'launcherOwner': launcher,
        'inputSent': False, 'gtkTarget': False, 'treeSynthetic': True}
    bus = None; owner = None; parent = ('', '/org/a11y/atspi/null')
    def get_property(_bus, _sender, path, interface, name):
        if interface.endswith('.Application'):
            values = {'Id': ('i', state['applicationId']), 'ToolkitName': ('s', 'owned-synthetic-exporter'),
                'ToolkitVersion': ('s', '1'), 'Version': ('s', '1'), 'AtspiVersion': ('s', '2.1'), 'InterfaceVersion': ('u', 1)}
        else:
            values = {'ChildCount': ('i', 1 if path == ROOT_PATH else 0),
                'Parent': ('(so)', parent if path == ROOT_PATH else (owner, ROOT_PATH)),
                **{key: ('s', '') for key in ('Name', 'Description', 'AccessibleId', 'HelpText')},
                'Locale': ('s', 'C'), 'version': ('u', 1)}
        signature, value = values[name]; return GLib.Variant(signature, value)
    def set_property(_bus, _sender, _path, interface, name, value):
        if interface.endswith('.Application') and name == 'Id':
            state['applicationId'] = value.unpack(); return True
        return False
    def method(_bus, _sender, path, interface, name, parameters, invocation):
        children = [(owner, ENTRY_PATH)] if path == ROOT_PATH else []
        if interface.endswith('.Application'):
            signature, answer = '(s)', ('',) if name == 'GetApplicationBusAddress' else ('C',)
        elif name == 'GetState':
            states = [Atspi.StateType.SHOWING, Atspi.StateType.VISIBLE, Atspi.StateType.ENABLED, Atspi.StateType.SENSITIVE]
            if path == ENTRY_PATH: states += [Atspi.StateType.FOCUSED, Atspi.StateType.EDITABLE]
            words = [0, 0]
            for item in states:
                bit = int(item); words[bit // 32] |= 1 << (bit % 32)
            signature, answer = '(au)', (words,)
        elif name == 'GetChildAtIndex':
            index = parameters.unpack()[0]
            if not 0 <= index < len(children):
                invocation.return_dbus_error('org.a11y.atspi.Error.InvalidIndex', 'Synthetic child index outside tree.'); return
            signature, answer = '((so))', (children[index],)
        else:
            values = {'GetChildren': ('(a(so))', (children,)),
                'GetRole': ('(u)', (int(Atspi.Role.APPLICATION if path == ROOT_PATH else Atspi.Role.ENTRY),)),
                'GetInterfaces': ('(as)', (['org.a11y.atspi.Accessible'] + (['org.a11y.atspi.Application'] if path == ROOT_PATH else []),)),
                'GetApplication': ('((so))', ((owner, ROOT_PATH),)), 'GetIndexInParent': ('(i)', (0,)),
                'GetAttributes': ('(a{ss})', ({},)), 'GetRelationSet': ('(a(ua(so)))', ([],))}
            signature, answer = values[name]
        invocation.return_value(GLib.Variant(signature, answer))
    def arm():
        nonlocal bus, owner, parent
        bus = connect(address); owner = bus.get_unique_name()
        registry = daemon(bus, 'GetNameOwner', 'org.a11y.atspi.Registry')
        state.update(accessibilityBusId=daemon(bus, 'GetId'), registryOwner=registry, owner=owner)
        for name in (launcher,):
            if daemon(session, 'GetConnectionUnixUser', name) != os.getuid(): raise RuntimeError('Different session native user.')
        if daemon(bus, 'GetConnectionUnixUser', registry) != os.getuid(): raise RuntimeError('Different registry native user.')
        for path in (ROOT_PATH, ENTRY_PATH):
            bus.register_object(path, Gio.DBusNodeInfo.new_for_xml(accessible_xml).interfaces[0], method, get_property, None)
        bus.register_object(ROOT_PATH, Gio.DBusNodeInfo.new_for_xml(application_xml).interfaces[0], method, get_property, set_property)
        parent = call(bus, registry, ROOT_PATH, 'org.a11y.atspi.Socket', 'Embed', '((so))', ((owner, ROOT_PATH),))
        state['generation'] += 1; state['connectionOpen'] = True
        save(root / 'owner-exporter-state.json', state)
    arm(); loop = GLib.MainLoop()
    def command():
        path = root / 'owner-exporter-command.json'
        if not path.exists(): return True
        if path.is_symlink() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077 or path.stat().st_size > 4096:
            raise RuntimeError('Invalid owned exporter command.')
        value = json.loads(path.read_text()); path.unlink(); operation = value['operation']
        if operation == 'close' and state['connectionOpen']:
            bus.close_sync(None); state['connectionOpen'] = False
        elif operation == 'reconnect' and not state['connectionOpen']: arm()
        elif operation == 'ping': pass
        elif operation == 'exit': loop.quit()
        else: raise RuntimeError('Invalid exporter lifecycle command.')
        state['lastCommand'] = value['nonce']; save(root / 'owner-exporter-state.json', state); return True
    GLib.timeout_add(50, command)
    try: loop.run()
    finally:
        if state['connectionOpen']: bus.close_sync(None)
        session.close_sync(None)


def parent(root, selected_source):
    sys.path.insert(0, str(root))
    from a11y_helper import AccessibilityHelper, process_start
    selection = Path.home() / '.local/share/augmentor/desktop.json'; original = selection.read_bytes()
    if json.loads(original)['sourceRef'] != selected_source: raise RuntimeError('Different selected application.')
    for name in ('owner-exporter-state.json', 'owner-exporter-command.json', 'owner-exporter.stderr', 'owner-loss-result.json'):
        path = root / name
        if path.exists() or path.is_symlink(): raise ValueError('Preserve prior owner proof; use a fresh candidate.')
    with (root / 'owner-exporter.stderr').open('xb') as errors:
        process = subprocess.Popen([sys.executable, '-I', str(Path(__file__)), '--candidate', root.name, '--exporter'],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=errors)
    target_start = process_start(process.pid); helper = None; fresh = None
    report = {'format': 'augmentor-gnome-native-selected-owner-loss/1', 'parentPid': os.getpid(),
        'targetPid': process.pid, 'targetStart': target_start, 'records': [], 'inputSent': False,
        'treeSynthetic': True, 'gtkTarget': False, 'selectedSource': selected_source,
        'sourceSha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__), root / 'a11y_helper.py', root / 'a11y_service.py')},
        'liveProcessOwnerLossQualified': False, 'fullProductInputQualified': False}
    def alive():
        if process.poll() is not None or process_start(process.pid) != target_start: raise RuntimeError('Owned exporter process identity changed.')
    def wait_state(predicate):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            alive(); path = root / 'owner-exporter-state.json'
            if path.exists():
                value = json.loads(path.read_text())
                if value.get('pid') != process.pid: raise RuntimeError('Different exporter acknowledgment identity.')
                if predicate(value): return value
            time.sleep(.05)
        raise RuntimeError('Exporter acknowledgment deadline.')
    def command(operation):
        nonce = uuid.uuid4().hex; save(root / 'owner-exporter-command.json', {'operation': operation, 'nonce': nonce})
        return wait_state(lambda value: value.get('lastCommand') == nonce)
    def focus(instance):
        for attempt in range(4):
            started = time.monotonic(); reply = instance.request('focus', generation=len(report['records']))
            report['records'].append({'operation': 'focus', 'reply': reply, 'durationSeconds': time.monotonic() - started})
            if reply['complete']: return reply
            time.sleep(.3)
        raise RuntimeError('Synthetic native tree discovery incomplete.')
    try:
        before = wait_state(lambda value: value['connectionOpen']); report['before'] = before
        helper = AccessibilityHelper(process.pid); initial = focus(helper)
        if initial['selectedOwner'] != before['owner']: raise RuntimeError('Selected synthetic owner mismatch.')
        closed = command('close'); alive(); report['afterDisconnect'] = closed
        started = time.monotonic()
        try: helper.request('status')
        except RuntimeError as error:
            report['ownerLossRefusal'] = {'kind': type(error).__name__, 'message': str(error),
                'durationSeconds': time.monotonic() - started, 'helperClosed': helper.closed}
            if 'native owner changed' not in str(error) or not helper.closed: raise
        else: raise RuntimeError('Lost selected owner unexpectedly accepted.')
        report['processAliveAfterOwnerLoss'] = True; report['supervisorPing'] = command('ping'); alive()
        reconnected = command('reconnect'); report['afterReconnect'] = reconnected
        if reconnected['owner'] == before['owner']: raise RuntimeError('Exporter failed to acquire a new unique owner.')
        for key in ('sessionBusId', 'launcherOwner', 'accessibilityBusId', 'registryOwner'):
            if before[key] != reconnected[key]: raise RuntimeError('Global native service identity changed.')
        try: helper.request('focus')
        except RuntimeError as error:
            if str(error) != 'Accessibility helper is closed.': raise
            report['oldHelperRearmRefused'] = True
        else: raise RuntimeError('Retired helper unexpectedly rearmed.')
        fresh = AccessibilityHelper(process.pid); reply = focus(fresh)
        if reply['selectedOwner'] != reconnected['owner']: raise RuntimeError('Fresh helper failed to pin new owner.')
        alive(); report['processAliveAfterReconnect'] = True
        report['liveProcessOwnerLossQualified'] = True
    except Exception as error:
        report['failure'] = {'kind': type(error).__name__, 'message': str(error)}; raise
    finally:
        if helper: helper.close()
        if fresh: fresh.close()
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=1)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=1)
        report['ownedProcessesDisposed'] = process.poll() is not None and (not helper or helper.closed) and (not fresh or fresh.closed)
        report['selectedApplicationChanged'] = selection.read_bytes() != original
        report['parentAtspiImported'] = 'gi.repository.Atspi' in sys.modules
        save(root / 'owner-loss-result.json', report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True); parser.add_argument('--source')
    parser.add_argument('--exporter', action='store_true'); args = parser.parse_args()
    if (os.getuid() != 1000 or os.environ.get('USER') != 'augmentor-proof'
            or Path('/etc/augmentor-test-vm').read_text() != 'Isolated Augmentor Fedora GNOME qualification VM\n'
            or subprocess.check_output(['systemd-detect-virt'], text=True).strip() != 'qemu'
            or subprocess.check_output(['getenforce'], text=True).strip() != 'Enforcing'):
        raise RuntimeError('Use only the owned normal-user Fedora QEMU fixture.')
    if not args.candidate.startswith('gnome-execution-probe-') or '/' in args.candidate or '..' in args.candidate:
        raise ValueError('Invalid private candidate name.')
    root = Path.home() / args.candidate
    if not root.is_dir() or root.is_symlink() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise ValueError('Use an existing owner-only candidate root.')
    os.umask(0o077)
    env = dict(row.split('=', 1) for row in subprocess.check_output(['systemctl', '--user', 'show-environment'], text=True).splitlines() if '=' in row)
    if env['XDG_CURRENT_DESKTOP'] != 'GNOME' or env['XDG_SESSION_TYPE'] != 'wayland': raise RuntimeError('Different native desktop.')
    os.environ.update({key: value for key, value in env.items() if key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS', 'XDG_CURRENT_DESKTOP', 'XDG_SESSION_TYPE')})
    if args.exporter: exporter(root)
    else:
        if not args.source or (root / 'owner-loss-result.json').exists(): raise ValueError('Require exact selected source and a fresh candidate.')
        parent(root, args.source)


if __name__ == '__main__':
    main()
