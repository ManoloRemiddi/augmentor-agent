#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Stage a bounded tablet overlay without discarding installed platform overlays.
Run inside harness-build-workspace.py with the target deployment XDG_DATA_HOME.
The original release is verified and never edited. Activation is separate.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--base',type=Path,required=True)
p.add_argument('--expected-base-sha256',required=True)
p.add_argument('--candidate',type=Path,required=True)
p.add_argument('--source-ref',required=True)
a=p.parse_args()
if 'AUGMENTOR_BUILD_WORKSPACE' not in os.environ:p.error('Use the managed build workspace.')
source=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('tablet_deployment',source/'scripts/desktop-deployment.py');deployment=importlib.util.module_from_spec(spec);spec.loader.exec_module(deployment)
base=deployment.verify(a.base)
if base['artifactSha256']!=a.expected_base_sha256:raise ValueError('Installed base changed. Review its overlays before staging.')
manifest=json.loads((a.candidate/'manifest.json').read_text())
if manifest.get('productVersion')!=base['deployment']['version']:raise ValueError('Tablet and installed product versions must match.')
for name,sha in manifest['files'].items():
 path=a.candidate/name
 if not path.resolve().is_relative_to(a.candidate.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError('Candidate manifest changed.')
work=Path(os.environ['AUGMENTOR_BUILD_WORKSPACE'])/'tablet-artifact'
shutil.copytree(a.base,work,symlinks=True)
host=work/'dist/runtime/src/host.js';s=host.read_text()
def replace(old,new,count=1):
 global s
 if s.count(old)!=count:raise ValueError('Installed Host differs at a tablet boundary. Preserve it for review: '+old[:55])
 s=s.replace(old,new)
replace("import { WorkspaceRegistry, workspacePath }", "import { ungroupedDirectory } from './ungrouped.js';\nimport { WorkspaceRegistry, workspacePath }")
replace('[...this.metadata.values()].map(m => resolve(m.cwd))','[...this.metadata.values()].filter(m => !m.ungrouped).map(m => resolve(m.cwd))')
replace('sessionId: m.id, cwd: m.cwd, agentPreset:', 'sessionId: m.id, cwd: m.cwd, ...(m.ungrouped ? { ungrouped: true } : {}), agentPreset:',3)
replace('capabilities: { voice: true, voiceBridge: true,','capabilities: { browserAudio: 1, browserDictationDraft: 1, isolatedUngrouped: 1, voice: true, voiceBridge: true,')
replace('const cwd = resolve(text(p.cwd, 4096));',"""if (p.ungrouped !== undefined && p.ungrouped !== true) throw Error('Choose an explicit Ungrouped chat.');
                    if (p.ungrouped && p.cwd !== undefined) throw Error('An Ungrouped chat cannot inherit a project directory.');
                    const cwd = p.ungrouped ? ungroupedDirectory(this.dirs.state, sid) : resolve(text(p.cwd, 4096));""")
replace("m = { surface: p.surface === 'browser' ? 'browser' : 'linux', id: sid, cwd, selection:", "m = { ...(p.ungrouped ? { ungrouped: true } : {}), surface: p.surface === 'browser' ? 'browser' : 'linux', id: sid, cwd, selection:")
host.write_text(s)
for name in ('harness-server.js','harness-voice.js','ungrouped.js'):shutil.copy2(a.candidate/'runtime'/name,work/'dist/runtime/src'/name)
shutil.rmtree(work/'dist/harness-web');shutil.copytree(a.candidate/'web',work/'dist/harness-web')
for name in ('dsh-app.jsx','dsh-pi-controller.mjs','harness-audio.mjs','responsive-sidebar.mjs','tablet.css','agent-continuity.mjs','dsh-drafts.mjs'):shutil.copy2(source/'apps/harness'/name,work/'apps/harness'/name)
for name in ('TABLET-HARNESS.md','ANDROID-AH.md','AGENT-HANDOFF.md','README.md'):shutil.copy2(source/'docs'/name,work/'docs'/name)
for name in ('stage-tablet-harness.py','build-mobile-ah.py'):shutil.copy2(source/'scripts'/name,work/'scripts'/name)
root=deployment.stage(work,a.source_ref,node=work/'node/bin/node')
print(json.dumps({'root':str(root),'artifactSha256':deployment.verify(root)['artifactSha256'],'baseArtifactSha256':a.expected_base_sha256}))
