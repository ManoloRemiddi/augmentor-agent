# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Observe/drain only a plan fixture's authenticated private companion graph."""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(sys.argv[1]).resolve(strict=True)
PRIVATE = Path(sys.argv[2]).resolve(strict=True)
if sys.platform != 'win32' or not PRIVATE.name.startswith('augmentor-plan-'):
    raise SystemExit('An actual private Windows plan fixture is required.')
if PRIVATE.parent != Path(os.environ['TEMP']).resolve(strict=True):
    raise SystemExit('The fixture is outside its explicit temporary root.')
sys.path.insert(0, str(ROOT / 'services'))
from platform_adapters.private_files import atomic_json, require_directory
from platform_adapters.windows_identity import private_directory
from lifecycle.windows_components import discover_owner
from lifecycle.windows_preparation import WindowsPreparation

runtime, shared = PRIVATE / 'runtime', PRIVATE / 'shared-state'
for path in (PRIVATE, runtime):
    require_directory(path)
if Path(os.environ['XDG_RUNTIME_DIR']).resolve(strict=True) != runtime:
    raise SystemExit('The cleanup profile differs from the fixture.')
if Path(os.environ['AUGMENTOR_SHARED_STATE']).resolve() != shared:
    raise SystemExit('The cleanup shared profile differs from the fixture.')
owner = discover_owner(ROOT, runtime)
if owner is None:
    print(json.dumps({'privateSupervisorObserved': False}))
    raise SystemExit(0)
try:
    pid = owner.pid
    if owner.initial.get('dsh', {}).get('running') or owner.initial.get('voice', {}).get('running'):
        raise ValueError('Unexpected DSH/voice work in the fixture; it was preserved.')
finally:
    owner.close()
private_directory(shared)

evidence = []
def checkpoint(phase, participant):
    evidence.append({'phase': phase, 'pid': participant.pid, 'component': getattr(participant, 'name', 'supervisor')})
    atomic_json(PRIVATE / 'companion-drain.json', {'supervisor': pid, 'observations': evidence})

deadline = time.monotonic() + 5
while True:
    preparation = WindowsPreparation(ROOT, runtime, shared, PRIVATE / 'xdg-data/augmentor/managed-dsh')
    try:
        preparation.__enter__()
        break
    except ValueError as error:
        # Retry only a known busy refusal after all reservations were released;
        # an unknown reply never permits another mutation attempt.
        if 'active work' not in str(error) or not preparation.preparation_released or time.monotonic() >= deadline:
            raise
        time.sleep(.02)
try:
    if preparation.windows or preparation.browsers or preparation.dsh or preparation.voice:
        raise ValueError('Unexpected application work in the fixture; it was preserved.')
    preparation.drain(checkpoint=checkpoint)
finally:
    preparation.__exit__(*sys.exc_info())
print(json.dumps({'privateSupervisorObserved': True, 'drained': True,
    'components': sorted({row['component'] for row in evidence})}))
