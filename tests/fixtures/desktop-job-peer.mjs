// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored synthetic peer for the public desktop wire protocol.
// The Host still invokes its actual desktop Python client and public Pi SDK.
import assert from 'node:assert/strict';
import net from 'node:net';
import {once} from 'node:events';
import {chmod,readdir,readFile} from 'node:fs/promises';
import {join} from 'node:path';
export const desktopPng='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJCkAAAAASUVORK5CYII=';
export async function desktopJobPeer(runtime,state,mode){
 const calls=[],sockets=new Set();let owner,token,sequence=0;
 const server=net.createServer(socket=>{sockets.add(socket);socket.once('close',()=>sockets.delete(socket));let raw='';socket.on('data',async bytes=>{raw+=bytes;if(!raw.includes('\n'))return;socket.removeAllListeners('data');
  try{
   const request=JSON.parse(raw);assert.equal(request.protocol,'augmentor-desktop/1');calls.push(request);
   const {method,params}=request;let result;
   if(method==='status')result={active:!!owner,sharing:!!owner,owner:owner??null,available:true};
   else if(method==='stop'){if(mode.failStop)throw Error('Synthetic Stop confirmation unavailable');if(owner===request.owner){owner=undefined;token=undefined;}result={stopped:true};}
   else if(method==='connect'){if(mode.denyConsent)throw Error('Synthetic OS consent declined');assert(!owner,'Only one consented owner');owner=request.owner;result={accepted:true};}
   else{
    assert.equal(request.owner,owner,'Exact consented OS owner');
    if(method==='capture'){token='synthetic-fresh-'+(++sequence);result={token,screen:'WORKER_ONLY_SCREEN_DETAIL',image:{data:desktopPng,mimeType:'image/png'}};}
    else if(method==='action'){
     assert.equal(params.token,token,'Fresh token required');token=undefined;
     const evidenceRoot=join(state,'desktop-runs'),ids=await readdir(evidenceRoot);let record;
     for(const id of ids){const candidate=JSON.parse(await readFile(join(evidenceRoot,id,'record.json'),'utf8'));if(candidate.owner===owner&&candidate.result.actionAttempted)record=candidate;}
     assert(record?.events.some(event=>event.tool==='desktop_action/intent'),'Durable intent precedes actual wire dispatch');
     const receipt=JSON.parse(await readFile(join(state,'jobs',record.result.jobId+'.json'),'utf8'));
     assert.equal(receipt.desktop.actionAttempted,true,'Job checkpoint also precedes input');
     if(mode.disconnectAction){socket.destroy();return;}
     result={accepted:true};
    }else throw Error('Unsupported synthetic desktop method');
   }
   socket.end(JSON.stringify({ok:true,result})+'\n');
  }catch(error){socket.end(JSON.stringify({ok:false,error:error.message})+'\n');}
 });});
 const path=join(runtime,'augmentor-desktop.sock');server.listen(path);await once(server,'listening');await chmod(path,0o600);
 return {calls,close:async()=>{for(const socket of sockets)socket.destroy();await new Promise(done=>server.close(done));}};
}
