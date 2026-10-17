// Copyright (c) 2026 Manolo Remiddi · SPDX-License-Identifier: MIT
// Model Picker Augmented 1.1.2 card presentation adapted to the Pi catalog.
// Original MIT notice: licenses/dsh-model-picker-augmented.txt.
import React,{useState,useSyncExternalStore} from 'react';
import {IconChevronUpOutlineRegular,IconChevronDownOutlineRegular} from '@deepseek-ai/dsh-client-ui-primitives';
import './model-picker.css';

export function ModelPickerSettings({controller}){
 const state=useSyncExternalStore(controller.subscribe,controller.getSnapshot);
 const [query,setQuery]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(null);
 const catalog=state.catalog,pins=catalog.pinned??[],hidden=new Set(catalog.hidden??[]),pinSet=new Set(pins);
 const rows=catalog.groups.flatMap(group=>group.models.map(model=>({key:group.provider+'/'+model.model,provider:group.provider,providerName:group.name,model:model.model,name:model.name||model.model})));
 const byKey=new Map(rows.map(row=>[row.key,row]));
 const match=row=>[row.name,row.model,row.providerName].some(text=>text.toLowerCase().includes(query.trim().toLowerCase()));
 const pinned=pins.flatMap(key=>byKey.has(key)&&match(byKey.get(key))?[byKey.get(key)]:[]);
 const groups=catalog.groups.map(group=>({...group,rows:rows.filter(row=>row.provider===group.provider&&!pinSet.has(row.key)&&match(row))})).filter(group=>group.rows.length);
 const disabled=busy||state.phase!=='ready'||state.readOnly;
 const change=async(row,action)=>{if(disabled)return;setBusy(true);setError(null);try{await controller.curateModel(row,action);}catch(e){setError(e.message+' Nothing was retried. Refresh the picker settings before editing again.');}finally{setBusy(false);}};
 const refresh=async()=>{if(disabled)return;setBusy(true);setError(null);try{const epoch=controller.epoch,value=await controller.rpc('models.list');if(epoch===controller.epoch&&!controller.state.readOnly){controller.catalogRead++;controller.update({catalog:value});}}catch{setError('The catalog could not be refreshed.');}finally{setBusy(false);}};
 const card=(row,isPinned)=>{const index=pins.indexOf(row.key),isHidden=hidden.has(row.key);return <li className="msp-card" key={row.key}>
  <div className="msp-cardHead"><span className="msp-cardName" title={row.name}>{row.name}</span><span className="msp-cardTag">{row.providerName}</span>
   <button className={'msp-chip'+(isHidden?'':' msp-chipOn')} type="button" aria-label={(isHidden?'Show ':'Hide ')+row.name+' ('+row.provider+')'} aria-pressed={!isHidden} disabled={disabled||!!error} onClick={()=>void change(row,isHidden?'show':'hide')}>{isHidden?'Hidden':'Visible'}</button>
   <button className={'msp-chip'+(isPinned?' msp-chipOn':'')} type="button" aria-label={(isPinned?'Unpin ':'Pin ')+row.name+' ('+row.provider+')'} disabled={disabled||!!error} onClick={()=>void change(row,isPinned?'unpin':'pin')}>{isPinned?'Unpin':'Pin to top'}</button>
   {isPinned&&<><button className="msp-iconBtn" type="button" aria-label={'Move up '+row.name+' ('+row.provider+')'} disabled={disabled||!!error||index<=0} onClick={()=>void change(row,'up')}><IconChevronUpOutlineRegular size={14}/></button><button className="msp-iconBtn" type="button" aria-label={'Move down '+row.name+' ('+row.provider+')'} disabled={disabled||!!error||index>=pins.length-1} onClick={()=>void change(row,'down')}><IconChevronDownOutlineRegular size={14}/></button></>}
  </div></li>;};
 return <section className="msp-section" aria-label="Model Picker Augmented"><h2 className="msp-title">Model Picker Augmented</h2><p className="msp-intro">Choose which models appear in the composer and pin favourites to the top. Changes are saved in this Harness profile.</p>
  <div className="msp-bar"><input className="msp-pageSearch" type="search" aria-label="Search picker settings" placeholder="Search models…" value={query} onChange={e=>setQuery(e.target.value)}/><button className="msp-reset" disabled={disabled} onClick={()=>void refresh()}>Refresh picker settings</button></div>
  {error&&<p className="msp-note msp-noteError" role="alert">{error}</p>}
  {!!pinned.length&&<><p className="msp-note">Pinned</p><ul className="msp-cards">{pinned.map(row=>card(row,true))}</ul></>}
  {groups.map(group=><div key={group.provider}><p className="msp-note">{group.name}</p><ul className="msp-cards">{group.rows.map(row=>card(row,false))}</ul></div>)}
  {!pinned.length&&!groups.length&&<p className="msp-note">No models match your search.</p>}
 </section>;
}
