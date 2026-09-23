// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {presentSettingsForm} from './settings-form.mjs'
export async function supportDialog(doc,send,container){
 if(doc.querySelector('.support-dialog'))return
 const dialog=doc.createElement('dialog');dialog.className='shared-prompt-editor memory-dialog support-dialog'
 const title=doc.createElement('h3');title.textContent='Support report'
 const note=doc.createElement('p');note.textContent='Review before sharing. This report contains versions and component status.'
 const preview=doc.createElement('textarea');preview.readOnly=true;preview.rows=14;preview.setAttribute('aria-label','Support report preview')
 const actions=doc.createElement('div'),close=doc.createElement('button'),save=doc.createElement('button')
 close.textContent='Close';close.onclick=()=>dialog.close();save.textContent='Save report';save.disabled=true
 actions.append(close,save);dialog.append(title,note,preview,actions);doc.body.append(dialog);dialog.addEventListener('close',()=>dialog.remove());presentSettingsForm(dialog,container)
 try{
  const response=await send('diagnostics');if(!response.ok)throw Error('The companion could not prepare a support report.')
  const report={...response.result,browser:{extensionVersion:chrome.runtime.getManifest().version,chromiumMajor:/Chrom(?:e|ium)\/(\d+)/.exec(navigator.userAgent)?.[1]??'unknown'}}
  preview.value=JSON.stringify(report,null,2)+'\n';save.disabled=false
  save.onclick=()=>{const url=URL.createObjectURL(new Blob([preview.value],{type:'application/json'})),link=doc.createElement('a');link.href=url;link.download='augmentor-support.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
 }catch(error){note.textContent=error.message}
}
