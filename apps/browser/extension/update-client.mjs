// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

// A short independent native connection also works when the selected harness
// cannot boot or the usual product handshake detects a version mismatch.
export function updateRequest(params,runtime=chrome.runtime){
 return new Promise((resolve,reject)=>{
  let port,finished=false
  const timer=setTimeout(()=>finish(Error('The update companion did not respond in time.')),30000)
  function finish(error,result){
   if(finished)return;finished=true;clearTimeout(timer)
   try{port?.disconnect()}catch{}
   error?reject(error):resolve(result)
  }
  try{
   port=runtime.connectNative('com.augmentor.agent')
   port.onDisconnect.addListener(()=>finish(Error(runtime.lastError?.message||'The update companion disconnected.')))
   port.onMessage.addListener(frame=>{
    if(frame.id==='update-handshake'){
     // Read-only discovery, cancellation and manual downloads are deliberately
     // available for mismatch recovery. Configuration still fails in the host.
     port.postMessage({id:'update-request',method:'augmentor/surface',params:{action:'updates',...params}})
    }else if(frame.id==='update-request')finish(frame.error?Error(frame.error.message||'Update operation failed.'):null,frame.result)
   })
   port.postMessage({id:'update-handshake',method:'augmentor/handshake',params:{protocol:'augmentor/1',version:runtime.getManifest().version}})
  }catch(error){finish(error)}
 })
}
