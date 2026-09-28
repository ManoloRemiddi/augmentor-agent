#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fixed native local-health action; no normal desktop or journal completion.

The native entrypoint holds the application's installation lease before Python
loads. This action may inspect an unresolved replacement, but only inside a new
private temporary profile. It never connects to models or starts companions.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != 'win32': raise RuntimeError('Use the Windows native health action.')
    args = sys.argv[1:]
    sys.path[:0] = [str(ROOT/'services'), str(ROOT/'apps/native')]
    from platform_adapters.windows_identity import local_app_data, private_directory, require_private_directory
    with (ROOT/'release.json').open('rb') as stream:
        release_bytes = stream.read(65537)
    if not 0 < len(release_bytes) <= 65536:
        raise ValueError('The installed payload metadata is invalid.')
    release = json.loads(release_bytes)
    if not isinstance(release, dict): raise ValueError('The installed payload metadata is invalid.')
    base = local_app_data()/'Augmentor'
    if args[:1] == ['--qualification-root']:
        if (len(args) != 3 or release.get('customerDistribution') is not False or
                release.get('qualificationStatus') != 'development-candidate'):
            raise ValueError('Disposable health data requires a development candidate.')
        base = Path(args[1]).absolute(); args = args[2:]
    if args != ['--local-health']: raise ValueError('Health checks do not accept desktop actions.')
    require_private_directory(base)
    probes = private_directory(base/'health-probes')
    profile = private_directory(probes/secrets.token_hex(24))
    try:
        # Inherited app/profile settings must not reconnect a service, read a
        # conversation or redirect this disposable render to the user's state.
        for name in list(os.environ):
            if name.startswith(('AUGMENTOR_', 'RESONANT_', 'XDG_', 'PI_', 'QT_', 'QML_')):
                del os.environ[name]
        environment = {key:str(private_directory(profile/child)) for key,child in (
            ('XDG_CONFIG_HOME','config'), ('XDG_DATA_HOME','data'), ('XDG_STATE_HOME','state'),
            ('XDG_CACHE_HOME','cache'), ('XDG_RUNTIME_DIR','run'))}
        for key,child in (('AUGMENTOR_SHARED_STATE','run/shared'),
                          ('AUGMENTOR_SHARED_CONFIG','config/shared'), ('AUGMENTOR_SHARED_DATA','data/shared')):
            environment[key] = str(private_directory(profile/child))
        spec = importlib.util.spec_from_file_location('health_windows_launcher', ROOT/'scripts/launch-windows.py')
        launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)
        launcher.load_launcher().configure(windows_paths=environment)
        os.environ['QT_QPA_PLATFORM'] = 'windows'
        os.environ['QSG_RHI_PREFER_SOFTWARE_RENDERER'] = '1'
        launcher.configure_qt()
        identified = launcher.preflight()
        if identified != release: raise RuntimeError('The observed payload metadata changed.')
        from augmentor_linux.local_health import render_preview
        result = {'schema':'augmentor-local-health/1', 'releaseSHA256':hashlib.sha256(release_bytes).hexdigest(),
                  'version':release['version'], 'sourceCommit':release['sourceCommit'], 'target':release['target'],
                  **render_preview(platform='windows')}
    finally:
        # Only this invocation's unpredictable, privately created profile.
        require_private_directory(profile)
        shutil.rmtree(profile)
    os.write(1, (json.dumps(result, separators=(',',':'))+'\n').encode('utf-8'))


if __name__ == '__main__':
    try: main()
    except Exception as error:
        # Exception type is useful for private diagnostics without disclosing
        # arbitrary paths, profile values or exception messages to a caller.
        os.write(2, ('Augmentor local health failed ('+type(error).__name__+
                    '); no transaction was completed.\n').encode('ascii',errors='replace'))
        raise SystemExit(1)
