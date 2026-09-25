#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Install stable Home launchers after selecting a tested desktop artifact."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shlex
import shutil
import tempfile


def install(autostart=True):
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))
    state = Path(os.environ.get('XDG_STATE_HOME', Path.home()/'.local/state'))
    with (data/'augmentor/deployment.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        selected = json.loads((data/'augmentor/desktop.json').read_text())
        root = Path(selected['root'])
        if not (root/'apps/native/augmentor_linux/home_tray.py').is_file():
            raise RuntimeError('Stage and activate a Home-enabled artifact first.')
        launch = data/'augmentor/home-launch.py'
        entry = Path.home()/'.local/bin/augmentor-home'
        # Desktop Exec escaping is separate from shell quoting.
        field = '"'+str(entry).replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')+'"'
        desktop = '[Desktop Entry]\nType=Application\nName=Augmentor Home\nComment=Open your NAS smart-home dashboard\nExec='+field+'\nIcon=go-home\nTerminal=false\nCategories=Utility;\nStartupWMClass=AugmentorHome\n'
        files = {
            launch: (root/'scripts/home-launch.py').read_text(),
            entry: '#!/bin/sh\nexec /usr/bin/python3 '+shlex.quote(str(launch))+' "$@"\n',
            data/'applications/com.augmentor.Home.desktop': desktop,
        }
        if autostart:
            files[config/'autostart/com.augmentor.Home.desktop'] = desktop.replace('Exec='+field, 'Exec='+field+' --background')
        state.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix='augmentor-home-install-', dir=state))
        for index, (path, content) in enumerate(files.items()):
            if path.exists():
                shutil.copy2(path, backup/(str(index)+'-'+path.name))
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix='.'+path.name, dir=path.parent)
            with os.fdopen(fd, 'w') as stream:
                stream.write(content)
            os.chmod(tmp, 0o700 if path == entry else 0o600)
            os.replace(tmp, path)
        print('Home menu entry and login startup installed. Backup: '+str(backup))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-autostart', action='store_true')
    install(not parser.parse_args().no_autostart)
