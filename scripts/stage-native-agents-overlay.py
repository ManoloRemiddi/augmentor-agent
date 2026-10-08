#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Apply the named-agent feature to a COPY of the compatible Linux artifact.

The selected artifact is immutable. Use augmentor-update stage/activate afterward.
The candidate keeps the approved identity UI and existing dependency contract.
"""
import argparse
from pathlib import Path
import shutil

SOURCE=Path(__file__).resolve().parents[1]

def replace(path,old,new):
    text=path.read_text()
    if text.count(old)<1:raise ValueError('Overlay baseline differs: '+str(path)+' / '+old[:60])
    path.write_text(text.replace(old,new))

def overlay(base,candidate):
    base=Path(base).resolve();candidate=Path(candidate).resolve()
    if candidate.exists() or candidate==base or candidate.is_relative_to(base):raise ValueError('Choose a new candidate outside the immutable release.')
    shutil.copytree(base,candidate,symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for file in ['apps/native/augmentor_linux/agent_entries.py','apps/native/augmentor_linux/agents_settings.py','apps/native/augmentor_linux/instances.py','apps/native/augmentor_linux/shortcuts.py','services/dsh/desktop-entries.mjs','docs/DESKTOP-AGENTS.md','adapters/dsh-product/exact-fork.mjs','adapters/dsh-product/interactions.mjs']:
        target=candidate/file;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE/file,target)
    for name in ('dsh-preset-boundary','dsh-preset-environment','dsh-preset-file'):shutil.copytree(SOURCE/'adapters'/name,candidate/'adapters'/name)
    # Preserve the selected normal-agent access initialization; custom agents cannot invoke it.
    adapter=candidate/'apps/native/augmentor_linux/adapters/dsh.py'
    original=adapter.read_text();start=original.index('    def setting(self, namespace):');end=original.index('    def owns_preset',start)
    setting=original[start:end].replace("namespace=='permission' and self.product", "namespace=='permission' and self.product and not self.custom")
    setting=setting.replace('    def setting(self, namespace):',"    def setting(self, namespace):\n        if self.custom and namespace=='permission':return None")
    adapter_source=(SOURCE/adapter.relative_to(candidate)).read_text()
    source_start=adapter_source.index('    def setting(self,namespace):');source_end=adapter_source.index('    def check_entry',source_start)
    adapter_source=adapter_source[:source_start]+setting+adapter_source[source_end:]
    adapter.write_text(adapter_source.replace("if method=='session.create':p=", "if method=='session.create' and self.product and not self.custom:self.setting('permission')\n        if method=='session.create':p=",1))
    controller=candidate/'apps/native/augmentor_linux/controller.py'
    replace(controller,'    def save_session(self):',"        if self.session is None and isinstance(getattr(self.client,'initial_selection',None),dict):self.selection=dict(self.client.initial_selection)\n\n    def save_session(self):")
    text=controller.read_text().replace("getattr(self.client,'owns_preset',lambda preset:preset==self.preset)(row.get('agentPreset'))", "getattr(self.client,'owns_session',lambda r:getattr(self.client,'owns_preset',lambda preset:preset==self.preset)(r.get('agentPreset')))(row)")
    text=text.replace("            if provider not in ('local','openai-live')", "            if getattr(self.client,'supports_voice',True) is False:raise ContractError('Voice chat is unavailable for this independent DSH agent. Use typed chat or dictation.')\n            if provider not in ('local','openai-live')")
    controller.write_text(text)
    prefs=candidate/'apps/native/augmentor_linux/preferences.py'
    replace(prefs,'        if fresh_secondary and persistent:self.save()',"        if fresh_secondary and persistent:self.save()\n        from .agent_entries import get\n        if (get() or {}).get('preset'):self.values['harness']='dsh'")
    window=candidate/'apps/native/augmentor_linux/window.py'
    replace(window,'    def switch_harness(self,harness,reconnect=False):',"    def switch_harness(self,harness,reconnect=False):\n        from .agent_entries import get\n        if harness!='dsh' and (get() or {}).get('preset'):\n            self.set_status('This entry uses an independent DSH agent. Choose Augmentor in Settings → Agents before switching harness.');return")
    text=window.read_text();old=next(line for line in text.splitlines() if 'self.voice_button.setEnabled(' in line)
    replace(window,old,old.replace('setEnabled(',"setEnabled(getattr(getattr(self.controller,'client',None),'supports_voice',True) is not False and (",1)+')')
    replace(window,"hasattr(getattr(self.controller,'client',None),'improve_prompt')","hasattr(getattr(self.controller,'client',None),'improve_prompt') and getattr(getattr(self.controller,'client',None),'supports_prompt_improvement',True) is not False")
    replace(window,'    def open_access(self):',"    def open_access(self):\n        if self.controller and getattr(self.controller.client,'custom',False):\n            self.set_status('DSH owns this independent agent’s permissions. Edit its preset in DSH.');return")
    history=candidate/'apps/native/augmentor_linux/panels.py'
    replace(history,'filters.addWidget(self.saved);filters.addWidget(self.all);layout.addLayout(filters)',"filters.addWidget(self.saved);filters.addWidget(self.all);layout.addLayout(filters)\n        from .agent_entries import read\n        if getattr(getattr(window.controller,'client',None),'custom',False) or read()['retained']:self.all.show()")
    replace(history,"if not self.all.isChecked() and row.get('agentPreset')!=getattr(self.owner.controller,'preset','augmentor-linux-pi'):continue", "if not self.all.isChecked() and not getattr(getattr(self.owner.controller,'client',None),'owns_session',lambda r:r.get('agentPreset')==getattr(self.owner.controller,'preset','augmentor-linux-pi'))(row):continue")
    shortcuts=candidate/'apps/native/augmentor_linux/shortcut_settings.py'
    replace(shortcuts,"for name,label in [('main','First agent'),('secondary','Second agent')]:","for name,label in [(e['id'],e['name']) for e in __import__(__package__+'.agent_entries',fromlist=['entries']).entries()]:")
    product=candidate/'adapters/dsh-product/index.mjs'
    replace(product,"import {ownsProductSession,profileForSession,profiles} from '../../services/workspaces/profiles.mjs'", "import {profiles} from '../../services/workspaces/profiles.mjs'\nimport {ownsNativeSession} from '../../services/dsh/desktop-entries.mjs'")
    replace(product,'nativeInteractions:1','nativeInteractions:1,desktopAgents:1')
    replace(product,'.filter(row=>ownsProductSession(row))','.filter(row=>ownsNativeSession(row,{retained:true}))')
    branch=candidate/'services/dsh/branch.py'
    replace(branch,'def branch(call, params, *, surface, endpoint, state=None, exact_fork=None):','def branch(call, params, *, surface, endpoint, state=None, exact_fork=None, allowed_presets=None, required_cwd=None):')
    replace(branch,"            allowed = ('augmentor-linux-product','augmentor-browser-product', 'augmentor-linux' if surface == 'linux' else 'augmentor')", "            allowed = allowed_presets or ('augmentor-linux-product','augmentor-browser-product', 'augmentor-linux' if surface == 'linux' else 'augmentor')\n            if required_cwd and (row is None or Path(row.get('cwd','')).resolve()!=Path(required_cwd).resolve()):raise BranchError('This chat belongs to another working folder.')")
    panel=candidate/'apps/native/augmentor_linux/agent_settings.py'
    replace(panel,"entries=[('Prompt library',self.open_prompts)","entries=[('Agents · named windows',lambda:self.show_page('agents')),('Prompt library',self.open_prompts)")
    replace(panel,'    def page_all(self):',"    def page_agents(self):\n        from .agents_settings import AgentsSettings\n        page,layout=self.make_page('Agents','Named windows connected to your DSH agents.')\n        self.agents=AgentsSettings(self.owner);layout.addWidget(self.agents);layout.addStretch();return page\n\n    def page_all(self):")
    replace(panel,'    def page_agent(self):',"    def page_agent(self):\n        if getattr(self.owner.controller.client,'custom',False):\n            from .agent_entries import get\n            entry=get();page,layout=self.make_page(entry['name'],'DSH owns this agent’s instructions, tools, skills and permissions.')\n            self.action(layout,'Agents · edit this entry',lambda:self.show_page('agents'))\n            note=QLabel('Augmentor personal identity, memory and conversational voice are unavailable for independent agents. Typed chat and dictation remain available.');note.setWordWrap(True);layout.addWidget(note);layout.addStretch();return page\n        return self.page_personal_agent()\n\n    def page_personal_agent(self):")
    replace(panel,'        self.avatar.sync_motion();self.sync_navigation();QTimer.singleShot(0,self.request_fit)',"        if hasattr(self,'avatar'):self.avatar.sync_motion()\n        self.sync_navigation();QTimer.singleShot(0,self.request_fit)")
    replace(panel,'    def open_memory_settings(self):',"    def open_memory_settings(self):\n        if getattr(self.owner.controller.client,'custom',False):self.feedback.setText('Personal memory is unavailable for independent DSH agents.');return\n        return self.open_personal_memory_settings()\n\n    def open_personal_memory_settings(self):")
    replace(panel,'    def open_voice(self):',"    def open_voice(self):\n        if getattr(self.owner.controller.client,'custom',False):self.feedback.setText('Conversational voice is unavailable for independent DSH agents. Use dictation.');return\n        return self.open_personal_voice()\n\n    def open_personal_voice(self):")
    replace(panel,"        return self.shortcuts.capture_current() if self.shortcuts else False", "        return (self.agents.capture_current() if hasattr(self,'agents') and self.agents.isVisible() else False) or (self.shortcuts.capture_current() if self.shortcuts else False)")
    replace(panel,'        self.save_name(); self.closing=True;',"        if hasattr(self,'name'):self.save_name()\n        self.closing=True;")
    return candidate

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('base');parser.add_argument('candidate');args=parser.parse_args()
    print(overlay(args.base,args.candidate))
