#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Prepare the bounded AH surface backport on the recorded 0.2.11 MX artifact.

Run only inside harness-build-workspace.py. The old DSH/speech/Handy contract,
release version and all unrelated files survive. The normal deployment tool
must verify, seal and activate the resulting candidate separately.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

BASE='90bc1347822bb3af6e4e96d6b6d00708d4631f9a9fbd68351a11c494c9d9669f'


def engines(s):
    for a,b in [("('pi','dsh','codex')","('pi','ah','dsh','codex')"),("['pi','dsh','codex']","['pi','ah','dsh','codex']"),("('pi','codex')","('pi','ah','codex')"),("['pi','codex']","['pi','ah','codex']")]:s=s.replace(a,b)
    for obj in ['self.harness','self.controller.harness','controller.harness','c.harness']:
        s=s.replace(obj+"=='pi'",obj+" in ('pi','ah')").replace(obj+"!='pi'",obj+" not in ('pi','ah')")
    s=s.replace("getattr(window.controller,'harness',None)=='pi'","getattr(window.controller,'harness',None) in ('pi','ah')")
    for obj in ['state.harness','harness']:
        s=s.replace(obj+"==='pi'","['pi','ah'].includes("+obj+")").replace(obj+"!=='pi'","!['pi','ah'].includes("+obj+")")
    return s.replace('Choose DSH, Pi or Codex','Choose Augmentor Harness, DSH, Pi or Codex')


def browser_updates(root):
    """Only AH-related edits; preserve custom/unrelated extension source."""
    changes={}
    for name in ['state.mjs','port.mjs','settings.mjs','panel-api.mjs','surface.mjs','voice.mjs']:
        p=root/name;before=p.read_text();after=engines(before)
        after=after.replace("['pi','dsh']","['pi','ah','dsh']").replace('Choose DSH or Pi','Choose Augmentor Harness, DSH or Pi')
        if name=='state.mjs':
            after=after.replace("if(saved['augmentor-harness']==='pi')return 'pi'","if(['pi','ah'].includes(saved['augmentor-harness']))return saved['augmentor-harness']")
        if name=='settings.mjs':
            after=after.replace("['pi','Pi'],['dsh'","['ah','Augmentor Harness'],['pi','Pi (legacy profile)'],['dsh'").replace("{dsh:'DSH',pi:'Pi',codex:'Codex'}","{dsh:'DSH',ah:'Augmentor Harness',pi:'Pi',codex:'Codex'}").replace("session:state.harness+':'+state.sessionId","session:(state.harness==='ah'?'pi':state.harness)+':'+state.sessionId")
            after=after.replace("{dsh:'DSH',pi:'Pi'}","{dsh:'DSH',ah:'Augmentor Harness',pi:'Pi'}")
        if name=='panel-api.mjs':
            after=after.replace("msg.type==='prompt/improve'&&(!['dsh','codex'].includes(state.harness)","msg.type==='prompt/improve'&&(!['dsh','ah','codex'].includes(state.harness)")
            after=after.replace("msg.type==='prompt/improve'&&(state.harness!=='dsh'", "msg.type==='prompt/improve'&&(!['dsh','ah'].includes(state.harness)")
        if after!=before:changes[name]=after.encode()
    return changes

def prepare(base, source, out):
    from importlib.util import spec_from_file_location, module_from_spec
    spec=spec_from_file_location('deployment',source/'scripts/desktop-deployment.py');d=module_from_spec(spec);spec.loader.exec_module(d)
    manifest=d.verify(base)
    if manifest['artifactSha256'] != BASE:
        raise ValueError('This bounded backport requires the exact recorded compatible base; reconcile a different release explicitly.')
    scratch=Path(os.environ['AUGMENTOR_BUILD_WORKSPACE']).resolve(strict=True)
    if not out.is_relative_to(scratch) or out==scratch or out.exists():
        raise ValueError('Prepare one new candidate inside the managed scratch workspace.')
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('desktop-release.json','__pycache__','*.pyc'))
    def edit(name,fn):
        p=out/name
        if not p.exists():return
        old=p.read_text();new=fn(old)
        if new!=old:p.write_text(new)
    for name in ['controller.py','window.py','preferences.py','panels.py','agent_settings.py']:
        edit('apps/native/augmentor_linux/'+name,engines)
    for name in ['state.mjs','port.mjs','settings.mjs','panel-api.mjs','surface.mjs','voice.mjs']:
        edit('apps/browser/extension/'+name,engines)
    edit('apps/native/augmentor_linux/controller.py',lambda s:s.replace("if client is None and harness=='dsh':","if client is None and harness=='ah':\n            from .adapters.ah import AhAdapter\n            self.client=AhAdapter()\n        elif client is None and harness=='dsh':"))
    edit('apps/native/augmentor_linux/agent_settings.py',lambda s:s.replace("[('DSH','dsh'),('Pi','pi'),('Codex (development)','codex')]","[('Augmentor Harness','ah'),('DSH','dsh'),('Pi (legacy profile)','pi'),('Codex (development)','codex')]"))
    edit('apps/native/augmentor_linux/agent_settings.py',lambda s:s.replace("return PromptClient().call('memory.dual.recall',{'session':harness+':'+sid}),None","return self.owner.prompt_client().call('memory.dual.recall',{'session':('pi' if harness=='ah' else harness)+':'+sid}),None"))
    for name in ['memory.py','dual_memory.py']:
        edit('apps/native/augmentor_linux/'+name,lambda s:s.replace('self.client=PromptClient()',"self.client=owner.prompt_client() if hasattr(owner,'prompt_client') else PromptClient()").replace('self.client = PromptClient()',"self.client = owner.prompt_client() if hasattr(owner,'prompt_client') else PromptClient()"))
    edit('apps/native/augmentor_linux/panels.py',lambda s:s.replace("engine.addItem('Pi','pi');","engine.addItem('Augmentor Harness','ah');engine.addItem('Pi (legacy profile)','pi');").replace("else 'Connect DSH')","else 'Connect a model' if getattr(window.controller,'harness',None) in ('pi','ah') else 'Connect DSH')"))
    def window(s):
        s=s.replace('    def bind_controller(self):','''    def prompt_client(self):
        from .prompt_client import PromptClient
        client=getattr(self.controller,'client',None)
        return client.prompt_client() if hasattr(client,'prompt_client') else PromptClient()

    def bind_controller(self):
        catalog=self.composer.prompt_menu.catalog
        catalog.generation+=1;catalog.pending=False;catalog.prompts=[];catalog.loaded=False;catalog.last_read=0
        catalog.client=self.prompt_client()''')
        return s.replace("settings=PromptClient().call('prompts.list').get('improvement')","settings=self.prompt_client().call('prompts.list').get('improvement')")
    edit('apps/native/augmentor_linux/window.py',window)
    edit('apps/browser/extension/settings.mjs',lambda s:s.replace("['pi','Pi'],['dsh'","['ah','Augmentor Harness'],['pi','Pi (legacy profile)'],['dsh'").replace("{dsh:'DSH',pi:'Pi',codex:'Codex'}","{dsh:'DSH',ah:'Augmentor Harness',pi:'Pi',codex:'Codex'}").replace("session:state.harness+':'+state.sessionId","session:(state.harness==='ah'?'pi':state.harness)+':'+state.sessionId"))
    edit('apps/browser/extension/panel-api.mjs',lambda s:s.replace("msg.type==='prompt/improve'&&(!['dsh','codex'].includes(state.harness)","msg.type==='prompt/improve'&&(!['dsh','ah','codex'].includes(state.harness)"))
    edit('apps/browser/native-host.mjs',lambda s:engines(s).replace("pi:'./pi-bridge.mjs',","pi:'./pi-bridge.mjs',ah:'./pi-bridge.mjs',"))
    def bridge(s):
        s=s.replace("process.env.AUGMENTOR_BROWSER_HARNESS!=='pi'","!['pi','ah'].includes(process.env.AUGMENTOR_BROWSER_HARNESS)")
        s=s.replace("const harness='pi'","const harness=process.env.AUGMENTOR_BROWSER_HARNESS??'pi'").replace("const preset='augmentor-browser-'+harness","const preset='augmentor-browser-pi'").replace("const workspace=","let workspace=")
        s=s.replace('connection=c;return c',"if(c.ah){workspace=c.ah.profile.workspace;Object.assign(process.env,{AUGMENTOR_SHARED_STATE:c.ah.profile.sharedState,AUGMENTOR_SHARED_DATA:c.ah.profile.sharedData,AUGMENTOR_PI_CONFIG:c.ah.profile.config,AUGMENTOR_PI_STATE:c.ah.profile.state})}connection=c;return c")
        s=s.replace('async function request(method,p={},id){',"async function request(method,p={},id){\n  if(harness==='ah'&&method!=='shutdown')await client()")
        # The old browser Improve prompt calls this existing surface operation.
        s=s.replace("if(method==='augmentor/surface'){", "if(method==='augmentor/surface'&&harness==='ah'&&p.action==='improve'){const c=await client(),library=await promptLibrary({action:'list'});if(!library.ok)throw Error(library.error);const requestId=crypto.randomUUID();return c.call('prompt.improve',{text:p.text,selection,requestId,scopeId:requestId,expectedInstructionsRevision:library.library.improvement.revision,...(currentSession?{sessionId:currentSession}:{})})}\n  if(method==='augmentor/surface'){")
        return s
    edit('apps/browser/pi-bridge.mjs',bridge)
    # Keep both original release/extension versions and the legacy Pi runtime.
    edit('dist/contracts/src/index.js',lambda s:s.replace('pi: {','ah: { branch: true, edit: true, memory: true }, pi: {',1))
    copies=['apps/native/augmentor_linux/pi_client.py','apps/native/augmentor_linux/prompt_client.py','apps/native/augmentor_linux/ah_connection.py','apps/native/augmentor_linux/adapters/ah.py','apps/native/augmentor_linux/platform_runtime.py','services/platform_adapters/__init__.py','services/platform_adapters/paths.py','services/platform_adapters/transport.py','scripts/ah-connection.py','dist/client/src/socket.js','dist/client/src/socket.js.map','dist/client/src/socket.d.ts','dist/platform/src/transport.js','dist/platform/src/transport.js.map','dist/platform/src/transport.d.ts']
    for name in copies:
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,target)
    # Recovery must use AH's existing launcher, never the legacy Pi starter.
    edit('services/recovery/__init__.py',lambda s:s.replace("elif harness == 'pi':","elif harness == 'ah':\n            client.ensure_running()\n            client.call('host.describe')\n        elif harness == 'pi':"))
    changed={}
    for p in out.rglob('*'):
        if p.is_file() and not p.is_symlink():
            rel=str(p.relative_to(out));prior=base/rel
            if not prior.exists() or p.read_bytes()!=prior.read_bytes():changed[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(baseArtifactSha256=BASE,files=changed,preservedVersion=json.loads((out/'package.json').read_text())['version'])


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('base',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    print(json.dumps(prepare(a.base.resolve(strict=True),Path(__file__).resolve().parents[1],a.out.resolve()),indent=2))
