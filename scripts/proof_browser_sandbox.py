#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Renderer sandbox evidence for the isolated Chromium qualification profile."""
import argparse
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

KEYS = ('suid', 'userNs', 'pidNs', 'netNs', 'seccompBpf', 'seccompTsync', 'sandboxGood')
DISABLED = ('--no-sandbox', '--disable-setuid-sandbox', '--disable-namespace-sandbox',
            '--disable-seccomp-filter-sandbox')


def display_environment(environment, platform):
    """Keep fixture runtime sockets private while using the observed compositor."""
    assert platform in ('x11', 'wayland'), 'Unsupported qualification Ozone platform'
    env = dict(environment)
    report = {'requestedPlatform': platform, 'xDisplayRemoved': False}
    if platform == 'wayland':
        assert env.get('XDG_SESSION_TYPE') == 'wayland'
        runtime = Path(env['XDG_RUNTIME_DIR'])
        assert runtime.is_absolute() and not runtime.is_symlink()
        state = runtime.stat()
        assert stat.S_ISDIR(state.st_mode) and state.st_uid == os.getuid() and not state.st_mode & 0o077
        name = Path(env['WAYLAND_DISPLAY'])
        socket = name if name.is_absolute() else runtime / name
        assert socket.parent == runtime and not socket.is_symlink()
        state = socket.stat()
        assert stat.S_ISSOCK(state.st_mode) and state.st_uid == os.getuid()
        # wl_display_connect accepts an absolute socket path, independently of
        # the fixture's subsequently isolated XDG_RUNTIME_DIR.
        env['WAYLAND_DISPLAY'] = str(socket)
        env.pop('DISPLAY', None)
        env.pop('XAUTHORITY', None)
        report.update(waylandSocket=str(socket), socketUid=state.st_uid,
                      socketInode=state.st_ino, xDisplayRemoved=True)
    return env, report


def command_arguments(data):
    args = [arg for arg in data.split(b'\0') if arg]
    if len(args) == 1 and b' ' in args[0]:
        # Chromium SetProcessTitleFromCommandLine joins argv with spaces, then
        # setproctitle replaces the kernel-visible argv with that single title.
        # Tokens corroborate controlled fixture flags; they are not a lossless
        # reconstruction of arbitrary arguments containing spaces.
        return args[0].split(), 'chromium-process-title-tokens'
    return args, 'nul-separated-argv'


def process(pid):
    root = Path('/proc') / str(pid)
    fields = dict(line.split(':', 1) for line in (root / 'status').read_text().splitlines() if ':' in line)
    result = {'pid': pid, 'uid': [int(n) for n in fields['Uid'].split()],
              'ppid': int(fields['PPid']), 'seccomp': int(fields['Seccomp']),
              'noNewPrivs': int(fields['NoNewPrivs']),
              'nspid': [int(n) for n in fields.get('NSpid', '').split()], 'namespaces': {}}
    for kind in ('user', 'pid', 'net'):
        try:
            result['namespaces'][kind] = os.readlink(root / 'ns' / kind)
        except OSError as error:
            result['namespaces'][kind] = {'error': type(error).__name__}
    args, source = command_arguments((root / 'cmdline').read_bytes())
    result['argumentEvidenceSource'] = source
    result['rendererArgument'] = b'--type=renderer' in args
    result['disabledSandboxArguments'] = [flag for flag in DISABLED if flag.encode() in args]
    return result, args


def collect(browser_pid, renderer_pids, profile, expected_uid):
    profile = profile.resolve(strict=True)
    assert not any(c.isspace() for c in str(profile))
    assert profile.name == 'profile' and profile.parent.name.startswith('augmentor-browser-proof-')
    assert profile.stat().st_uid == expected_uid and profile.parent.stat().st_uid == expected_uid
    assert 0 < expected_uid and 0 < len(renderer_pids) <= 64
    browser, args = process(browser_pid)
    assert browser['uid'] == [expected_uid] * 4 and not browser['rendererArgument']
    assert ('--user-data-dir=' + str(profile)).encode() in args
    assert not browser['disabledSandboxArguments']
    renderers = []
    for pid in sorted(set(renderer_pids)):
        renderer, _ = process(pid)
        assert renderer['uid'] == [expected_uid] * 4 and renderer['rendererArgument']
        assert not renderer['disabledSandboxArguments']
        # Read only descendants of this fixture browser; never inspect arbitrary
        # owner processes supplied in a PID list.
        parent = renderer['ppid']; ancestors = []
        while parent != browser_pid:
            assert parent > 1 and parent not in ancestors and len(ancestors) < 16
            ancestors.append(parent)
            ancestor, _ = process(parent)
            assert ancestor['uid'] == [expected_uid] * 4
            parent = ancestor['ppid']
        renderer['browserDescendantVerified'] = True
        renderers.append(renderer)
    return {'browser': browser, 'renderers': renderers, 'expectedUid': expected_uid,
            'rootReadOnlyCollector': os.geteuid() == 0}


def verify(report):
    assert report['chromiumExpectedRendererSandbox']['sandboxGood'] is True
    expected = report['chromiumExpectedRendererSandbox']
    assert (expected['suid'] or expected['userNs']) and expected['pidNs'] and expected['netNs'] and expected['seccompBpf']
    browser = report['processes']['browser']
    assert not browser['disabledSandboxArguments']
    for renderer in report['processes']['renderers']:
        assert renderer['browserDescendantVerified'] and renderer['seccomp'] == 2 and renderer['noNewPrivs'] == 1
        for kind in ('pid', 'net'):
            actual = renderer['namespaces'][kind]; baseline = browser['namespaces'][kind]
            assert isinstance(actual, str) and isinstance(baseline, str) and actual != baseline
    assert report['processes']['renderers']
    return report


def prove(cdp, evaluate, browser_pid, profile, privileged=False):
    assert sys.platform == 'linux' and os.geteuid() != 0
    target = cdp('Target.createTarget', {'url': 'chrome://sandbox/'})['targetId']
    session = cdp('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
    try:
        expression = "(async()=>{const {loadTimeData:d}=await import('chrome://resources/js/load_time_data.js');return Object.fromEntries(" + json.dumps(KEYS) + ".map(k=>[k,d.getBoolean(k)]))})()"
        expected = None
        for _ in range(50):
            try:
                expected = evaluate(expression, session)
                if expected is not None:
                    break
            except AssertionError:
                pass
            time.sleep(.1)
        assert expected is not None, 'Chromium did not expose its sandbox diagnostics'
        pids = [int(p['id']) for p in cdp('SystemInfo.getProcessInfo')['processInfo'] if p['type'] == 'renderer']
        if privileged:
            argv = ['sudo', '-n', sys.executable, '-B', str(Path(__file__).resolve()),
                    '--browser', str(browser_pid), '--profile', str(profile),
                    '--uid', str(os.getuid()), '--renderers', json.dumps(pids)]
            processes = json.loads(subprocess.check_output(argv, text=True, timeout=20))
        else:
            processes = collect(browser_pid, pids, profile, os.getuid())
        report = {'chromiumExpectedRendererSandbox': expected, 'processes': processes,
                  'scope': 'Chromium expected renderer status plus actual fixture renderer seccomp, no-new-privileges and distinct PID/network namespaces; no device or permission acceptance.'}
        # Retain failed evidence too; sandbox flags alone cannot qualify a run.
        (profile.parent / 'sandbox-evidence.json').write_text(json.dumps(report, indent=2) + '\n')
        return verify(report)
    finally:
        cdp('Target.closeTarget', {'targetId': target})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', type=int, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--uid', type=int, required=True)
    parser.add_argument('--renderers', required=True)
    args = parser.parse_args()
    if os.geteuid() == 0:
        # Privileged /proc reads are permitted only in these owned test VMs,
        # called by their ordinary fixture user. No writes or process signals.
        marker = Path('/etc/augmentor-test-vm').read_text()
        assert marker in ('Isolated Augmentor openSUSE Leap 16.0 GNOME qualification VM\n',
                          'Isolated Augmentor Ubuntu 24.04 GNOME qualification VM\n',
                          'Isolated Augmentor Linux Mint 22.3 Cinnamon ISO qualification VM\n')
        assert subprocess.check_output(['systemd-detect-virt'], text=True).strip() == 'qemu'
        assert int(os.environ['SUDO_UID']) == args.uid > 0
    else:
        assert os.getuid() == args.uid
    print(json.dumps(collect(args.browser, json.loads(args.renderers), args.profile, args.uid)))


if __name__ == '__main__':
    main()
