#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Prepare a bounded personal-client repair; never select or mutate an installation.

The caller verifies/clones its complete base, then this script accepts only the
two inspected native-host baselines. Preserve runtime/dependency contracts,
product versions, extension key/storage and unrelated client customizations.
Seal, test and activate the resulting independent candidate with its OS installer.
If publishing is interrupted, discard the candidate and re-clone its base.
"""
import argparse
import hashlib
import json
from pathlib import Path

BASE_HOSTS={
 'linux':'3435592298dd4ec47820495bb54e43301a0487af17801836aed066531de37236',
 'macos':'58b2eeadaf5fa7d23864bb4d081ef8160b1a9bc8a8900a8ce5828103133b9be8'
}

BASE_FILES={
 'linux':{
  'apps/browser/native-host.mjs':BASE_HOSTS['linux'],
  'dist/runtime/src/host.js':'a7402717d7c128a6bc46e84b3505ced1fcedec07f28dbd4d6f3ae413d172fcb8',
  'adapters/dsh-desktop/index.mjs':'be6411860649b2d239fa29fcf9b1d6588d9f0290c104eef533af53eb26c6a3c8',
  'apps/browser/extension/sw.js':'dd2439c8a029eafada0e76dea1b85dc63e761168d6cdb5037cd5451e4b6559a5',
  'apps/browser/extension/port.mjs':'d3eaed45a5ef8072e8b8ab7941c663e1029e53f9d4b75d09ea71f973fbc97900',
  'apps/browser/extension/manifest.json':'9117a26d155e2a03128aa1d757e5b6ce2bb199a9b408ac1f955a1b77254e5434'},
 'macos':{
  'apps/browser/native-host.mjs':BASE_HOSTS['macos'],
  'dist/runtime/src/host.js':'f21a8fa481e87b962d8a016e3cad3beb87e96104ba5c3bab57cbe479717faf87',
  'adapters/dsh-desktop/index.mjs':'be6411860649b2d239fa29fcf9b1d6588d9f0290c104eef533af53eb26c6a3c8',
  'apps/browser/extension/sw.js':'4bcd7d646e4f8f7571d62d86e0fa3f2415624db90f41f9a01a752a800375a028',
  'apps/browser/extension/port.mjs':'21ff5916bf7fbfb56509639a399ffeea483bb05b48b752bf793d29bfaa42f72e',
  'apps/browser/extension/manifest.json':'218943c10ca02e7a510c9b4186c3fbf1e2bf4f442a12d36104f4c856bc8444d7'}
}


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def replace_once(text,old,new):
 if text.count(old)!=1:raise ValueError('The compatible source differs at a required patch boundary: '+old[:90])
 return text.replace(old,new,1)

def host_patch(text):
 text=replace_once(text,"import {surfaceRequest} from './shared/surface.mjs'","import {surfaceRequest} from './shared/surface.mjs'\nimport {registerConnectedBrowserHost} from './shared/connected-executor.mjs'\nimport {TOOL_REPAIR_BUILD} from './extension/build.mjs'")
 text=replace_once(text,'compatible=false',"compatible=false,extensionBuild=''")
 text=replace_once(text,"if(first.method==='augmentor/handshake'){","if(first.method==='augmentor/handshake'){extensionBuild=first.params?.extensionBuild??'';")
 busy='!compatible||closing||maintenance.paused' if 'function readFrames(' in text else '!compatible||closing' if 'closing=false' in text else '!compatible'
 reply_lines=[line for line in text.splitlines() if 'const reply=' in line]
 if len(reply_lines)!=1 or not reply_lines[0].rstrip().endswith(('}', '};')):raise ValueError('Use the inspected single-line native reply function.')
 text=replace_once(text,'const reply=value=>{',"const reply=value=>{if(value?.result?.protocol==='augmentor/1')value={...value,result:{...value.result,companionBuild:TOOL_REPAIR_BUILD}};")
 at=text.index('\n',text.index('const reply='));text=text[:at]+"\nconst connectedExecutor=registerConnectedBrowserHost(reply,{busy:()=>"+busy+",requiresReload:()=>extensionBuild!==TOOL_REPAIR_BUILD})"+text[at:]
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
 lines=text.splitlines(True);result=[];skip=False;removed=0
 for line in lines:
  if "if (m.surface === 'browser' && ![" in line and 'includes(e.toolName)' in line:skip=True;removed+=1;continue
  if skip:
   if 'return { block:' not in line:raise ValueError('Unexpected legacy surface policy body.')
   skip=False;continue
  result.append(line)
 if removed!=1 or skip:raise ValueError('The legacy surface policy boundary differs.')
 text=''.join(result)
 text=replace_once(text,"m.surface === 'browser' ? [] : resources.sources",'resources.sources');text=replace_once(text,"m.surface === 'browser' ? [] : resources.skills",'resources.skills')
 text=replace_once(text,'extensionFactories: [this.policy(m),','extensionFactories: [piShellDeadlines(), this.policy(m),')
 text=replace_once(text,"...(m.surface === 'browser' ? [this.browser.package(m.id)] : process.env.AUGMENTOR_PI_LINUX_TOOLS === '0' ? [] : [", "this.browser.package(m.id), ...(process.env.AUGMENTOR_PI_LINUX_TOOLS === '0' ? [] : [")
 text=replace_once(text,'browserRecovery,','browserRecovery, SHELL_DEADLINE_GUIDANCE,')
 text=replace_once(text,"'browser_tabs_list', 'browser_screenshot', 'browser_snapshot'].includes(e.toolName)","'browser_tabs_list', 'browser_screenshot', 'browser_snapshot', 'browser_capabilities', 'browser_document_read', 'browser_stop'].includes(e.toolName)")
 text=replace_once(text,"...(m.surface === 'browser' ? [] : ['read', 'write', 'edit', 'bash', 'ls', 'find', 'grep'])", "...['read', 'write', 'edit', 'bash', 'ls', 'find', 'grep']")
 import re
 text,count=re.subn(r"if \(m\.surface !== 'browser'\)(?=\s*await desktopControl\()","if (process.env.AUGMENTOR_PI_LINUX_TOOLS !== '0')",text)
 if count!=2:raise ValueError('The legacy desktop Stop boundaries differ: '+str(count))
 if "m.surface === 'browser' && ![" in text or "m.surface === 'browser' ? []" in text or 'piShellDeadlines(), this.policy(m)' not in text:raise ValueError('The compatible tool patch did not satisfy its postconditions.')
 return text

def apply(candidate,source,platform,source_ref):
 candidate=candidate.resolve(strict=True);source=source.resolve(strict=True)
 marker=json.loads((candidate/'.repair-candidate.json').read_text(encoding='utf-8'))
 base=Path(marker['baseRoot']).resolve(strict=True)
 if marker.get('schema')!='augmentor-independent-candidate/1' or marker.get('candidateRoot')!=str(candidate) or candidate==base or candidate.is_relative_to(base):raise ValueError('Use the recorded independent clone, never its selected base.')
 if candidate==source or candidate.is_relative_to(source):raise ValueError('Use a separate complete candidate, not the source checkout.')
 host=candidate/'apps/browser/native-host.mjs'
 for relative,expected in BASE_FILES[platform].items():
  if digest(candidate/relative)!=expected:raise ValueError('This client baseline was not reconciled: '+relative)
 before={};changed={};staged={}
 def publish(relative,bytes):
  target=candidate/relative
  if target.exists() and target.read_bytes()==bytes:return
  before[relative]=digest(target) if target.exists() else None
  staged[relative]=bytes
  changed[relative]=hashlib.sha256(bytes).hexdigest()
 def copy(relative):publish(relative,(source/relative).read_bytes())
 publish('apps/browser/native-host.mjs',host_patch(host.read_text(encoding='utf-8')).encode())
 for relative in ['apps/browser/shared/connected-executor.mjs','apps/browser/shared/control-tools.mjs',
  'apps/browser/extension/actions.mjs','apps/browser/extension/worktab.mjs','apps/browser/extension/trusted-input.mjs','apps/browser/extension/document-readback.mjs','apps/browser/extension/build.mjs',
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
 text="import {TOOL_REPAIR_BUILD} from './build.mjs'\n"+text
 text=replace_once(text,"{protocol:'augmentor/1',version:chrome.runtime.getManifest().version}","{protocol:'augmentor/1',version:chrome.runtime.getManifest().version,extensionBuild:TOOL_REPAIR_BUILD}")
 if "import {stopTrusted}" not in text:
  text="import {stopTrusted} from './trusted-input.mjs'\n"+text
  text=replace_once(text,'port.onDisconnect.addListener(() => {','port.onDisconnect.addListener(() => {\n    if(state.port!==port)return\n    void stopTrusted().catch(()=>{})')
 publish('apps/browser/extension/port.mjs',text.encode())
 manifest=candidate/'apps/browser/extension/manifest.json';value=json.loads(manifest.read_text(encoding='utf-8'))
 if 'debugger' not in value['permissions']:value['permissions'].append('debugger')
 value['host_permissions']=['<all_urls>'];publish('apps/browser/extension/manifest.json',(json.dumps(value,indent=2)+'\n').encode())
 receipt={'schema':'augmentor-personal-tool-repair/1','platform':platform,'repairSource':source_ref,
  'baseNativeHostSha256':BASE_HOSTS[platform],'preservedVersion':json.loads((candidate/'package.json').read_text(encoding='utf-8'))['version'],
  'before':dict(before),'files':dict(changed),'scope':'Bounded personal client overlay; not clean-commit or whole-product provenance. Seal/test/OS activation remain separate.'}
 publish('release/tool-repair-overlay.json',(json.dumps(receipt,indent=2)+'\n').encode())
 # Validate every transform before the first candidate file is written.
 for relative,data in staged.items():
  target=candidate/relative;target.parent.mkdir(parents=True,exist_ok=True)
  temporary=target.with_name('.'+target.name+'.repair');temporary.write_bytes(data);temporary.replace(target)
 return receipt

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('candidate',type=Path);p.add_argument('--source',type=Path,required=True);p.add_argument('--platform',choices=BASE_HOSTS,required=True);p.add_argument('--source-ref',required=True);a=p.parse_args()
 print(json.dumps(apply(a.candidate,a.source,a.platform,a.source_ref),indent=2))
