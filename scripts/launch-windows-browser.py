#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Console-free Windows native host with binary stdio and owned bridge children."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]


def origin(root=ROOT):
    manifest = json.loads((root/'apps/browser/extension/manifest.json').read_text(encoding='utf-8'))
    digest = hashlib.sha256(base64.b64decode(manifest['key'], validate=True)).hexdigest()[:32]
    return 'chrome-extension://'+''.join(chr(ord('a')+int(value, 16)) for value in digest)+'/'


def validate_arguments(args, root=ROOT):
    if (not args or args[0] != origin(root) or len(args) > 2 or
            (len(args) == 2 and not re.fullmatch(r'--parent-window=\d{1,20}', args[1]))):
        raise ValueError('This browser host only accepts the matching Augmentor extension.')


def main():
    if sys.platform != 'win32': raise ValueError('Use the browser companion for this operating system.')
    sys.path[:0] = [str(ROOT/'services'), str(ROOT/'apps/native')]
    spec = importlib.util.spec_from_file_location('windows_launcher', ROOT/'scripts/launch-windows.py')
    desktop = importlib.util.module_from_spec(spec); spec.loader.exec_module(desktop)
    desktop.configure_qt()
    release = desktop.preflight()
    args = list(sys.argv[1:]); paths = None
    if args[:1] == ['--qualification-root']:
        if len(args) < 2: raise ValueError('A disposable qualification directory is required.')
        paths = desktop.configure_qualification(args[1], release); args = args[2:]
    validate_arguments(args)
    desktop.load_launcher().configure(windows_paths=paths)
    from platform_adapters.paths import private_directory
    from platform_adapters.private_files import descriptor
    log = private_directory(Path(os.environ['XDG_STATE_HOME'])/'logs')/'browser-host.log'
    with os.fdopen(descriptor(log, writable=True, create=True), 'a', encoding='utf-8', buffering=1) as stream:
        # stdout belongs exclusively to the extension protocol. Failures are
        # private diagnostics, never a modal dialog or a stray stdout line.
        sys.stderr = stream
        try:
            from lifecycle.lease import hold
            from windows_supervisor import ensure
            from platform_adapters.processes import OwnedProcess
            hold('runtime'); ensure(ROOT)
            environment = {**os.environ}
            environment.pop('NODE_OPTIONS', None); environment.pop('NODE_PATH', None)
            child = OwnedProcess([str(ROOT/'node/node.exe'), str(ROOT/'apps/browser/native-host.mjs'), *args],
                env=environment, cwd=str(ROOT), stdin=sys.stdin.buffer,
                stdout=sys.stdout.buffer, stderr=stream)
            try: return child.wait()
            finally: child.close()
        except Exception:
            traceback.print_exc()
            return 1


if __name__ == '__main__':
    try: code = main()
    except Exception:
        if sys.stderr is not None and not sys.stderr.closed:
            print('The Augmentor browser companion could not start. Repair this installation.', file=sys.stderr)
        code = 1
    raise SystemExit(code)
