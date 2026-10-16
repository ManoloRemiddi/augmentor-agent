// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useEffect,useRef,useState} from 'react';
import {Button} from '@deepseek-ai/dsh-client-ui-primitives';
import './plugins.css';
const empty=()=>({id:null,name:'',content:'',revision:undefined});
/** Editor for the same revisioned service used by Native, Browser and DSH.
 * Reads never replace edits; unknown mutation outcomes are never retried. */
export function PromptLibraryContent({controller,onUse,initialTab='saved',onDirtyChange=()=>{}}){
 const [tab,setTab]=useState(initialTab),[library,setLibrary]=useState(null),[form,setForm]=useState(empty),[editing,setEditing]=useState(false),[dirty,setDirty]=useState(false),[query,setQuery]=useState('');
 const [instructions,setInstructions]=useState(null),[text,setText]=useState(''),[instructionsDirty,setInstructionsDirty]=useState(false);
 const [note,setNote]=useState('Loading shared library…'),[busy,setBusy]=useState(false),[confirmation,setConfirmation]=useState(null);
 const confirmRef=useRef(null);useEffect(()=>{if(confirmation)confirmRef.current?.focus();},[confirmation]);
 const gate=useRef(false),life=useRef(0),body=useRef(null),draft=useRef({});draft.current={dirty,instructionsDirty};
 const writable=controller.state.phase==='ready'&&!controller.state.readOnly;
 useEffect(()=>{onDirtyChange(dirty||instructionsDirty);},[dirty,instructionsDirty,onDirtyChange]);
 const transact=async(action)=>{
  if(gate.current)return;gate.current=true;setBusy(true);const ticket=life.current,epoch=controller.epoch;
  const valid=()=>ticket===life.current&&epoch===controller.epoch;
  try{await action(valid);}catch(error){if(valid())setNote(error.message+' Your edits are kept. Refresh before trying another change.');}
  finally{gate.current=false;if(valid())setBusy(false);}
 };
 const accept=value=>{setLibrary(value);if(!draft.current.dirty&&!editing)setForm(previous=>value.prompts.find(row=>row.id===previous.id)??empty());};
 const refresh=()=>transact(async valid=>{const value=await controller.rpc('prompts.list');if(!valid())return;accept(value);setNote('Library refreshed. Unsaved edits are kept.');});
 useEffect(()=>{life.current++;void transact(async valid=>{const value=await controller.rpc('prompts.list');if(!valid())return;accept(value);setInstructions(value.improvement);setText(value.improvement?.content??'');setNote('');});return()=>{life.current++;};},[controller]);
 const guard=(action,message='Discard your unsaved prompt changes?')=>{if(draft.current.dirty)setConfirmation({message,action});else action();};
 const choose=row=>guard(()=>{setForm(row??empty());setEditing(!row);setDirty(false);setNote('');});
 const save=()=>transact(async valid=>{
  const value=await controller.rpc('prompts.save',{id:form.id||undefined,name:form.name.trim().replace(/^\//,''),content:form.content,expectedRevision:form.revision});if(!valid())return;
  accept(value);const saved=value.prompts.find(row=>row.id===form.id||row.name===form.name.trim().replace(/^\//,''));setForm(saved);setEditing(false);setDirty(false);setNote('Prompt saved. Type /'+saved.name+' in chat to insert it.');
 });
 const remove=()=>setConfirmation({message:'Delete /'+form.name+' from the shared library? This affects all Augmentor interfaces.',confirmLabel:'Delete prompt',action:()=>void transact(async valid=>{const value=await controller.rpc('prompts.delete',{id:form.id,name:form.name,expectedRevision:form.revision});if(valid()){accept(value);setForm(empty());setEditing(false);setDirty(false);setNote('Prompt deleted.');}})});
 const saveInstructions=()=>transact(async valid=>{const value=await controller.rpc('prompts.improvementSave',{content:text,expectedRevision:instructions.revision});if(valid()){accept(value);setInstructions(value.improvement);setInstructionsDirty(false);setNote('Improvement instructions saved.');}});
 const reloadInstructions=()=>{
  const action=()=>void transact(async valid=>{const value=await controller.rpc('prompts.list');if(valid()){accept(value);setInstructions(value.improvement);setText(value.improvement.content);setInstructionsDirty(false);setNote('Latest instructions loaded.');}});
  if(instructionsDirty)setConfirmation({message:'Replace unsaved instructions with the latest saved version?',action});else action();
 };
 const rows=(library?.prompts??[]).filter(row=>(row.name+' '+row.content).toLocaleLowerCase().includes(query.trim().replace(/^\//,'').toLocaleLowerCase()));
 const modify=(field,value)=>{setForm(previous=>({...previous,[field]:value}));setDirty(true);};
 return <section className="augmentor-prompt-library" aria-label="Shared prompt library">
  <div className="prompt-tabs" aria-label="Prompt library sections"><Button aria-pressed={tab==='saved'} onClick={()=>setTab('saved')}>Saved prompts</Button><Button aria-pressed={tab==='improve'} onClick={()=>setTab('improve')}>Improve prompt</Button></div>
  <div hidden={tab!=='saved'}>
   <p className="prompt-help">Choose a reusable prompt to preview it, or type / in chat to insert it. Nothing is sent automatically. Augmentor interfaces connected to this library share its prompts; other profiles may keep separate copies.</p>
   <label>Search saved prompts<input type="search" placeholder="Find a prompt…" value={query} onChange={e=>setQuery(e.target.value)}/></label>
   <div className="prompt-actions"><Button disabled={busy||!writable} onClick={()=>choose(null)}>New prompt</Button><Button disabled={busy} onClick={()=>void refresh()}>Refresh library</Button></div>
   <div className="prompt-results" aria-label="Saved prompts">{rows.map(row=><Button key={row.id} disabled={busy} aria-label={'/'+row.name} aria-pressed={form.id===row.id} onClick={()=>choose(row)}><span>/{row.name}<small>{row.content.replace(/\s+/g,' ').slice(0,100)}</small></span></Button>)}</div>
   {library&&!rows.length&&<p>{library.prompts.length?'No prompts match your search.':'Your library is empty. Choose New prompt to get started.'}</p>}
   {!editing&&form.id&&<><h3>/{form.name}</h3><div className="prompt-preview" role="region" aria-label="Prompt preview">{form.content}</div><div className="prompt-actions"><Button disabled={busy||!writable||!onUse} onClick={()=>onUse(form.content)}>Use in draft</Button><Button disabled={busy||!writable} onClick={()=>setEditing(true)}>Edit prompt</Button><Button disabled={busy||!writable} onClick={remove}>Delete prompt</Button></div></>}
   {editing&&<><h3>{form.id?'Edit prompt':'New prompt'}</h3><label>Shortcut name<input aria-label="Prompt shortcut name" placeholder="For example: summarise" maxLength={128} disabled={busy||!writable} value={form.name} onChange={e=>modify('name',e.target.value)}/></label><label>Prompt text<textarea ref={body} aria-label="Saved prompt text" rows={7} maxLength={32000} disabled={busy||!writable} value={form.content} onChange={e=>modify('content',e.target.value)}/></label><div className="prompt-actions"><Button disabled={busy||!writable} onClick={()=>{const start=body.current.selectionStart,end=body.current.selectionEnd;modify('content',form.content.slice(0,start)+'[clipboard]'+form.content.slice(end));body.current.focus();}}>Insert clipboard placeholder</Button><Button variant="primary" disabled={busy||!library||!writable||!form.name.trim()||!form.content.trim()||!dirty} onClick={()=>void save()}>Save prompt</Button><Button disabled={busy} onClick={()=>guard(()=>{setForm(library?.prompts.find(row=>row.id===form.id)??empty());setEditing(false);setDirty(false);})}>Cancel edit</Button></div><p className="prompt-help">[clipboard] is replaced with copied text when you insert the /prompt in chat.</p></>}
  </div>
  <div hidden={tab!=='improve'}>
   <h3>Improve a draft before sending</h3><p className="prompt-help">Type a draft, then choose ✦ beside Send. The selected model rewrites it using these shared instructions. Review the result, edit it or choose Undo. Your message is sent only when you press Send.</p>
   <label>Prompt improvement instructions<textarea aria-label="Prompt improvement instructions" rows={11} maxLength={8000} disabled={busy||!instructions||!writable} value={text} onChange={e=>{setText(e.target.value);setInstructionsDirty(true);}}/></label>
   <div className="prompt-actions"><Button variant="primary" disabled={busy||!instructions||!writable||!instructionsDirty||!text.trim()} onClick={()=>void saveInstructions()}>Save instructions</Button><Button disabled={busy||!library} onClick={reloadInstructions}>Reload instructions</Button><Button disabled={busy||!instructions||!writable} onClick={()=>{setText(instructions.defaultContent);setInstructionsDirty(true);setNote('Default loaded. Save instructions to apply it.');}}>Use default instructions</Button></div>
   <p className="prompt-help">These instructions apply to Augmentor interfaces connected to this library. They are separate from your saved /prompts and conversation system prompt.</p>
  </div>
  {confirmation&&<div className="prompt-confirmation" ref={confirmRef} tabIndex={-1} role="alert"><p>{confirmation.message}</p><div className="prompt-actions"><Button disabled={busy} onClick={()=>{const action=confirmation.action;setConfirmation(null);action();}}>{confirmation.confirmLabel??'Discard changes'}</Button><Button disabled={busy} onClick={()=>setConfirmation(null)}>Keep editing</Button></div></div>}
  <p className="prompt-notice" role="status">{busy?'Working…':note}</p>
 </section>;
}
