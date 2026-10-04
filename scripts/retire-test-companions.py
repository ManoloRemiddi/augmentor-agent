#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Linux compatibility watchdog for abandoned fixtures from older checkouts.

Production companions retire themselves. This deliberately narrow fallback only
observes known disposable test namespaces; it never deletes files or kills a
process tree. Run once without --apply to preview eligible process counts.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import time

SUFFIXES=('/services/memory/service.py','/services/prompt-library/service.py','/services/dictation/server.py')
PREFIXES=('augmentor-pi-contract-','augmentor-offscreen-dictation-','augmentor-update-', 'codex-voice-')


def snapshot():
    rows=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            if path.stat().st_uid!=os.getuid():continue
            fields=(path/'stat').read_text().rsplit(')',1)[1].split()
            if fields[0]=='Z':continue
            args=(path/'cmdline').read_bytes().split(b'\0')
            env=dict(item.split('=',1) for item in (path/'environ').read_text().split('\0') if '=' in item)
            service=next((arg.decode() for arg in args if arg.endswith(tuple(x.encode() for x in SUFFIXES))),None)
            rows.append({'pid':int(path.name),'start':fields[19],'ppid':int(fields[1]),'env':env,'service':service})
        except (OSError,ValueError):continue
    return rows


def isolated(base):
    path=Path(base)
    return (path.is_absolute() and path.parent==Path('/tmp') and path.name.startswith(PREFIXES)) or (
        path.is_absolute() and len(path.parts)>3 and path.parts[1]=='tmp' and path.parts[2].startswith(PREFIXES))


def eligible(row, rows):
    if not row['service']:return False
    env=row['env'];dictation='/dictation/' in row['service']
    key='AUGMENTOR_DICTATION_STATE' if dictation else 'AUGMENTOR_SHARED_STATE'
    base=env.get(key) or (env.get('HOME','')+'/.local/share/augmentor/dictation' if dictation else '')
    if not isolated(base):return False
    try:
        path=Path('/proc')/str(row['pid'])
        if os.readlink(path/'ns/mnt')!=os.readlink('/proc/self/ns/mnt'):return False
        for peer in rows:
            if peer['ppid']==row['pid']:return False
            if peer['pid']==row['pid'] or peer['service']:continue
            if peer['env'].get(key)==base:return False
            if dictation and not env.get(key) and peer['env'].get('HOME')==env.get('HOME'):return False
        if dictation:
            preferences=Path(base)/'preferences.json'
            if preferences.exists() and json.loads(preferences.read_text()).get('enabled'):return False
        elif '/memory/' in row['service']:
            data=env.get('AUGMENTOR_SHARED_DATA')
            # Do not infer that configured inference has completed from sockets.
            if not data or (Path(data)/'hindsight.json').exists():return False
        sockets={line.split()[6]:int(line.split()[3],16) for line in (path/'net/unix').read_text().splitlines()[1:] if len(line.split())>=7}
        count=0
        for descriptor in (path/'fd').iterdir():
            target=os.readlink(descriptor)
            if target.startswith('socket:['):
                count+=1
                if not sockets.get(target[8:-1],0)&0x10000:return False
        return count==1
    except (OSError,ValueError):return False


def advance(rows, previous, now, *, idle_seconds=600):
    observations={};ready=[]
    for row in rows:
        if not eligible(row,rows):continue
        identity=str(row['pid'])+':'+row['start']
        since=previous.get(identity,now)
        observations[identity]=since
        if now-since>=idle_seconds:ready.append(row)
    return observations,ready


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if not Path('/proc/self/stat').exists():parser.error('This compatibility watchdog requires Linux /proc.')
    folder=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'augmentor/companion-watchdog'
    os.umask(0o077);folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    # Serialize observations/signals from manual and timer invocations.
    import fcntl
    with (folder/'watch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        record=folder/'observations.json'
        try:previous=json.loads(record.read_text())
        except (FileNotFoundError,ValueError):previous={}
        observed,ready=advance(snapshot(),previous,time.monotonic())
        # monotonic timestamps must never survive a reboot as old evidence.
        boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        try:old_boot=(folder/'boot-id').read_text()
        except FileNotFoundError:old_boot=None
        if old_boot!=boot:observed,ready=advance(snapshot(),{},time.monotonic())
        signalled=0
        if args.apply:
            fresh=snapshot();by_pid={row['pid']:row for row in fresh}
            for row in ready:
                current=by_pid.get(row['pid'])
                if not current or current['start']!=row['start'] or not eligible(current,fresh):continue
                # pidfd binds the signal to this process even if its PID is reused.
                try:
                    descriptor=os.pidfd_open(row['pid'])
                    try:
                        fields=(Path('/proc')/str(row['pid'])/'stat').read_text().rsplit(')',1)[1].split()
                        if fields[19]!=row['start']:continue
                        signal.pidfd_send_signal(descriptor,signal.SIGTERM);signalled+=1
                    finally:os.close(descriptor)
                except ProcessLookupError:pass
        temporary=folder/'observations.tmp';temporary.write_text(json.dumps(observed));temporary.replace(record)
        (folder/'boot-id').write_text(boot)
        print(f'Abandoned test candidates: {len(observed)}; idle for ten minutes: {len(ready)}; signalled: {signalled}.')


if __name__=='__main__':main()
