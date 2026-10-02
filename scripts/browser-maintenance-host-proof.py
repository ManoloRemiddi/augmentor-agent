#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Linux qualification owner per Chromium native-host process, never an installer.

Actual Windows uses launch-windows-browser.py and kernel Job membership. This
disposable wrapper uses an exact direct child PID/executable and private Unix
transport, allowing old/new native hosts to overlap while switching harnesses.
"""
import os
from pathlib import Path
import subprocess
import sys
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from lifecycle.browser_control import BrowserControlServer


def main():
    if sys.platform!='linux' or os.environ.get('AUGMENTOR_PROOF_MAINTENANCE')!='1':
        raise RuntimeError('This owner requires the explicit disposable Linux browser proof.')
    root=Path(sys.argv[1]).resolve();node=Path(sys.argv[2]).resolve()
    runtime=Path(os.environ['XDG_RUNTIME_DIR'])
    started=threading.Event();child=None
    def verify(pid):
        if (not started.wait(5) or child is None or child.poll() is not None or
                pid!=child.pid or Path(f'/proc/{pid}/exe').resolve()!=node):
            raise ValueError('The registering bridge is not this proof owner\'s exact child.')
    with BrowserControlServer(root,runtime,verify_bridge=verify) as owner:
        environment={**os.environ,'AUGMENTOR_BROWSER_OWNER_ENDPOINT':str(owner.endpoint),
            'AUGMENTOR_BROWSER_OWNER_NONCE':owner.nonce,'AUGMENTOR_BROWSER_OWNER_PID':str(os.getpid()),
            'AUGMENTOR_BROWSER_OWNER_ROOT':str(root)}
        child=subprocess.Popen([str(node),str(root/'apps/browser/native-host.mjs'),*sys.argv[3:]],
            stdin=sys.stdin.buffer,stdout=sys.stdout.buffer,stderr=sys.stderr,env=environment)
        started.set()
        return child.wait()


if __name__=='__main__':raise SystemExit(main())
