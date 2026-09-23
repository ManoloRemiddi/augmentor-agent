// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

import {presentSettingsForm} from './settings-form.mjs'
export function promptEditor(doc,request,onSaved,container){
  const dialog=doc.createElement('dialog');dialog.className='shared-prompt-editor';
  const make=(tag,text)=>{const e=doc.createElement(tag);if(text)e.textContent=text;return e}
  const title=make('h3','Prompt library'),list=make('select'),name=make('input'),body=make('textarea'),note=make('p'),actions=make('div')
  list.size=5;list.setAttribute('aria-label','Saved prompts');name.placeholder='Shortcut name';name.setAttribute('aria-label','Prompt name');body.setAttribute('aria-label','Prompt text');body.rows=8
  const button=(text,fn)=>{const b=make('button',text);b.type='button';b.onclick=fn;actions.append(b);return b}
  const sections=make('div'),saved=make('div'),improvement=make('div');improvement.hidden=true
  let current=null,improvementBusy=false
  const instructions=make('textarea');instructions.rows=12;instructions.maxLength=8000;instructions.setAttribute('aria-label','Prompt improvement instructions')
  const improvementNote=make('p');improvementNote.setAttribute('role','status')
  improvement.append(make('p','Instructions for ✦ Improve prompt in the input box. Edit these independently of your saved /prompts.'),instructions,improvementNote)
  const improvementActions=make('div');improvement.append(improvementActions)
  const control=(label,fn)=>{const b=make('button',label);b.type='button';b.onclick=fn;improvementActions.append(b);return b}
  const applyImprovement=value=>{if(!value){improvementNote.textContent='Restart the prompt service to load these settings.';return}current=value;instructions.value=value.content}
  control('Save instructions',async()=>{
    if(!current||improvementBusy)return
    improvementBusy=true;instructions.disabled=true;for(const b of improvementActions.children)b.disabled=true
    try{const value=await request({action:'improvement.save',content:instructions.value,expectedRevision:current.revision});current=value.improvement;onSaved(value);improvementNote.textContent='Instructions saved.'}
    catch(e){improvementNote.textContent=e.message}
    finally{improvementBusy=false;instructions.disabled=false;for(const b of improvementActions.children)b.disabled=false}
  })
  control('Reload',async()=>{try{applyImprovement((await request({action:'list'})).improvement);improvementNote.textContent='Latest instructions loaded.'}catch(e){improvementNote.textContent=e.message}})
  control('Use default',()=>{if(current){instructions.value=current.defaultContent;improvementNote.textContent='Default loaded. Save to apply it.'}})
  for(const [label,target] of [['Saved prompts',saved],['Improve prompt',improvement]]){const b=make('button',label);b.type='button';b.setAttribute('aria-pressed',String(target===saved));b.onclick=()=>{saved.hidden=target!==saved;improvement.hidden=target!==improvement;for(const item of sections.children)item.setAttribute('aria-pressed',String(item===b))};sections.append(b)}
  let rows=[],selected=null,busy=false
  const error=e=>{note.textContent=e.message}
  const load=async()=>{const value=await request({action:'list'});rows=value.prompts;if(!current)applyImprovement(value.improvement);list.replaceChildren();for(const row of rows){const option=make('option','/'+row.name);option.value=row.id;list.append(option)}list.value=selected?.id??'';return value}
  const select=()=>{selected=rows.find(r=>r.id===list.value)??null;name.value=selected?.name??'';body.value=selected?.content??'';note.textContent=''}
  list.onchange=select
  button('New',()=>{selected=null;list.value='';name.value='';body.value='';name.focus()})
  button('Insert clipboard',()=>{body.setRangeText('[clipboard]',body.selectionStart,body.selectionEnd,'end');body.focus()})
  const mutate=async action=>{
    if(busy)return;if(action==='delete'&&!selected)return
    if(action==='delete'&&!doc.defaultView.confirm('Delete /'+selected.name+'?'))return
    busy=true;for(const b of [...actions.children,name,body,list])b.disabled=true
    try{
      const value=await request({action,id:selected?.id,expectedRevision:selected?.revision,name:name.value.trim(),content:body.value})
      onSaved(value);await load();selected=null;list.value='';name.value='';body.value='';note.textContent=action==='save'?'Prompt saved.':'Prompt deleted.'
    }catch(e){error(e)}finally{busy=false;for(const b of [...actions.children,name,body,list])b.disabled=false}
  }
  button('Save',()=>mutate('save'));button('Delete',()=>mutate('delete'))
  button('Refresh',()=>load().then(()=>{note.textContent='Library refreshed. Your draft is preserved; select a prompt to load its latest version.'}).catch(error))
  button('Reload selected',()=>load().then(select).catch(error))
  button('Done',()=>dialog.close())
  saved.append(list,name,body,actions,note);dialog.append(title,sections,saved,improvement);const done=make('button','Done');done.type='button';done.onclick=()=>dialog.close();improvement.append(done);doc.body.append(dialog)
  const poll=doc.defaultView.setInterval(()=>{if(!busy)load().catch(error)},1500)
  dialog.addEventListener('close',()=>{doc.defaultView.clearInterval(poll);dialog.remove()});presentSettingsForm(dialog,container);load().catch(error)
  return dialog
}
