// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {presentSettingsForm} from './settings-form.mjs'

export function codexSetupDialog(doc,send,container){
  const make=(tag,text)=>{const e=doc.createElement(tag);if(text)e.textContent=text;return e}
  const dialog=make('dialog');dialog.className='shared-prompt-editor memory-dialog codex-setup'
  const form=make('fieldset'),fields={}
  for(const [name,label,type] of [['profile','Saved connection','select'],['kind','Connection type','select'],['name','Connection name','text'],['endpoint','Endpoint URL','url'],['model','Model ID','text'],['credential','API key','password'],['remove','Remove the saved key','checkbox']]){
    const row=make('label',label),input=make(type==='select'?'select':'input');if(type!=='select')input.type=type
    input.setAttribute('aria-label',label);row.append(input);form.append(row);fields[name]=input
  }
  for(const [value,label] of [['api','API provider'],['local','Local model']]){const option=make('option',label);option.value=value;fields.kind.append(option)}
  fields.credential.placeholder='Optional; blank keeps the saved key'
  fields.endpoint.placeholder='https://provider.example/v1 or http://127.0.0.1:8080/v1'
  const note=make('p'),actions=make('div');note.setAttribute('role','status')
  let rows=[],profileId=null,busy=false,dirty=false,closed=false
  const request=async payload=>{const result=await send('codexSetup',{request:payload});if(!result.ok)throw Error(result.error);return result.result}
  const controls=()=>{form.disabled=busy;save.disabled=busy;check.disabled=busy||dirty||!profileId;imageCheck.disabled=check.disabled;close.disabled=busy}
  const button=(label,fn)=>{const b=make('button',label);b.type='button';b.onclick=fn;actions.append(b);return b}
  const run=async fn=>{if(busy)return;busy=true;controls();try{await fn()}catch(error){if(!closed)note.textContent=error.message}finally{busy=false;if(!closed)controls()}}
  const selected=()=>{
    profileId=fields.profile.value||null;const row=rows.find(row=>row.id===profileId)||{}
    fields.name.value=row.name||'My Codex model';fields.kind.value=row.kind||'api';fields.endpoint.value=row.endpoint||'';fields.model.value=row.model||'';fields.credential.value='';fields.remove.checked=false;dirty=false
    note.textContent=row.toolsVerified?'Codex tool check passed for this connection.':row.imageValidatedAt?'Image response checked; screenshots are available in new chats.':row.validation==='responses-text'?'Text response checked; tool compatibility is not verified.':'Save a connection, then check it with Codex.';controls()
  }
  const load=async()=>{
    rows=(await request({action:'profiles'})).profiles
    fields.profile.replaceChildren();for(const row of [{id:'',name:'New connection'},...rows]){const option=make('option',row.name);option.value=row.id;fields.profile.append(option)}
    fields.profile.value=profileId||'';selected()
  }
  const close=button('Close',()=>dialog.close())
  const check=button('Check Codex connection',()=>run(async()=>{note.textContent='Checking Codex chat and tool support…';await request({action:'test',id:profileId,capability:'agent'});note.textContent='Codex chat and the test tool worked. Browser and desktop tasks still need their own checks.'}))
  const imageCheck=button('Check image response',()=>run(async()=>{note.textContent='Checking a synthetic image…';await request({action:'test',id:profileId,capability:'image'});await load();note.textContent='Image response verified. Start a new chat to use browser screenshots. General vision and tool accuracy still need a chat test.'}))
  const save=button('Save connection',()=>run(async()=>{
    const profile={id:profileId||crypto.randomUUID(),kind:fields.kind.value,name:fields.name.value.trim(),endpoint:fields.endpoint.value.trim(),model:fields.model.value.trim()}
    if(fields.remove.checked)profile.credential=null;else if(fields.credential.value)profile.credential=fields.credential.value
    note.textContent='Saving connection…';const row=await request({action:'configure',profile});profileId=row.id;fields.credential.value=''
    await load();const refreshed=await send('models-refresh');if(!refreshed.ok)throw Error('Connection saved. Refresh the model picker to use it. '+(refreshed.error||''))
  }))
  for(const [key,field] of Object.entries(fields)){if(key==='profile')continue;field.oninput=()=>{dirty=true;controls()}}
  fields.profile.onchange=selected
  dialog.append(make('h3','Connect a model · Codex'),make('p','Use a Responses-compatible API provider or local model. Subscription sign-in is not available in this development build.'),form,make('p','Keys are stored in the operating system credential store. Checks send a short tool exercise or a synthetic image that your provider may charge for. The Codex check uses one harmless test tool and sends no personal files or chat history. The image check enables screenshots for new chats.'),note,actions)
  dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault()})
  dialog.addEventListener('close',()=>{closed=true;fields.credential.value='';dialog.remove()})
  doc.body.append(dialog);presentSettingsForm(dialog,container);void run(load);return dialog
}
