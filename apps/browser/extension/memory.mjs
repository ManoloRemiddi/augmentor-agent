// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {presentSettingsForm} from './settings-form.mjs'
export function memoryDialog(doc,send,provenance,container){
  const dialog=doc.createElement('dialog');dialog.className='shared-prompt-editor memory-dialog'
  const make=(tag,text)=>{const e=doc.createElement(tag);if(text)e.textContent=text;return e}
  const intro=make('p','Relationship and work memory builds automatically from conversations. Hindsight maintains relationship pages and searchable project memory.')
  const automatic=make('fieldset'),autoNote=make('p','Loading automatic memory…'),autoContext=make('pre');autoContext.style.whiteSpace='pre-wrap';automatic.append(make('legend','Automatic continuity'),make('p','Transcripts are stored locally. Hindsight processes relationship and project context automatically, with durable retry. Voice brings relationship continuity into the conversation.'),autoNote,autoContext)
  const connection=make('fieldset'),legend=make('legend','Optional manual library connection'),fields={};connection.append(legend)
  for(const [id,label,placeholder] of [['endpoint','Endpoint','http://127.0.0.1:8888'],['apiKey','API key','Required for a remote service'],['userBank','User bank',''],['projectBank','Project bank (optional)','']]){
    const l=make('label',label),e=make('input');e.setAttribute('aria-label',label);e.placeholder=placeholder;e.type=id==='apiKey'?'password':'text';l.append(e);connection.append(l);fields[id]=e
  }
  const scope=make('select');scope.setAttribute('aria-label','Agent recall scope')
  const dataScope=make('select');dataScope.setAttribute('aria-label','Memory data scope')
  for(const select of [scope,dataScope])for(const id of ['user','project']){const option=make('option',id==='user'?'User':'Project');option.value=id;select.append(option)}
  const scopeLabel=make('label','Agent recall scope');scopeLabel.append(scope);connection.append(scopeLabel)
  connection.append(make('p','Requires Hindsight 0.9.2. Checking sends no chat history. Save enables recall. Retain sends only the text you enter below; Hindsight may charge for processing. The key is stored privately without encryption.'))
  const connectionActions=make('div'),data=make('fieldset');connection.append(connectionActions);data.append(make('legend','Memories'),dataScope)
  const text=make('textarea');text.rows=3;text.setAttribute('aria-label','Memory text');text.placeholder='Text to remember. Only this text will be retained.';data.append(text)
  const dataActions=make('div'),operationNote=make('p'),list=make('select'),contents=make('textarea'),pageNote=make('p');list.size=4;list.setAttribute('aria-label','Retained documents');contents.rows=4;contents.readOnly=true;contents.setAttribute('aria-label','Retained document text')
  data.append(dataActions,operationNote,list,contents,pageNote)
  const note=make('p','Loading memory settings…'),actions=make('div')
  dialog.append(make('h3','Memory'),intro,automatic,connection,data,note,actions);doc.body.append(dialog)
  let config={},token=null,busy=false,closed=false,rows=[],offset=0,total=0
  const button=(parent,label,fn)=>{const b=make('button',label);b.type='button';b.onclick=fn;parent.append(b);return b}
  const request=async(action,params={})=>{const r=await send('memory',{request:{action,...params}});if(!r.ok)throw Error(r.error);return r.result}
  let autoEnabled=true
  const loadAutomatic=async()=>{
    const value=await request('dual.describe');autoEnabled=!!value.enabled;autoToggle.textContent=autoEnabled?'Pause automatic memory':'Resume automatic memory';autoNote.textContent=(autoEnabled?'Automatic memory is on. ':'Automatic memory is paused. ')+`${value.events} transcript records; ${value.pending} memory scopes pending. ${value.message||''}`
    const source=provenance();if(source.sessionId){try{const context=await request('dual.recall',{session:source.harness+':'+source.sessionId});autoContext.textContent=['relationship','work'].map(kind=>kind+': '+(context[kind]?.summary||'No distilled picture yet.')).join('\n\n')}catch{autoContext.textContent='Remembered context appears after this conversation uses automatic memory.'}}
  }
  const autoToggle=button(automatic,'Pause automatic memory',async()=>{autoToggle.disabled=true;try{await request('dual.configure',{enabled:!autoEnabled});await loadAutomatic()}catch(e){autoNote.textContent=e.message}finally{autoToggle.disabled=false}})
  button(automatic,'Refresh remembered context',()=>{void loadAutomatic().catch(e=>autoNote.textContent=e.message)})
  void loadAutomatic().catch(()=>{autoNote.textContent='Automatic memory requires the updated Augmentor companion.'})
  const controls=()=>{connection.disabled=busy;data.disabled=busy;save.disabled=busy||!token;retain.disabled=busy||!config.enabled}
  const run=async(fn)=>{if(busy)return;busy=true;controls();try{await fn()}catch(e){note.textContent=e.message}finally{busy=false;controls()}}
  const invalidate=()=>{token=null;controls()};for(const e of [...Object.values(fields),scope])e.addEventListener('input',invalidate)
  const loadConfig=async()=>{
    config=await request('describe');token=null
    for(const id of ['endpoint','projectBank'])fields[id].value=config[id]??''
    fields.userBank.value=config.userBank??'augmentor-user-'+crypto.randomUUID().slice(0,12)
    fields.apiKey.value='';fields.apiKey.placeholder=config.apiKeySet?'Stored key kept if left blank':'Required for a remote service'
    scope.value=config.activeScope??'user';dataScope.value=scope.value
    note.textContent=config.enabled?'Hindsight memory enabled.':'Hindsight memory disabled.'
  }
  const operations=async()=>{
    const value=await request('operations',{scope:dataScope.value})
    const pending=value.items.find(r=>!['completed','failed','cancelled','deleted'].includes(r.status))
    if(pending){const result=await request('operation',{scope:dataScope.value,id:pending.id});Object.assign(pending,result)}
    operationNote.textContent=value.items.slice(0,4).map(r=>r.document.slice(-12)+': '+r.status).join('\n')
  }
  const refresh=async()=>{
    if(!config.endpoint)return
    const value=await request('documents',{scope:dataScope.value,offset});rows=value.items;total=value.total;list.replaceChildren();contents.value=''
    for(const row of rows){const option=make('option',row.id+' · '+row.memory_unit_count+' facts');option.value=row.id;list.append(option)}
    list.selectedIndex=-1;pageNote.textContent=`Showing ${rows.length?offset+1:0}–${offset+rows.length} of ${total} documents.`;await operations()
  }
  button(connectionActions,'Check connection',()=>run(async()=>{token=null;const result=await request('check',{...Object.fromEntries(Object.entries(fields).map(([k,e])=>[k,e.value])),activeScope:scope.value});token=result.token;note.textContent='Connection verified. Save to enable memory.'}))
  const save=button(connectionActions,'Save and enable',()=>run(async()=>{await request('configure',{token});await loadConfig();offset=0;await refresh()}))
  button(connectionActions,'Disable memory',()=>run(async()=>{await request('disable');await loadConfig()}))
  connection.append(make('p','Disable stops new recall and retention. Submitted operations may finish. Retained data stays available for view, export and deletion.'))
  const retain=button(dataActions,'Retain this text',()=>run(async()=>{
    if(!text.value.trim())throw Error('Enter the text to retain.')
    const value=await request('retain',{scope:dataScope.value,content:text.value,provenance:provenance(),requestId:crypto.randomUUID()})
    text.value='';note.textContent=value.status==='pending'?'Retention queued. Refresh to check completion.':'Retention outcome is unknown. Refresh its status before saving again.';await operations()
  }))
  button(dataActions,'Refresh',()=>run(refresh))
  button(dataActions,'Previous',()=>run(async()=>{offset=Math.max(0,offset-20);await refresh()}))
  button(dataActions,'Next',()=>run(async()=>{if(offset+rows.length<total){offset+=20;await refresh()}}))
  list.onchange=()=>run(async()=>{const value=await request('document',{scope:dataScope.value,id:list.value});contents.value=value.original_text??'(No source text)'})
  dataScope.onchange=()=>run(async()=>{offset=0;await refresh()})
  button(dataActions,'Delete selected',()=>run(async()=>{
    if(!list.value)return
    if(!doc.defaultView.confirm('Delete this source document and its associated memories from Hindsight?'))return
    await request('delete',{scope:dataScope.value,id:list.value});await refresh();note.textContent='Memory document deleted.'
  }))
  button(dataActions,'Export facts',()=>run(async()=>{
    const facts=[];let next=0
    while(true){const page=await request('exportPage',{scope:dataScope.value,offset:next});facts.push(...page.items);next+=page.items.length;if(next>=page.total)break;if(!page.items.length)throw Error('Memory changed during export. Please try again.')}
    const url=URL.createObjectURL(new Blob([JSON.stringify({provider:'hindsight',scope:dataScope.value,facts},null,2)],{type:'application/json'}));const a=make('a');a.href=url;a.download='augmentor-memory.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);note.textContent='Memory facts exported.'
  }))
  button(actions,'Done',()=>dialog.close())
  dialog.addEventListener('close',()=>{closed=true;fields.apiKey.value='';dialog.remove()})
  dialog.addEventListener('cancel',()=>{if(busy)note.textContent='Submitted operations remain available in Memory.'})
  presentSettingsForm(dialog,container);void run(async()=>{await loadConfig();if(!closed)await refresh()});return dialog
}
