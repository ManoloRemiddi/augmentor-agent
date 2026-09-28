#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Disposable Inno coordinator; customer handoff authentication is not implemented."""
import argparse
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from lifecycle.windows_startup import Startup


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installer',required=True,type=Path)
    parser.add_argument('--state',required=True,type=Path)
    parser.add_argument('--log',required=True,type=Path)
    args=parser.parse_args()
    with Startup(args.state,maintenance=True) as gate:
        installer=subprocess.Popen([str(args.installer),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',
            '/LOG='+str(args.log),'/startupowner='+str(os.getpid()),
            '/startuphandle='+str(msvcrt.get_osfhandle(gate.fd))],stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True)
        (args.state/'coordinator.json').write_text(json.dumps({'installerPid':installer.pid}),encoding='utf-8')
        deadline=time.monotonic()+30
        while not (args.state/'parent-release').exists():
            if installer.poll() is not None:raise RuntimeError('The disposable installer exited before handoff.')
            if time.monotonic()>=deadline:raise TimeoutError('The disposable handoff was not observed.')
            time.sleep(.02)
    # No wait or termination: the actual independent Setup process retains the
    # duplicated writer. The test separately waits on its exact kernel handle.


if __name__=='__main__':main()
