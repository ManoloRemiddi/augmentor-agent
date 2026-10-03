#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Temporary password fixture for the marked Ubuntu GNOME VM only.

Root records stay private. Normal password tools change only the synthetic
account; interrupted dispatches are inspected, never repeated. This helper
does not lock/unlock a desktop or establish authentication acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import time

USER = 'augmentor-proof'
HOME = Path('/home/augmentor-proof')
STORE = Path('/root/augmentor-gnome-password-fixtures')
SHADOW = Path('/etc/shadow')


def account_rows(raw):
    rows = raw.decode().splitlines(keepends=True)
    own = [n for n, row in enumerate(rows) if row.startswith(USER+':')]
    if len(own) != 1 or not rows[own[0]].endswith('\n'):
        raise ValueError('The synthetic account row is not unique and complete.')
    fields = rows[own[0]].rstrip('\n').split(':')
    if len(fields) != 9:
        raise ValueError('The synthetic shadow row format differs.')
    return rows, own[0], fields


def changed_account(raw, password_hash, day):
    rows, index, fields = account_rows(raw)
    fields[1:3] = [password_hash, day]
    rows[index] = ':'.join(fields)+'\n'
    return ''.join(rows).encode()


def private_read(path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        info = os.fstat(stream.fileno())
        forbidden = 0o022 if path == SHADOW else 0o077
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or
                info.st_nlink != 1 or info.st_mode & forbidden or info.st_size > 1024*1024):
            raise ValueError('Root-owned fixture data identity differs.')
        return stream.read(1024*1024+1)


def private_write(path, raw):
    temporary = path.with_name(path.name+'.pending')
    with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


def journal(root, record):
    private_write(root/'run.json', (json.dumps(record, indent=2)+'\n').encode())


def dispatch_once(root, record, phase, command, text):
    record['phase'] = phase
    record.setdefault('dispatches', []).append(phase)
    journal(root, record)
    # No exception handler repeats a native password command. The retained
    # expected shadow images allow a later read-only outcome classification.
    subprocess.run(command, input=text, text=True, capture_output=True, check=True, timeout=20)


def guard(source, artifact):
    if os.geteuid() != 0 or not re.fullmatch('[a-f0-9]{40}', source) or not re.fullmatch('[a-f0-9]{64}', artifact):
        raise ValueError('Use root inside the explicitly marked fixture and exact artifact identities.')
    marker = Path('/etc/augmentor-test-vm'); info = marker.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022 or
            marker.read_text() != 'Isolated Augmentor Ubuntu 24.04 GNOME qualification VM\n'):
        raise ValueError('This helper is restricted to the owned Ubuntu GNOME fixture.')
    os_info = dict(row.split('=', 1) for row in Path('/etc/os-release').read_text().splitlines() if '=' in row)
    if os_info['ID'].strip('"') != 'ubuntu' or os_info['VERSION_ID'].strip('"') != '24.04':
        raise ValueError('The fixture distro differs.')
    for command, expected in ((['hostname'], 'augmentor-gnome-ubuntu24-mesa2'), (['systemd-detect-virt'], 'qemu')):
        if subprocess.check_output(command, text=True, timeout=15).strip() != expected:
            raise ValueError('The fixture host/virtualization identity differs.')
    user = pwd.getpwnam(USER)
    if user.pw_uid != 1000 or user.pw_dir != str(HOME):
        raise ValueError('The dedicated synthetic account differs.')
    selection = HOME/'.local/share/augmentor/desktop.json'; info = selection.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 1000 or info.st_nlink != 1 or info.st_mode & 0o077:
        raise ValueError('The fixture selection identity differs.')
    selected = json.loads(selection.read_bytes())
    if selected.get('sourceRef') != source or selected.get('artifactSha256') != artifact:
        raise ValueError('The explicitly bound selected artifact differs.')
    return hashlib.sha256(selection.read_bytes()).hexdigest()


def preparation_plan(request):
    if not isinstance(request, dict):raise ValueError('The private request must be an object.')
    before = private_read(SHADOW); fields = account_rows(before)[2]
    if fields[1] != request.get('expectedOriginalPasswordHash'):
        raise ValueError('The original random Cloud fixture password hash differs; it was preserved.')
    password = request.get('syntheticPassword', '')
    if not isinstance(password, str) or not re.fullmatch('[a-z0-9]{24}', password):
        raise ValueError('Use a fresh bounded synthetic credential.')
    result = subprocess.run(['/usr/bin/openssl', 'passwd', '-6', '-stdin'], input=password+'\n',
                            capture_output=True, text=True, timeout=15, check=True)
    password_hash = result.stdout.strip()
    if not re.fullmatch(r'\$6\$[^:\n]+', password_hash):
        raise ValueError('The synthetic password hash format differs.')
    day = str(int(time.time()//86400))
    after = changed_account(before, password_hash, day)
    intermediate = changed_account(before, fields[1], day)
    return before, after, intermediate, password, fields[2], password_hash


def prepare(root, record, plan):
    before, after, intermediate, password, original_day, password_hash = plan
    if private_read(SHADOW) != before:
        raise ValueError('The account changed after preparation; no password command was dispatched.')
    for name, raw in (('before.shadow', before), ('after.shadow', after), ('intermediate.shadow', intermediate)):
        private_write(root/name, raw)
    private_write(root/'synthetic-password', password.encode())
    record['originalDay'] = original_day
    dispatch_once(root, record, 'prepare-pending', ['/usr/sbin/chpasswd', '-e'], USER+':'+password_hash+'\n')
    if private_read(SHADOW) != after:
        raise ValueError('Native password outcome differs; all fixture receipts were retained.')
    record['phase'] = 'installed'; journal(root, record)


def restore(root, record):
    before = private_read(root/'before.shadow'); after = private_read(root/'after.shadow')
    intermediate = private_read(root/'intermediate.shadow'); current = private_read(SHADOW)
    if current == before:
        record['phase'] = 'restored'; journal(root, record)
        (root/'synthetic-password').unlink(missing_ok=True)
        return
    if current == after and record['phase'] in ('installed', 'prepare-pending'):
        original_hash = account_rows(before)[2][1]
        dispatch_once(root, record, 'restore-password-pending', ['/usr/sbin/chpasswd', '-e'], USER+':'+original_hash+'\n')
        current = private_read(SHADOW)
    if current != intermediate or record['phase'] not in ('restore-password-pending', 'restore-age-ready'):
        raise ValueError('Concurrent or uncertain password state was preserved; no command is repeated.')
    # A prior interrupted password restoration is positively observed before
    # the distinct age restoration. An uncertain age dispatch is never repeated.
    record['phase'] = 'restore-age-ready'; journal(root, record)
    day = record['originalDay'] or '-1'
    dispatch_once(root, record, 'restore-age-pending', ['/usr/bin/chage', '-d', day, USER], None)
    if private_read(SHADOW) != before:
        raise ValueError('Original account restoration is not confirmed; retained evidence requires inspection.')
    record['phase'] = 'restored'; journal(root, record)
    (root/'synthetic-password').unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'status', 'restore'))
    parser.add_argument('--run', required=True); parser.add_argument('--source', required=True)
    parser.add_argument('--artifact', required=True); args = parser.parse_args()
    if not re.fullmatch('[a-f0-9]{32}', args.run):raise ValueError('Use an explicit one-run fixture identity.')
    selection_hash = guard(args.source, args.artifact)
    if not STORE.exists():STORE.mkdir(mode=0o700)
    info = STORE.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise ValueError('The root-only fixture store differs.')
    root = STORE/args.run
    if args.operation == 'prepare':
        for entry in STORE.iterdir():
            info = entry.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
                raise ValueError('A prior root-only fixture directory differs; it was preserved.')
            prior = json.loads(private_read(entry/'run.json'))
            if prior.get('phase') != 'restored':raise ValueError('A prior fixture remains pending; it was preserved.')
        import sys
        raw = sys.stdin.buffer.read(4097)
        if len(raw)>4096:raise ValueError('The private credential request exceeds its bound.')
        # Validate and derive before creating a persistent run. Invalid input
        # cannot strand a created journal that has no restoration images.
        plan = preparation_plan(json.loads(raw))
        root.mkdir(mode=0o700)  # Existing and interrupted runs are never adopted.
        record = {'format':'augmentor-owned-gnome-password-fixture/1', 'run':args.run,
                  'source':args.source, 'artifact':args.artifact, 'selectionHash':selection_hash,
                  'phase':'created', 'dispatches':[]}
        journal(root, record)
        prepare(root, record, plan)
    else:
        info = root.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
            raise ValueError('The root-only run directory differs.')
        record = json.loads(private_read(root/'run.json'))
        if any(record.get(key) != value for key,value in
               (('run',args.run), ('source',args.source), ('artifact',args.artifact), ('selectionHash',selection_hash))):
            raise ValueError('The retained fixture belongs to another run or selection.')
        if args.operation == 'restore':restore(root, record)
    print(json.dumps({'phase':record['phase'], 'run':args.run,
                      'credentialContentReturned':False, 'passwordAuthenticationTested':False}))


if __name__ == '__main__':main()
