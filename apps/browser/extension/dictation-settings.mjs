// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

export async function dictationSettings(container,send){
  const make=(tag,text)=>{const el=document.createElement(tag);if(text)el.textContent=text;return el}
  const call=async(method,params={})=>{const r=await send('surface/dictation',{method,params});if(!r?.ok)throw Error(r?.error||'System dictation unavailable');return r.result}
  const label=(text,input)=>{const row=make('label',text);row.append(input);container.append(row);return input}
  container.append(make('h2','Handy · built into Augmentor'),make('p','Local transcription into the focused application. The recording pill follows your Augmentor colours and animation settings.'))
  const enabled=label('Enable system dictation',make('input'));enabled.type='checkbox'
  const note=make('p');note.setAttribute('role','status');container.append(note)
  const shortcut=label('Activation shortcut',make('input'));shortcut.value='ctrl+space'
  const activation=label('Activation',make('select'))
  for(const [value,text] of [['push_to_talk','Hold to talk'],['toggle','Press to start / stop']]){const option=make('option',text);option.value=value;activation.append(option)}
  const models=label('Transcription model',make('select'))
  const terms=make('p');container.append(terms)
  const reviewed=label('I reviewed the selected model publisher terms before downloading',make('input'));reviewed.type='checkbox'
  const microphone=label('Microphone',make('select')),language=label('Recognition language',make('select'))
  const translate=label('Translate to English (supported models)',make('input'));translate.type='checkbox'
  const paste=label('Insert text',make('select'))
  for(const [value,text] of [['ctrl_v','Paste · Ctrl+V'],['ctrl_shift_v','Terminal paste · Ctrl+Shift+V'],['shift_insert','Paste · Shift+Insert'],['direct','Type directly'],['none','Copy only']]){const option=make('option',text);option.value=value;paste.append(option)}
  const clipboard=label('Leave transcription on the clipboard',make('input'));clipboard.type='checkbox'
  const history=label('Recordings to keep',make('input'));history.type='number';history.min='0';history.max='100';history.value='5'
  let snapshot={},busy=false,closed=false,dirty=false,savedRevision=null,rows=[]
  for(const control of [shortcut,activation,microphone,language,translate,paste,clipboard,history])control.addEventListener('input',()=>{dirty=true})
  const showTerms=()=>{
    const row=rows.find(row=>row.id===models.value);terms.replaceChildren()
    if(!row)return
    terms.append(document.createTextNode((row.license||'Publisher terms')+' · '))
    for(const [url,text] of [[row.model_card,'Model card and terms'],[row.base_model_card,'Original model terms']])if(url){const a=make('a',text);a.href=url;a.target='_blank';a.rel='noopener noreferrer';terms.append(a,document.createTextNode(' '))}
  }
  models.addEventListener('change',()=>{reviewed.checked=false;showTerms()})
  const buttons=[]
  const button=(text,fn)=>{const b=make('button',text);b.type='button';b.onclick=()=>void operate(fn,true);container.append(b);buttons.push(b)}
  const refresh=async()=>{
    snapshot=await call('status');enabled.checked=snapshot.enabled;note.textContent=snapshot.error||snapshot.phase+(snapshot.shortcut_description?' · '+snapshot.shortcut_description:'')
    if(snapshot.installed===false)return
    rows=await call('models');snapshot=await call('status');const selected=models.value||snapshot.settings?.model;models.replaceChildren()
    for(const row of rows){const option=make('option',row.name+' · '+(row.installed?'Installed':row.downloading?'Downloading':row.size_mb+' MB'));option.value=row.id;models.append(option)}
    if(selected)models.value=selected
    showTerms()
    if(!dirty){
      shortcut.value=snapshot.settings?.shortcut||'ctrl+space';activation.value=snapshot.settings?.activation||'push_to_talk';savedRevision=snapshot.revision
      const devices=await call('devices');microphone.replaceChildren(make('option','System default'));microphone.firstChild.value=''
      for(const device of devices){const option=make('option',device.name);option.value=device.name;microphone.append(option)}
      microphone.value=snapshot.settings?.microphone||''
      language.replaceChildren(make('option','Automatic'));language.firstChild.value='auto'
      for(const value of [...new Set(rows.flatMap(row=>row.languages))].sort()){const option=make('option',value);option.value=value;language.append(option)}
      language.value=snapshot.settings?.language||'auto';translate.checked=snapshot.settings?.translate===true
      paste.value=snapshot.settings?.paste_method||'ctrl_v';clipboard.checked=(snapshot.settings?.clipboard||'copy_to_clipboard')==='copy_to_clipboard'
      history.value=String(snapshot.settings?.history_limit??5)
    }
  }
  async function operate(fn,mutation=false){
    if(busy||closed)return;busy=true;enabled.disabled=true;for(const b of buttons)b.disabled=true
    const controls=[shortcut,activation,microphone,language,translate,paste,clipboard,history,models]
    if(mutation)for(const control of controls)control.disabled=true
    try{await fn();await refresh()}catch(error){note.textContent=error.message}finally{busy=false;enabled.disabled=false;for(const b of buttons)b.disabled=false;for(const control of controls)control.disabled=false}
  }
  enabled.onchange=()=>void operate(()=>call('enable',{enabled:enabled.checked}),true)
  button('Save dictation settings',async()=>{await call('settings',{revision:savedRevision,values:{shortcut:shortcut.value,activation:activation.value,microphone:microphone.value||null,language:language.value,translate:translate.checked,paste_method:paste.value,clipboard:clipboard.checked?'copy_to_clipboard':'dont_modify',history_limit:Number(history.value),retention:'preserve_limit'}});dirty=false})
  button('Download model',()=>{if(!reviewed.checked)throw Error('Review the linked model terms and check the confirmation first.');return call('model.download',{id:models.value,terms_reviewed:true})})
  button('Cancel download',()=>call('model.cancel',{id:models.value}))
  button('Use model',()=>call('model.select',{id:models.value}))
  button('Cancel dictation',()=>call('cancel'))
  button('Reload saved settings',async()=>{dirty=false;models.value=''})
  container.append(make('p','Hold Ctrl+Space, speak, then release to transcribe and paste. Escape or × cancels. Model downloads have their own licenses.'))
  await operate(async()=>{})
  const timer=setInterval(()=>void operate(async()=>{}),2000)
  window.addEventListener('pagehide',()=>{closed=true;clearInterval(timer)},{once:true})
}
