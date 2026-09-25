// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

let desktopAppearance=null
export function applyDesktopAppearance(result){
  if(!result?.tokens)return
  desktopAppearance=result
  document.documentElement.dataset.theme=result.theme
  document.documentElement.dataset.animation=String(result.animation)
  for(const [key,value] of Object.entries(result.tokens))document.documentElement.style.setProperty(key,value)
}
export async function refreshDesktopAppearance(){
  const reply=await chrome.runtime.sendMessage({type:'surface/appearance'})
  if(reply?.ok){applyDesktopAppearance(reply.result);return reply.result}
}
const T = globalThis.__dshAugTheme
export const appearanceFields = [
  ['neutHue','augmentor-neut-hue','Surface colour',0,360],
  ['neutBright','augmentor-neut-bright','Surface brightness',-15,15],
  ['accentHue','augmentor-accent-hue','Accent colour',0,360],
  ['accentBright','augmentor-accent-bright','Accent brightness',-15,15],
]
export const formattingFields=[['heading','Headings'],['link','Links'],['emphasis','Bold text'],['keyword','Code keywords'],['string','Code strings'],['number','Code numbers'],['name','Code functions'],['comment','Code comments'],['operator','Code operators']]
export function formattingDefaults(theme='dark'){
  const code=theme==='light'?['#6639ba','#236b35','#9a4600','#005c85','#596579','#a82c46']:['#c4a7ff','#a6da95','#f5a97f','#8bd5ef','#a5adcb','#ed8796']
  return Object.fromEntries(formattingFields.map(([key],i)=>[key,i===2?(theme==='light'?'#152b2c':'#edf3f3'):i<2?(theme==='light'?'#4176e6':'#5686fe'):code[i-3]]))
}
export function readAppearance() {
  const values = {theme:localStorage.getItem('augmentor-theme') === 'light' ? 'light' : 'dark'}
  for(const [key,storage,,min,max] of appearanceFields){
    const raw=localStorage.getItem(storage),value=raw===null?T.DEFAULTS[key]:Number(raw)
    values[key]=Number.isFinite(value)?Math.max(min,Math.min(max,value)):T.DEFAULTS[key]
  }
  try {values.formatColours=JSON.parse(localStorage.getItem('augmentor-format-colours')||'{}')} catch {values.formatColours={}}
  if(!values.formatColours||typeof values.formatColours!=='object')values.formatColours={}
  return desktopAppearance?.values?{...values,...desktopAppearance.values}:values
}
export function applyAppearance() {
  const value=readAppearance(),root=document.documentElement
  root.dataset.theme=value.theme
  T.applyPanelTheme(root,value.theme,value.neutHue,value.neutBright,value.accentHue,value.accentBright)
  for(const [key] of formattingFields){
    const colour=value.formatColours[key],property=(['heading','link','emphasis'].includes(key)?'--format-':'--syntax-')+key
    if(/^#[0-9a-f]{6}$/i.test(colour||''))root.style.setProperty(property,colour)
    else root.style.removeProperty(property)
  }
  if(desktopAppearance)applyDesktopAppearance(desktopAppearance)
  return value
}
export async function saveAppearance(value) {
  const reply=await chrome.runtime.sendMessage({type:'surface/appearance',settings:value})
  if(!reply?.ok)throw Error(reply?.error||'Could not save shared appearance')
  desktopAppearance=reply.result
  const stored={'augmentor-theme':value.theme,'augmentor-format-colours':JSON.stringify(value.formatColours||{})}
  for(const [key,storage] of appearanceFields)stored[storage]=value[key]
  for(const [key,v] of Object.entries(stored))localStorage.setItem(key,String(v))
  applyAppearance()
  // The service worker uses these values for browser-control overlays.
  return chrome.storage.local.set(stored)
}
export function watchAppearance(onChange=()=>{}) {
  const refresh=()=>onChange(applyAppearance())
  const listener=event=>{if(event.key===null||event.key.startsWith('augmentor-'))void refreshDesktopAppearance().then(refresh).catch(()=>refresh())}
  window.addEventListener('storage',listener);refresh()
  window.addEventListener('pagehide',()=>window.removeEventListener('storage',listener),{once:true})
}
export function resetAppearance(){return {theme:'dark',...T.DEFAULTS,formatColours:{}}}
