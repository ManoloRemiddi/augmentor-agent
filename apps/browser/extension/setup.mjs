// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {presentSettingsForm} from './settings-form.mjs'
export function modelSetupDialog(doc,send,container){
  if(doc.querySelector('.model-setup'))return
  const make=(tag,text)=>{const e=doc.createElement(tag);if(text)e.textContent=text;return e}
  const dialog=make('dialog');dialog.className='shared-prompt-editor memory-dialog model-setup'
  const intro=make('p','Connect your own OpenAI-compatible endpoint. The connection is shared with Augmentor Agent. The check sends one short message and, if selected, a generated test image, without tools, files or history. Your provider may charge for it. The key is stored in private user configuration without encryption.')
  intro.textContent='Enter your provider’s endpoint and model. Check the connection, then save.'
  const form=make('fieldset');form.append(make('legend','Pi model connection'))
  const fields={}
  for(const [key,label,value,type,min,max] of [['name','Connection name','My model','text'],['baseUrl','Endpoint URL','','url'],['apiKey','API key','','password'],['model','Model ID','','text'],['contextWindow','Context limit (tokens)',32768,'number',1024,10000000],['maxTokens','Response limit (tokens)',4096,'number',32,1000000]]){
    const l=make('label',label),e=make('input');e.type=type;e.value=value;e.setAttribute('aria-label',label);if(min)e.min=min;if(max)e.max=max;l.append(e);form.append(l);fields[key]=e
  }
  fields.baseUrl.placeholder='https://your-provider.example/v1';fields.apiKey.placeholder='Optional for a model on this computer'
  const imageLabel=make('label','Model accepts images'),images=make('input');images.type='checkbox';images.setAttribute('aria-label','Model accepts images');imageLabel.append(images);form.append(imageLabel);fields.images=images
  const mode=make('select');mode.setAttribute('aria-label','Approval mode')
  for(const [value,label] of [['workspace-write','Ask before changes'],['read-only','Read only'],['danger-full-access','Allow actions without asking']]){const o=make('option',label);o.value=value;mode.append(o)}
  const modeLabel=make('label','Approval mode');modeLabel.append(mode);form.append(modeLabel)
  const explanation=make('p');form.append(explanation)
  mode.onchange=()=>{explanation.textContent={ 'workspace-write':'Routine observations run directly. Actions that can change files or applications require approval.', 'read-only':'Tools that can change state are blocked. This is a tool policy, not an operating-system sandbox.', 'danger-full-access':'Tools act within their environment without further approval. Stop remains available.'}[mode.value]};mode.onchange()
  const note=make('p','Enter the limits published by your provider. Select image input for desktop screenshots. This checks accepted formats; visual reasoning needs separate testing.'),actions=make('div')
  let token=null,busy=false,saving=false,closed=false
  const button=(label,fn)=>{const b=make('button',label);b.type='button';b.onclick=fn;actions.append(b);return b}
  const request=async(action,params={})=>{const r=await send('modelSetup',{action,params});if(!r.ok)throw Error(r.error);return r.result}
  const controls=()=>{form.disabled=busy;check.disabled=busy;save.disabled=busy||!token;later.disabled=saving}
  const run=async(fn)=>{busy=true;controls();try{await fn()}catch(e){if(!closed)note.textContent=e.message}finally{busy=false;saving=false;if(!closed)controls()}}
  for(const e of Object.values(fields))e.oninput=()=>{token=null;controls()}
  const later=button('Later',()=>dialog.close())
  const check=button('Check connection',()=>run(async()=>{
    token=null;note.textContent='Checking the model connection…'
    const p=Object.fromEntries(Object.entries(fields).map(([k,e])=>[k,e.type==='checkbox'?e.checked:e.type==='number'?Number(e.value):e.value]));p.api='openai-completions'
    const result=await request('test',p);if(closed)return;token=result.token;note.textContent='Connection verified. Save to use this model.'
  }))
  const save=button('Save and use model',()=>{saving=true;return run(async()=>{await request('save',{token,approvalMode:mode.value});dialog.close()})})
  if(container){
    const detail=make('details'),summary=make('summary','Advanced');detail.className='advanced';detail.append(summary)
    for(const key of ['name','contextWindow','maxTokens','images'])detail.append(fields[key].parentElement)
    detail.append(modeLabel,explanation);form.append(detail)
    note.textContent='Connection checks send a short test request to your provider.'
  }
  dialog.append(make('h3','Connect a model · Pi'),intro,form,note,actions);doc.body.append(dialog)
  dialog.addEventListener('cancel',e=>{if(saving)e.preventDefault()})
  dialog.addEventListener('close',()=>{closed=true;fields.apiKey.value='';if(!saving)void request('cancel').catch(()=>{});dialog.remove()})
  presentSettingsForm(dialog,container);controls();return dialog
}
