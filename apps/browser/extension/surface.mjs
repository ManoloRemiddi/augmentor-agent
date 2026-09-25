import {SURFACE} from './surface-design.mjs'
import {startLetterRoll} from './prompt-animation.mjs'
// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Window controls and the composer use the floating window's positions and glyphs.
export function attachSurface({send,openSettings,onError,approval,state}){
  const $=id=>document.getElementById(id),input=$('input'),improve=$('improve'),menu=$('more-menu'),more=$('more')
  for(const [key,glyph] of Object.entries(SURFACE.glyphs)){const id=key==='latest'?'top':key;if($(id))$(id).textContent=glyph}
  // The native plus glyph depends on OS font fallback; use a matching vector.
  for(const [id,path] of [['newchat','M8 3v10M3 8h10']]){
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg'),shape=document.createElementNS(ns,'path')
    for(const [key,value] of Object.entries({width:'16',height:'16',viewBox:'0 0 16 16',fill:'none',stroke:'currentColor','stroke-width':'1.2','aria-hidden':'true'}))svg.setAttribute(key,value)
    shape.setAttribute('d',path);svg.append(shape);$(id).replaceChildren(svg)
  }
  let improving=false,epoch=0,undo=null,roll=null
  const cancelImprovement=()=>{epoch++;improving=false;roll?.stop();roll=null}
  const announce=text=>{$('surface-status').textContent=text}
  const fail=error=>{announce(error.message);onError(error.message)}
  const closeMenu=()=>{menu.hidden=true;more.setAttribute('aria-expanded','false')}
  more.onclick=()=>{menu.hidden=!menu.hidden;more.setAttribute('aria-expanded',String(!menu.hidden));if(!menu.hidden)menu.querySelector('button').focus()}
  menu.querySelectorAll('[data-section]').forEach(button=>button.onclick=()=>{closeMenu();void openSettings(button.dataset.section||undefined)})
  $('approval-menu-item').onclick=()=>{closeMenu();approval()}
  document.addEventListener('pointerdown',e=>{if(!menu.contains(e.target)&&!more.contains(e.target))closeMenu()})
  menu.onkeydown=e=>{const items=[...menu.querySelectorAll('button')];let i=items.indexOf(document.activeElement);if(['ArrowDown','ArrowUp','Home','End'].includes(e.key)){e.preventDefault();i=e.key==='Home'?0:e.key==='End'?items.length-1:(i+(e.key==='ArrowDown'?1:-1)+items.length)%items.length;items[i].focus()}}
  const draftKey='augmentor-sidebar-draft'
  let sessionId=null,restored=false
  const remember=()=>chrome.storage.session.set({[draftKey]:{sessionId,text:input.value}}).catch(()=>{})
  input.addEventListener('input',remember)
  const hide=()=>{cancelImprovement();closeMenu();void remember().finally(()=>window.close())}
  $('hide').onclick=hide;$('hide-menu-item').onclick=hide
  const fit=()=>{
    // Reset before measuring so deleting text also shrinks the composer.
    // scrollHeight includes padding but excludes the two border pixels.
    input.style.height='29px'
    input.style.overflowY='hidden'
    const height=input.value ? Math.max(29,input.scrollHeight+2) : 29
    input.style.height=Math.min(125,height)+'px'
    input.style.overflowY=height>125?'auto':'hidden'
  }
  window.addEventListener('resize',fit)
  if(window.ResizeObserver){
    let width=0
    new window.ResizeObserver(([entry])=>{
      if(entry.contentRect.width!==width){width=entry.contentRect.width;fit()}
    }).observe($('composer-field'))
  }
  const controls=()=>{improve.disabled=!improving&&(!input.value.trim()||state().phase!=='ready'||state().running);improve.textContent=improving?'×':undo?'↶':'✦';improve.title=improving?'Cancel prompt improvement':undo?'Undo prompt improvement':'Improve prompt';improve.setAttribute('aria-label',improve.title)}
  input.addEventListener('input',()=>{cancelImprovement();undo=null;fit();controls()})
  new MutationObserver(fit).observe(input,{attributes:true,attributeFilter:['disabled']})
  improve.onclick=async()=>{
    if(improving){cancelImprovement();controls();return}
    if(undo!==null){input.value=undo;undo=null;void remember();fit();controls();return}
    const original=input.value,id=++epoch;improving=true;roll=startLetterRoll(input);controls();announce('Improving prompt…')
    const animation=roll
    try{
      const r=await send('prompt/improve',{text:original})
      if(id!==epoch||input.value!==original)return
      if(!r?.ok||r.result?.kind!=='rewrite'||typeof r.result.text!=='string'||!r.result.text.trim())throw Error(r?.error||'Could not improve the prompt')
      if(!await animation.settle(r.result.text)||id!==epoch||input.value!==original)return
      input.value=r.result.text;undo=original;void remember();fit();announce('Prompt improved. Undo is available.')
    }catch(error){if(id===epoch)fail(error)}finally{if(id===epoch){cancelImprovement();controls()}}
  }
  input.addEventListener('keydown',e=>{
    if(!improving)return
    if(e.key==='Enter'){e.preventDefault();e.stopPropagation()}
    else if(e.key==='Escape'){e.preventDefault();e.stopPropagation();cancelImprovement();controls()}
  },true)
  window.addEventListener('pagehide',cancelImprovement)

  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!menu.hidden){e.preventDefault();closeMenu();more.focus()}else if(e.ctrlKey&&e.key==='End'){$('log').scrollTo({top:$('log').scrollHeight,behavior:'smooth'})}else if(e.ctrlKey&&e.key==='Home'){$('log').scrollTo({top:0,behavior:'smooth'})}})
  fit();controls()
  return {get improving(){return improving},update(value){
    if(value.sessionId){if(sessionId&&value.sessionId!==sessionId){cancelImprovement();undo=null;void chrome.storage.session.remove(draftKey)}sessionId=value.sessionId;if(!restored){restored=true;void chrome.storage.session.get(draftKey).then(saved=>{const draft=saved[draftKey];if(draft?.sessionId===sessionId&&!input.value){input.value=draft.text;fit();controls()}})}}
    const current={...state(),...value};const dot=$('connection-dot');dot.dataset.phase=current.phase;dot.title=current.phase==='ready'?'Connected':current.error||'Connecting…';dot.setAttribute('aria-label',dot.title);controls()}}
}
