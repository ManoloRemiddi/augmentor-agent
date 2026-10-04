#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Install the Linux compatibility watchdog for this user's old test checkouts."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    if not sys.platform.startswith('linux'):raise SystemExit('This compatibility watchdog is Linux only.')
    os.umask(0o077)
    source=Path(__file__).with_name('retire-test-companions.py')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    data=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))
    script=data/'augmentor/companion-watchdog'/digest/source.name
    script.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    shutil.copy2(source,script)
    config=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'systemd/user'
    config.mkdir(parents=True,exist_ok=True)
    def quote(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"'
    (config/'augmentor-test-companion-watchdog.service').write_text(
        '[Unit]\nDescription=Retire abandoned Augmentor test companions\n\n[Service]\nType=oneshot\n'
        'ExecStart='+quote(sys.executable)+' '+quote(script)+' --apply\n'
        'Nice=10\nTimeoutStartSec=60\n')
    (config/'augmentor-test-companion-watchdog.timer').write_text(
        '[Unit]\nDescription=Bound companion leftovers from older Augmentor tests\n\n[Timer]\n'
        'OnStartupSec=5min\nOnUnitActiveSec=5min\nAccuracySec=30s\n\n[Install]\nWantedBy=timers.target\n')
    subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    subprocess.run(['systemctl','--user','enable','--now','augmentor-test-companion-watchdog.timer'],check=True)
    subprocess.run(['systemctl','--user','start','augmentor-test-companion-watchdog.service'],check=True)
    print('Installed test-only compatibility watchdog; checks every five minutes, requires ten minutes without an observed owner or work.')


if __name__=='__main__':main()
