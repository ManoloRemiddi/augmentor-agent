// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const KEY='augmentor-sidebar-follow'
export async function surfaceState(){const saved=(await chrome.storage.session.get(KEY))[KEY];return {ok:true,pinned:saved?.pinned!==false}}
export async function pinSurface(pinned){
 if(typeof pinned!=='boolean')throw Error('Invalid sidebar pin')
 const [tab]=await chrome.tabs.query({active:true,lastFocusedWindow:true})
 if(!tab)throw Error('The active browser tab is unavailable')
 await chrome.storage.session.set({[KEY]:{pinned,tabId:tab.id,windowId:tab.windowId}})
 return {ok:true,pinned}
}
export function watchSurface(){
 chrome.tabs.onActivated.addListener(async({tabId,windowId})=>{
  const saved=(await chrome.storage.session.get(KEY))[KEY]
  if(saved?.pinned===false&&saved.windowId===windowId&&saved.tabId!==tabId){
   // A global side panel follows tabs by default. Unpinning hides it when leaving
   // its tab, without replacing its document or changing the conversation.
   try{await chrome.runtime.sendMessage({type:'surface/hide',windowId})}catch{}
  }
 })
}
