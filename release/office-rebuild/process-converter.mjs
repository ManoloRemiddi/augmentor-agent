// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Explicit diagnostic converter seat; never selected by the installed app.
import {fork} from 'node:child_process';
import {mkdtemp,rm} from 'node:fs/promises';
import {dirname,join} from 'node:path';
export const rendererProcesses=[];
const codes=new Set(['input-too-large','output-too-large','invalid-document','unsupported-format','invalid-output','timeout','unavailable','failed']);
const failure=(code,message)=>Object.assign(new Error(message),{code});
export async function createProcessConverter(options){
 const lifetime=new AbortController(),active=new Set();
 return {
  render(request,signal){
   const deadline=AbortSignal.timeout(options.timeoutMs),upstream=AbortSignal.any([lifetime.signal,deadline,...(signal?[signal]:[])]);
   upstream.throwIfAborted();
   const pending=(async()=>{
    // The provider already owns this input directory. Keep the original
    // entry's nested scratch inside it even when its process is interrupted.
    const scratch=await mkdtemp(join(dirname(request.inputPath),'renderer-'));
    try {upstream.throwIfAborted();return await new Promise((resolve,reject)=>{
    const child=fork(new URL('./process-renderer.mjs',import.meta.url),[],{execArgv:['--max-old-space-size=1536'],env:{...process.env,TMPDIR:scratch},stdio:['ignore','pipe','pipe','ipc']});
    const row={pid:child.pid,closed:false};rendererProcesses.push(row);
    let terminal,error,bytes=0,timer;
    const kill=()=>{if(timer)return;child.kill('SIGTERM');timer=setTimeout(()=>child.kill('SIGKILL'),2000);timer.unref();};
    const observe=chunk=>{bytes+=chunk.byteLength;if(bytes>8192&&!error){error=failure('failed','Diagnostic renderer exceeded its output bound.');kill();}};
    child.stdout.on('data',observe);child.stderr.on('data',observe);child.on('error',cause=>{error=cause;});
    child.on('message',message=>{
     if(terminal){error=failure('failed','Duplicate renderer terminal reply.');kill();return;}
     terminal=message;
    });
    upstream.addEventListener('abort',kill,{once:true});if(upstream.aborted)kill();
    child.once('close',(code,signal)=>{
     row.closed=true;row.exitCode=code;row.signal=signal;upstream.removeEventListener('abort',kill);if(timer)clearTimeout(timer);
     if(upstream.aborted){reject(deadline.aborted&&!lifetime.signal.aborted?failure('timeout','Diagnostic conversion timed out.'):upstream.reason);return;}
     if(error||code!==0){reject(error??failure('failed','Diagnostic renderer did not exit successfully.'));return;}
     if(terminal?.error){reject(failure(codes.has(terminal.error.code)?terminal.error.code:'failed','Office conversion failed.'));return;}
     if(!terminal||!Array.isArray(terminal.missingFonts)||terminal.missingFonts.length>20000||terminal.missingFonts.some(s=>typeof s!=='string')){reject(failure('failed','Invalid diagnostic renderer reply.'));return;}
     resolve({missingFonts:terminal.missingFonts});
    });
    child.send({options,request},cause=>{if(cause){error=cause;kill();}});
   });}finally{await rm(scratch,{recursive:true,force:true});}
   })();
   active.add(pending);pending.then(()=>active.delete(pending),()=>active.delete(pending));return pending;
  },
  async dispose(){lifetime.abort();await Promise.allSettled(active);},
 };
}
