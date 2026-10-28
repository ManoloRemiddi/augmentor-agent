// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// One original entry conversion per diagnostic OS process. IPC carries metadata.
import assert from 'node:assert/strict';
assert(process.connected);
// This is an IPC-parent-loss diagnostic guard, not a production kernel guard.
let finished=false;
process.on('disconnect',()=>{if(!finished)process.exit(70);});
process.once('message',async({options,request})=>{
 let converter,reply;
 try {
  const entry=await import('/app/dist/runtime/vendor/office-entry/index.js');
  assert.equal((await entry.discoverRuntime()).backend,'wasm');
  converter=await entry.createConverter(options);reply=await converter.render(request);
 }catch(error){reply={error:{code:typeof error?.code==='string'?error.code:'failed'}};}
 finally{try{await converter?.dispose();}catch{reply={error:{code:'failed'}};}}
 if(process.connected)process.send(reply,error=>{if(error)process.exitCode=71;finished=true;if(process.connected)process.disconnect();});
});
