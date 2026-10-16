// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useRef,useState,useEffect,useMemo,useSyncExternalStore} from 'react';
import {Button} from '@deepseek-ai/dsh-client-ui-primitives';
import './plugins.css';
import {DshPluginControls} from './dsh-plugin-controls.mjs';
const groups=[
 ['Writing',[
  ['prompts','Prompt library','Save reusable prompts and insert them into a draft.'],
  ['improve','Improve prompt','Rewrite a draft before sending it. Edit the shared improvement instructions.']]],
 ['Research & knowledge',[
  ['search','Web search','Choose search engines and control how web pages are fetched.'],
  ['wiki','Wiki tools & skills','Connect your knowledge vault and manage its tools.']]],
 ['Workspace & models',[
  ['folders','Workspace folders','Organize projects and conversations with Metafolders.'],
  ['models','Model picker','Choose visible models, pin favourites and arrange their order.'],
  ['reasoning','Adaptive reasoning','Choose thinking preferences and inspect the effective reasoning mode.']]],
 ['Context & memory',[
  ['context','Context & insights','Inspect context usage and choose dashboard, sidebar and Fleet defaults.'],
  ['memory','Automatic memory','Check capture, recall and processing for relationship and project memory.']]],
 ['Connections',[
  ['mcp','Connected tools','Manage MCP connections to applications and external tools.'],
  ['voice','Voice input','Choose a microphone and insert speech as editable text.']]],
];
const entries=groups.flatMap(([,rows])=>rows);
/** A directory first, one settings panel at a time. Visited panels stay mounted
 * within Plugins so returning to the directory does not discard unsaved edits. */
export function PluginSettings({controller,folders,panels,onPrompts,onModels,canEditPrompts}){
 const controls=useMemo(()=>new DshPluginControls(controller,folders),[controller,folders]);useEffect(()=>()=>controls.close(),[controls]);
 const status=useSyncExternalStore(controls.subscribe,controls.getSnapshot);
 const detailPanels=panels(controls);
 const [query,setQuery]=useState(''),[selected,select]=useState(null),[visited,setVisited]=useState([]);
 const heading=useRef(null),lastCard=useRef(null),first=useRef(true);
 useEffect(()=>{if(first.current){first.current=false;return;}if(selected)heading.current?.focus();else{lastCard.current?.focus();void controls.refresh();}},[selected]);
 const open=(id,event)=>{
  lastCard.current=event.currentTarget;
  if(id==='prompts'||id==='improve'){onPrompts(id==='improve'?'improve':'saved');return;}
  if(id==='models'){onModels();return;}
  setVisited(ids=>ids.includes(id)?ids:[...ids,id]);select(id);
 };
 const active=entries.find(([id])=>id===selected),q=query.trim().toLocaleLowerCase();
 return <div className="augmentor-plugins" data-plugin-directory>
  <div hidden={!!selected}>
   <header><h2>Plugins</h2><p>Tools that extend your Augmentor workspace. Choose a feature to see its settings.</p></header>
   <label className="plugin-search">Find a plugin<input type="search" placeholder="Search features…" value={query} onChange={e=>setQuery(e.target.value)}/></label>
   {!canEditPrompts&&<p className="plugin-help">Open an operator connection to manage shared prompts. Read-only inspection does not allow library access.</p>}
   <p className="plugin-help">Switch plugins on or off here. Built-in features stay available; connected tools are managed per connection.</p><div className="plugin-overview-actions"><Button disabled={!canEditPrompts||Object.values(status.rows).some(row=>row.busy)} onClick={()=>void controls.refresh()}>Refresh plugin status</Button></div>
   {groups.map(([group,rows])=>{const matches=rows.filter(row=>[group,...row].join(' ').toLocaleLowerCase().includes(q));return matches.length?<section key={group} className="plugin-group" aria-label={group}><h3>{group}</h3><div className="plugin-grid">{matches.map(([id,title,description])=>{const row=status.rows[id],known=typeof row?.enabled==='boolean',label=row?(row.busy?'Checking…':row.error?'Unconfirmed':row.note==='Saved; application pending'?'Pending':known?(id==='memory'?(row.enabled?'Capture on':'Capture off'):(row.enabled?'On':'Off')):'Unavailable'):id==='mcp'?'Per connection':id==='voice'?'On demand':'Built in';return <article className="plugin-card" key={id} data-plugin-card={id}>
     <div className="plugin-card-status"><span className="plugin-state" data-enabled={known?String(row.enabled):undefined} role="status">{label}</span>{row&&<button type="button" className="plugin-switch" role="switch" aria-label={title} aria-checked={known&&row.enabled} aria-describedby={'plugin-note-'+id} disabled={!row.writable} onClick={()=>void controls.toggle(id)}><span aria-hidden="true"/></button>}</div>
     <button type="button" className="plugin-card-open" aria-label={'Open '+title+' settings'} disabled={(id==='prompts'||id==='improve')&&!canEditPrompts} onClick={e=>open(id,e)}><span className="plugin-card-title">{title}<span aria-hidden="true">→</span></span><span className="plugin-card-description">{description}</span><span className="plugin-card-action">{id==='prompts'?'Open library':id==='improve'?'Instructions & help':'Settings'}</span></button>
     {row&&<p id={'plugin-note-'+id} className="plugin-state-note">{row.error||row.note}</p>}
    </article>;})}}</div></section>:null;})}
   {!entries.some(row=>row.join(' ').toLocaleLowerCase().includes(q))&&!groups.some(([group])=>group.toLocaleLowerCase().includes(q))&&<p role="status">No plugins match “{query}”. Try a feature name such as prompts, search or context.</p>}
  </div>
  <div hidden={!selected}>
   <Button variant="ghost" onClick={()=>select(null)}>← All plugins</Button>
   <header className="plugin-detail-heading"><h2 ref={heading} tabIndex={-1}>{active?.[1]}</h2><p>{active?.[2]}</p></header>
  </div>
  {visited.map(id=><div key={id} hidden={selected!==id} data-plugin-panel={id}>{detailPanels[id]}</div>)}
 </div>;
}
