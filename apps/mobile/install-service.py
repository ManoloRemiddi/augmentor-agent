# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Install the remote Desktop supervisor as a per-user systemd service."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
NAME = 'augmentor-mobile.service'


def quote(value):
    # systemd syntax, not shell quoting. Percent specifiers must stay literal.
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', required=True, help='Exact private HTTPS origin, without trailing slash')
    args = parser.parse_args()
    origin = urlsplit(args.origin)
    if origin.scheme != 'https' or not origin.hostname or origin.username or origin.password or origin.path or origin.query or origin.fragment or any(c.isspace() for c in args.origin):
        parser.error('Use an exact HTTPS origin, for example https://computer.example:8443')
    node = shutil.which('node')
    if not node:
        parser.error('Node is required')
    subprocess.run(['systemctl', '--user', 'show-environment'], check=True, stdout=subprocess.DEVNULL)
    config = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    unit = config / 'systemd/user' / NAME
    unit.parent.mkdir(parents=True, exist_ok=True)
    command = ' '.join(map(quote, [sys.executable, ROOT / 'apps/mobile/start.py', '--origin', args.origin]))
    unit.write_text(f'''# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
[Unit]
Description=Augmentor original Desktop remote interface
StartLimitIntervalSec=120
StartLimitBurst=5

[Service]
Type=simple
ExecStart={command}
WorkingDirectory={str(ROOT).replace('%', '%%')}
Environment={quote('PATH=' + str(Path(node).parent) + ':/usr/local/bin:/usr/bin:/bin')}
Environment=PYTHONUNBUFFERED=1
UMask=0077
Restart=on-failure
RestartSec=10
TimeoutStopSec=30
KillMode=control-group

[Install]
WantedBy=default.target
''')
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', '--user', 'enable', NAME], check=True)
    print(f'Installed and enabled {unit}')
    print(f'After stopping any existing development supervisor, run: systemctl --user start {NAME}')


if __name__ == '__main__':
    main()
