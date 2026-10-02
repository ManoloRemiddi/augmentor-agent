#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fixed independent observer extracted from the exact retained source installer.

Native Setup supplies compiled locations, private scratch and source metadata.
The actual installer has an independent Job; failure/timeout closes observations
without terminating it. No installed Python or saved process command is used.
"""
from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services'))
PHASE = 0


@contextmanager
def admission(base, *, maintenance=False):
    from lifecycle.windows_startup import Startup
    from platform_adapters.private_files import descriptor
    from platform_adapters import locks
    with ExitStack() as held:
        held.enter_context(Startup(base/'run', maintenance=maintenance))
        fd = descriptor(base/'run/installation.lock', writable=True)
        held.callback(os.close, fd)
        locks.flock(fd, (locks.LOCK_EX if maintenance else locks.LOCK_SH) | locks.LOCK_NB)
        yield


def registration(installed, key_name, application_id, *, source=None):
    import winreg
    def value(key, name, expected):
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as handle:
            actual, kind = winreg.QueryValueEx(handle, name)
        if kind != winreg.REG_SZ or actual != expected:
            raise ValueError('Owned installation metadata does not match this recovery source.')
    value(key_name, 'Root', str(installed))
    value(key_name, 'AppId', 'com.augmentor.Agent')
    if source is not None:
        uninstall = 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\' + application_id + '_is1'
        value(uninstall, 'ModifyPath', '"' + str(source) + '"')


def main():
    global PHASE
    if sys.platform != 'win32' or len(sys.argv) != 9:
        raise ValueError('Use the independent installer recovery action.')
    installed, base = Path(sys.argv[1]), Path(sys.argv[2])
    release_digest, installer_digest, helper_digest = sys.argv[3:6]
    key_name, application_id, qualification = sys.argv[6:9]
    if (not installed.is_absolute() or not base.is_absolute() or
            any(not re.fullmatch('[a-f0-9]{64}', value) for value in (release_digest, installer_digest, helper_digest)) or
            not key_name.startswith('Software\\') or not re.fullmatch('[A-Za-z0-9.]{1,128}', application_id) or
            qualification not in ('0', '1')):
        raise ValueError('Invalid compiled recovery context.')
    from lifecycle.payload_integrity import _read, _json, validate_inventory, inspect_payload, MAX_INVENTORY
    from lifecycle.installed_source import open_recorded_source, open_installed_source
    from lifecycle.source_restoration import SourceRestoration
    from lifecycle.windows_installer_process import InstallerProcess
    from lifecycle.windows_health import verify_local_health
    from platform_adapters.private_files import descriptor, require_directory
    from platform_adapters.windows_identity import local_app_data, private_file_descriptor
    from platform_adapters import locks
    PHASE = 1
    release_bytes = _read(ROOT/'release.json', 65536)
    inventory_bytes = _read(ROOT/'payload-integrity.json', MAX_INVENTORY)
    original = _read(ROOT/'recovery-record.json', 65536)
    if hashlib.sha256(release_bytes).hexdigest() != release_digest:
        raise ValueError('Independent source metadata changed.')
    validate_inventory(release_bytes, inventory_bytes)
    release = _json(release_bytes, 65536)
    if qualification == '1':
        if release.get('customerDistribution') is not False or release.get('qualificationStatus') != 'development-candidate':
            raise ValueError('Only a development candidate accepts qualification locations.')
    elif (base != local_app_data()/'Augmentor' or
          installed != local_app_data()/'Programs/Augmentor Agent/current' or
          key_name != 'Software\\Augmentor\\Installation' or application_id != 'com.augmentor.Agent'):
        raise ValueError('Recovery requires the compiled per-user installation.')
    require_directory(base); require_directory(base/'run'); require_directory(base/'updates')
    with ExitStack() as resources:
        PHASE = 2
        with admission(base, maintenance=True):
            registration(installed, key_name, application_id)
            # Pin the actual journal source, regardless of selected-installer.
            # Recheck the original snapshot under the live writer in the shared
            # attempt before any apply intent; concurrent recovery cannot adopt it.
            writer = descriptor(base/'updates/writer.lock', writable=True)
            try:
                locks.flock(writer, locks.LOCK_EX | locks.LOCK_NB)
                with os.fdopen(private_file_descriptor(base/'updates/active.json', share_write=False), 'rb') as active:
                    if active.read(65537) != original:
                        raise ValueError('The active update changed after independent assessment.')
                    source = resources.enter_context(open_recorded_source(base/'recovery', original, target=release['target']))
            finally:
                os.close(writer)
            if source.identity['sha256'] != installer_digest or source.release_digest != release_digest:
                raise ValueError('The retained source differs from independent installer metadata.')
            attempt = resources.enter_context(SourceRestoration(base/'updates', original, release_bytes, installer_digest))
            log = base/'updates'/('recovery-' + attempt.record['id'] + '.log')
            os.close(descriptor(log, writable=True, exclusive=True))
            attempt.apply_intent()
        PHASE = 3
        # The native observer Job explicitly permits breakaway. Always request
        # it; there is no hosted-test fallback tying Setup to this observer.
        installer = resources.enter_context(InstallerProcess(source.installer, installer_digest,
            ['/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
             '/augmentorrecover=source', '/LOG=' + str(log)]))
        deadline = time.monotonic() + 300
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Source installation is still running. It was preserved.')
            try:
                code = installer.wait(timeout=min(5, remaining))
                break
            except TimeoutError:
                continue  # Observe the same actual Job; never launch again.
        if code:
            raise RuntimeError('The independently observed source installer refused or failed.')
        PHASE = 4
        attempt.observed_installer_exit(lambda: installer.wait(timeout=0) == 0)
        health = None
        def verify_source(assessment):
            nonlocal health
            registration(installed, key_name, application_id, source=source.installer)
            if hashlib.sha256(_read(installed.parent/'maintenance/augmentor-installer-handoff.dll', 8*1024*1024)).hexdigest() != helper_digest:
                raise ValueError('Installed maintenance code differs from the independent source.')
            with open_installed_source(base/'recovery', release_bytes, target=release['target']) as selected:
                if selected.identity != source.identity or selected.release_digest != release_digest:
                    raise ValueError('Restored source selection differs from the retained source.')
                if not inspect_payload(installed, release_bytes, inventory_bytes)['complete']:
                    raise ValueError('Restored source payload is incomplete.')
                health = verify_local_health(installed, release_bytes,
                    qualification=base if qualification == '1' else None)
            return True
        PHASE = 5
        with admission(base):
            archive = attempt.complete(verify_source)
        PHASE = 6
        report = {'schema': 'augmentor-source-recovery/1', 'outcome': 'source-restored',
            'recordSHA256': hashlib.sha256(original).hexdigest(), 'installerSHA256': installer_digest,
            'releaseSHA256': release_digest, 'archive': archive.name,
            'receipt': attempt.path.name, 'localHealth': health}
        # Native Setup owns/pins this fresh private scratch. The durable receipt
        # and original archive precede this disposable reporting output.
        with (ROOT.parent/'recovery-result.json').open('xb') as stream:
            stream.write((json.dumps(report, separators=(',', ':')) + '\n').encode('ascii'))


if __name__ == '__main__':
    try: main()
    except Exception as error:
        # Numeric/class-only diagnostics; no traceback, paths or user content.
        if sys.platform == 'win32' and (ROOT/'recovery-record.json').is_file():
            try:
                code = getattr(error, 'winerror', None) or getattr(error, 'errno', None)
                failure = {'schema': 'augmentor-source-recovery-error/1', 'phase': PHASE,
                    'kind': type(error).__name__[:64], 'code': code if type(code) is int else None}
                with (ROOT.parent/'recovery-error.json').open('x', encoding='ascii') as stream:
                    json.dump(failure, stream)
            except Exception: pass
        sys.exit(120 + PHASE)
