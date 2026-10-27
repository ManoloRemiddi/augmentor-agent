#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Prepare a bounded personal-client repair; never select or mutate an installation.

The caller verifies/clones its complete base, then this script accepts only the
two inspected native-host baselines. Preserve runtime/dependency contracts,
product versions, extension key/storage and unrelated client customizations.
Seal, test and activate the resulting independent candidate with its OS installer.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

BASE_HOSTS={
 'linux':'3435592298dd4ec47820495bb54e43301a0487af17801836aed066531de37236',
 'macos':'58b2eeadaf5fa7d23864bb4d081ef8160b1a9bc8a8900a8ce5828103133b9be8'
}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def replace_once(text,old,new):
 if text.count(old)!=1:raise ValueError('The compatible source differs at a required patch boundary: '+old[:90])
 return text.replace(old,new,1)

def host_patch(text):
 text=replace_once(text,"import {surfaceRequest} from './shared/surface.mjs'","import {surfaceRequest} from './shared/surface.mjs'\nimport {registerConnectedBrowserHost} from './shared/connected-executor.mjs'")
 busy='!compatible||closing||maintenance.paused' if 'function readFrames(' in text else '!compatible||closing' if 'closing=false' in text else '!compatible'
 at=text.index('\n',text.index('const reply='));text=text[:at]+"\nconst connectedExecutor=registerConnectedBrowserHost(reply,{busy:()=>"+busy+"})"+text[at:]
 if 'function readFrames(' in text:
  text=replace_once(text,'    if(closing)return','    if(closing)return\n    if(connectedExecutor.receive(first))return')
  text=replace_once(text,'if(!closing){closing=true;','if(!closing){closing=true;connectedExecutor.close();')
  text=replace_once(text,'childRequests.size+childActions.size','childRequests.size+childActions.size+connectedExecutor.active')
 else:
  # Parse every frame even after the engine starts: cross-harness browser replies
  # belong to this existing native host, never to its selected engine child.
  text=replace_once(text,'  if(child){child.stdin.write(chunk);return}\n','')
  anchor='buffer=buffer.subarray(n+4)'
  text=replace_once(text,anchor,anchor+"\n    if(connectedExecutor.receive(first))continue\n    if(child){const b=Buffer.from(JSON.stringify(first)),h=Buffer.alloc(4);h.writeUInt32LE(b.length);child.stdin.write(Buffer.concat([h,b]));continue}")
  text=replace_once(text,'    if(buffer.length)child.stdin.write(buffer);buffer=Buffer.alloc(0);return','    continue')
  if 'function close(' in text:text=replace_once(text,'if(!closing){closing=true;','if(!closing){closing=true;connectedExecutor.close();')
  else:
   text=replace_once(text,"process.stdin.on('end',()=>{child?.kill();", "process.stdin.on('end',()=>{connectedExecutor.close();child?.kill();")
   text=replace_once(text,"process.on('SIGTERM',()=>{child?.kill();", "process.on('SIGTERM',()=>{connectedExecutor.close();child?.kill();")
 return text

def legacy_host_patch(text):
 # These client artifacts retain their locked Pi0.85.1 API and dependencies.
 # Add current browser/tool adapters and a default-only shell hook, not a new loop.
 if "m.surface === 'browser' ? [] : resources.sources" not in text:raise ValueError('The legacy runtime source was not reconciled.')
 text="import {piShellDeadlines,SHELL_DEADLINE_GUIDANCE} from './shell-deadlines.js';\n"+text
 lines=text.splitlines(True);result=[];skip=False
 for line in lines:
  if "if (m.surface === 'browser' && ![" in line and 'includes(e.toolName)' in line:skip=True;continue
  if skip:
   if 'return { block:' not in line:raise ValueError('Unexpected legacy surface policy body.')
   skip=False;continue
  result.append(line)
 text=''.join(result)
 text=replace_once(text,"m.surface === 'browser' ? [] : resources.sources",'resources.sources');text=replace_once(text,"m.surface === 'browser' ? [] : resources.skills",'resources.skills')
 text=replace_once(text,'extensionFactories: [this.policy(m),','extensionFactories: [piShellDeadlines(), this.policy(m),')
 text=replace_once(text,"...(m.surface === 'browser' ? [this.browser.package(m.id)] : process.env.AUGMENTOR_PI_LINUX_TOOLS === '0' ? [] : [", "this.browser.package(m.id), ...(process.env.AUGMENTOR_PI_LINUX_TOOLS === '0' ? [] : [")
 text=replace_once(text,'browserRecovery,','browserRecovery, SHELL_DEADLINE_GUIDANCE,')
 text=replace_once(text,"'browser_tabs_list', 'browser_screenshot', 'browser_snapshot'].includes(e.toolName)","'browser_tabs_list', 'browser_screenshot', 'browser_snapshot', 'browser_capabilities', 'browser_document_read', 'browser_stop'].includes(e.toolName)")
 text=replace_once(text,"...(m.surface === 'browser' ? [] : ['read', 'write', 'edit', 'bash', 'ls', 'find', 'grep'])", "...['read', 'write', 'edit', 'bash', 'ls', 'find', 'grep']")
 if "m.surface === 'browser' ? []" in text or 'piShellDeadlines(), this.policy(m)' not in text:raise ValueError('The compatible tool patch did not satisfy its postconditions.')
 return text

def apply(candidate,source,platform,source_ref):
 candidate=candidate.resolve(strict=True);source=source.resolve(strict=True)
 marker=json.loads((candidate/'.repair-candidate.json').read_text(encoding='utf-8'))
 base=Path(marker['baseRoot']).resolve(strict=True)
 if marker.get('schema')!='augmentor-independent-candidate/1' or marker.get('candidateRoot')!=str(candidate) or candidate==base or candidate.is_relative_to(base):raise ValueError('Use the recorded independent clone, never its selected base.')
 if candidate==source or candidate.is_relative_to(source):raise ValueError('Use a separate complete candidate, not the source checkout.')
 host=candidate/'apps/browser/native-host.mjs'
 if digest(host)!=BASE_HOSTS[platform]:raise ValueError('This client baseline was not reconciled; do not patch it by version label.')
 before={};changed={}
 def publish(relative,bytes):
  target=candidate/relative
  if target.exists() and target.read_bytes()==bytes:return
  before[relative]=digest(target) if target.exists() else None
  target.parent.mkdir(parents=True,exist_ok=True)
  # Atomic replacement also preserves a clone sharing unchanged immutable files.
  temporary=target.with_name('.'+target.name+'.repair');temporary.write_bytes(bytes);temporary.replace(target)
  changed[relative]=digest(target)
 def copy(relative):publish(relative,(source/relative).read_bytes())
 publish('apps/browser/native-host.mjs',host_patch(host.read_text(encoding='utf-8')).encode())
 for relative in ['apps/browser/shared/connected-executor.mjs','apps/browser/shared/control-tools.mjs',
  'apps/browser/extension/actions.mjs','apps/browser/extension/worktab.mjs','apps/browser/extension/trusted-input.mjs','apps/browser/extension/document-readback.mjs',
  'services/browser/executor.py','services/desktop/service.py','services/desktop/client.py',
  'services/desktop/portal.py','services/desktop/screen_mapping.py','services/desktop/windows.py',
  'services/platform_adapters/locks.py','services/platform_adapters/private_files.py','services/platform_adapters/transport.py','services/platform_adapters/paths.py',
  'dist/desktop/src/index.js','dist/desktop/src/capabilities.js',
  'dist/pi-browser/src/index.js','dist/runtime/src/shell-deadlines.js',
  'adapters/dsh-desktop/connected-browser.mjs','config/browser-recovery.md','config/skills/google-docs-browser/SKILL.md']:
  copy(relative)
 # Keep local DSH steering, policy and support overlays; add only this registration.
 adapter=candidate/'adapters/dsh-desktop/index.mjs';text=adapter.read_text(encoding='utf-8')
 text="import {applyConnectedBrowser} from './connected-browser.mjs'\n"+text
 text=replace_once(text,'export function apply(ctx){','export function apply(ctx){\n  applyConnectedBrowser(ctx)')
 publish('adapters/dsh-desktop/index.mjs',text.encode())
 legacy=candidate/'dist/runtime/src/host.js'
 publish('dist/runtime/src/host.js',legacy_host_patch(legacy.read_text(encoding='utf-8')).encode())
 # Port the already-qualified toolbar grant fix without replacing panel/UI files.
 worker=candidate/'apps/browser/extension/sw.js';text=worker.read_text(encoding='utf-8')
 if 'openPanelOnActionClick: true' in text or 'openPanelOnActionClick:true' in text:
  text=text.replace('openPanelOnActionClick: true','openPanelOnActionClick: false').replace('openPanelOnActionClick:true','openPanelOnActionClick:false')
  text+="\nchrome.action.onClicked.addListener(tab=>{if(tab.id!==undefined)void chrome.sidePanel.open({tabId:tab.id}).catch(()=>{})})\n"
  publish('apps/browser/extension/sw.js',text.encode())
 port=candidate/'apps/browser/extension/port.mjs';text=port.read_text(encoding='utf-8')
 if "import {stopTrusted}" not in text:
  text="import {stopTrusted} from './trusted-input.mjs'\n"+text
  text=replace_once(text,'port.onDisconnect.addListener(() => {','port.onDisconnect.addListener(() => {\n    if(state.port!==port)return\n    void stopTrusted().catch(()=>{})')
  publish('apps/browser/extension/port.mjs',text.encode())
 manifest=candidate/'apps/browser/extension/manifest.json';value=json.loads(manifest.read_text(encoding='utf-8'))
 if 'debugger' not in value['permissions']:value['permissions'].append('debugger')
 value['host_permissions']=['<all_urls>'];publish('apps/browser/extension/manifest.json',(json.dumps(value,indent=2)+'\n').encode())
 receipt={'schema':'augmentor-personal-tool-repair/1','platform':platform,'repairSource':source_ref,
  'baseNativeHostSha256':BASE_HOSTS[platform],'preservedVersion':json.loads((candidate/'package.json').read_text(encoding='utf-8'))['version'],
  'before':before,'files':changed,'scope':'Bounded personal client overlay; not clean-commit or whole-product provenance. Seal/test/OS activation remain separate.'}
 publish('release/tool-repair-overlay.json',(json.dumps(receipt,indent=2)+'\n').encode())
 return receipt

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('candidate',type=Path);p.add_argument('--source',type=Path,required=True);p.add_argument('--platform',choices=BASE_HOSTS,required=True);p.add_argument('--source-ref',required=True);a=p.parse_args()
 print(json.dumps(apply(a.candidate,a.source,a.platform,a.source_ref),indent=2))
