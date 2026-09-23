// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {presentSettingsForm} from './settings-form.mjs'
export function dshSetupDialog(doc,send,container){
  if(doc.querySelector('.dsh-setup'))return
  const make=(tag,text)=>{const e=doc.createElement(tag);if(text)e.textContent=text;return e}
  const dialog=make('dialog');dialog.className='shared-prompt-editor memory-dialog dsh-setup'
  const intro=make('p','Connect a running local DSH 0.1.5-rc.1 web profile. Augmentor adds its Linux and browser roles, shared prompts and memory. Manage model providers in DSH. Both Augmentor interfaces share this connection.')
  const form=make('fieldset'),fields={}
  for(const [key,label] of [['endpoint','DSH URL'],['home','DSH data folder']]){
    const l=make('label',label),e=make('input');e.type='text';e.setAttribute('aria-label',label);l.append(e);form.append(l);fields[key]=e
  }
  const detail=make('p','Install integration adds Augmentor-owned presets and appends to the profile, keeping a backup. Running tasks must finish first. Restart DSH yourself after installation, then check again. Existing custom Augmentor integration requires migration.')
  const note=make('p','Loading connection…'),actions=make('div');let token=null,installed=false,busy=false,changing=false,closed=false
  const button=(label,fn)=>{const b=make('button',label);b.type='button';b.onclick=fn;actions.append(b);return b}
  const request=async(action,params={})=>{const r=await send('dshSetup',{request:{action,...params}});if(!r.ok)throw Error(r.error);return r.result}
  const controls=()=>{form.disabled=busy;check.disabled=busy;install.disabled=busy||!token||installed;save.disabled=busy||!token||!installed;later.disabled=changing}
  const run=async(action,p,callback)=>{busy=true;changing=['install','save'].includes(action);controls();try{const value=await request(action,p);if(!closed)callback(value)}catch(e){if(!closed)note.textContent=e.message}finally{busy=false;changing=false;if(!closed)controls()}}
  const later=button('Later',()=>dialog.close())
  const check=button('Check connection',()=>{token=null;note.textContent='Checking DSH and its integration…';return run('check',Object.fromEntries(Object.entries(fields).map(([k,e])=>[k,e.value])),value=>{token=value.token;installed=value.installed;note.textContent=value.message})})
  const install=button('Install integration',()=>run('install',{token},value=>{token=null;note.textContent=value.message}))
  const save=button('Save and use DSH',()=>run('save',{token},()=>dialog.close()))
  for(const e of Object.values(fields))e.oninput=()=>{token=null;controls()}
  dialog.append(make('h3','Connect DSH'),intro,form,detail,note,actions);doc.body.append(dialog)
  dialog.addEventListener('cancel',e=>{if(changing)e.preventDefault()});dialog.addEventListener('close',()=>{closed=true;dialog.remove()})
  presentSettingsForm(dialog,container);void run('describe',{},value=>{fields.endpoint.value=value.endpoint;fields.home.value=value.home;note.textContent='Check this connection before saving or installing the integration.'});return dialog
}
