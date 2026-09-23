// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {connect} from 'node:net';
import {spawn} from 'node:child_process';
import {homedir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {randomUUID} from 'node:crypto';
import {pythonExecutable,componentEnvironment} from '../../platform/src/index.js';
export const PROMPT_PROTOCOL='augmentor-prompts/1';
export function promptSocket(){const env=componentEnvironment();return join(env.AUGMENTOR_SHARED_STATE??join(env.XDG_STATE_HOME??join(homedir(),'.local/state'),'augmentor'),'prompts.sock');}
function request(method:string,params:Record<string,unknown>,id:string,signal?:AbortSignal):Promise<any>{return new Promise((resolve,reject)=>{
  if(signal?.aborted){reject(new Error('Cancelled'));return;}
  const socket=connect(method.startsWith('memory.dual.')?join(promptSocket(),'../dual-memory.sock'):promptSocket());let buffer=Buffer.alloc(0);
  const abort=()=>socket.destroy(new Error('Cancelled'));signal?.addEventListener('abort',abort,{once:true});
  socket.once('close',()=>signal?.removeEventListener('abort',abort));
  socket.setTimeout(20000,()=>socket.destroy(new Error('Prompt request timed out; reload before retrying a save.')));
  socket.on('connect',()=>socket.write(JSON.stringify({protocol:PROMPT_PROTOCOL,id,method,params})+'\n'));
  socket.on('error',reject);socket.on('data',chunk=>{
    buffer=Buffer.concat([buffer,chunk]);if(buffer.length>1024*1024){socket.destroy(new Error('Prompt response too large'));return;}
    const end=buffer.indexOf(10);if(end<0)return;
    try{const result=JSON.parse(buffer.subarray(0,end).toString());if(result.id!==id)throw new Error('Prompt response ID mismatch');if(result.error)throw new Error(result.error.message);resolve(result.result);}catch(error){reject(error);}finally{socket.end();}
  });socket.on('end',()=>reject(new Error('Prompt service disconnected; reload before retrying a save.')));
});}
export async function promptCall(method:string,params:Record<string,unknown>={},id:string=randomUUID(),signal?:AbortSignal):Promise<any>{
  try{return await request(method,params,id,signal);}catch(error:any){
    // Only connection failures before a request was sent can be retried.
    if(!['ENOENT','ECONNREFUSED'].includes(error.code))throw error;
    const child=spawn(pythonExecutable(),[fileURLToPath(new URL(method.startsWith('memory.dual.')?'../../../services/memory/service.py':'../../../services/prompt-library/service.py',import.meta.url))],{stdio:'ignore',detached:true,env:componentEnvironment()});child.on('error',()=>{});child.unref();
    for(let n=0;n<100;n++){
      signal?.throwIfAborted();
      await new Promise(r=>setTimeout(r,50));
      try{return await request(method,params,id,signal);}catch(next:any){if(!['ENOENT','ECONNREFUSED'].includes(next.code))throw next;}
    }
    throw new Error('Shared prompt service could not start.');
  }
}
