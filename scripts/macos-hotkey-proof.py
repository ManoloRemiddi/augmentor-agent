#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Native registration lifecycle proof; does not synthesize keyboard input."""
import json
from pathlib import Path
import selectors
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
command=[str(ROOT/'outputs/native/augmentor-hotkey'),'80','6912']
if sys.platform!='darwin':raise SystemExit('Run on macOS with the compiled helper.')

def ready(process):
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout,selectors.EVENT_READ)
        assert selector.select(5),'Hotkey readiness timed out'
        return json.loads(process.stdout.readline())

def start():
    return subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

first=start()
try:
    resolver=command[:1]
    lower=subprocess.run([*resolver,'--resolve','j'],capture_output=True,check=True)
    upper=subprocess.run([*resolver,'--resolve','J'],capture_output=True,check=True)
    assert json.loads(lower.stdout)==json.loads(upper.stdout)
    invalid=subprocess.run([*resolver,'--resolve','not-a-single-key'],capture_output=True)
    assert invalid.returncode!=0 and 'error' in json.loads(invalid.stdout)
    response=ready(first);assert response.get('event')=='ready',response
    duplicate=subprocess.run(command,input=b'',capture_output=True,timeout=5)
    assert duplicate.returncode!=0 and 'error' in json.loads(duplicate.stdout),duplicate.stdout
    first.stdin.close();assert first.wait(timeout=5)==0
    second=start()
    try:
        assert ready(second).get('event')=='ready'
        second.stdin.close();assert second.wait(timeout=5)==0
    finally:
        if second.poll() is None:second.kill();second.wait()
    result={'registration':True,'conflictRefused':True,'ownerExitReleasesShortcut':True,
            'activeLayoutResolution':True,'invalidKeyRefused':True,
            'keyPressDeliveryTested':False}
    (ROOT/'outputs/cross-platform').mkdir(parents=True,exist_ok=True)
    (ROOT/'outputs/cross-platform/mac-hotkey-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
finally:
    if first.poll() is None:first.kill();first.wait()
