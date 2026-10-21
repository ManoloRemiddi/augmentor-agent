// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {StringDecoder} from 'node:string_decoder';
import {pythonExecutable,componentEnvironment} from '../../platform/src/index.js';
import type {JobControl,JobOutcome,JobRecord} from './jobs.js';
const VERSION='augmentor-shell-job/1';
const helper=fileURLToPath(new URL('../../../services/platform_adapters/shell_job.py',import.meta.url));
const uncertain=():JobOutcome=>({state:'unknown',reason:'Owned Windows command receipt or producer exit was not confirmed. Effects may remain; do not replay automatically.'});

/** Command bytes are output, never control. Only the private supervisor frames receipts. */
export class WindowsShellFrames {
 private buffer='';private ready=false;private receipt:JobOutcome|undefined;
 private decoders={stdout:new StringDecoder('utf8'),stderr:new StringDecoder('utf8')};
 constructor(private append:JobControl['append']){}
 get settled(){return Boolean(this.receipt);}
 push(data:Buffer){
  if(data.some(byte=>byte>127))throw Error('Non-ASCII producer frame.');
  this.buffer+=data.toString('ascii');
  let end:number;while((end=this.buffer.indexOf('\n'))>=0){
   if(end>65535)throw Error('Oversized producer frame.');
   const line=this.buffer.slice(0,end);this.buffer=this.buffer.slice(end+1);
   const event=JSON.parse(line);
   if(!event||typeof event!=='object'||event.version!==VERSION||this.receipt)throw Error('Invalid producer receipt.');
   const exact=(keys:string[])=>{if(Object.keys(event).some(key=>!keys.includes(key)))throw Error('Invalid producer fields.');};
   if(event.type==='ready'){
    exact(['version','type','range','boundary']);
    if(this.ready||event.range!=='windows-job'||event.boundary!=='assigned-before-workload')throw Error('Invalid owned range.');this.ready=true;
   }else if(event.type==='output'){
    exact(['version','type','channel','data']);
    if(!this.ready||!['stdout','stderr'].includes(event.channel)||typeof event.data!=='string'||event.data.length>5464||!/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(event.data))throw Error('Invalid producer output.');
    const bytes=Buffer.from(event.data,'base64');
    if(bytes.length>4096||bytes.toString('base64')!==event.data)throw Error('Invalid producer bytes.');
    const channel=event.channel as keyof typeof this.decoders;this.append(this.decoders[channel].write(bytes),channel);
   }else if(event.type==='settled'){
    exact(['version','type','state','drained','exitCode']);
    if(!['completed','failed','cancelled','unknown'].includes(event.state)||typeof event.drained!=='boolean'||event.exitCode!==undefined&&(!Number.isSafeInteger(event.exitCode)||event.exitCode<0||event.exitCode>0xffffffff)||['completed','cancelled'].includes(event.state)&&!event.drained||event.state==='completed'&&(!this.ready||event.exitCode!==0)||event.exitCode!==undefined&&!this.ready||event.state==='failed'&&event.drained&&event.exitCode===0)throw Error('Invalid settlement evidence.');
    this.receipt={state:event.state,exitCode:event.exitCode,reason:event.state==='unknown'?'Owned Windows command range settlement was not confirmed. Effects may remain.':event.drained?'Owned Windows command range drained. Verify task results separately; effects are not rolled back.':'Windows command startup failed before confirmed range execution.'};
   }else throw Error('Invalid producer event.');
  }
  if(this.buffer.length>65535)throw Error('Oversized incomplete producer frame.');
 }
 finish(code:number|null):JobOutcome{
  for(const channel of ['stdout','stderr'] as const)this.append(this.decoders[channel].end(),channel);
  return !this.buffer&&code===0&&this.receipt?this.receipt:uncertain();
 }
}

/** A private pipe is the producer's liveness lease, never a reusable PID. */
export function windowsShellJob(cwd:string,row:JobRecord,control:JobControl):Promise<JobOutcome>{
 control.signal.throwIfAborted();
 const child=spawn(pythonExecutable(),['-I','-Xutf8','-B',helper],{cwd,env:componentEnvironment(),windowsHide:true,stdio:['pipe','pipe','pipe']});
 return new Promise(resolve=>{
  let problem=false,timer:ReturnType<typeof setTimeout>|undefined,closed=false,stopping=false;
  const frames=new WindowsShellFrames(control.append);
  const stop=()=>{if(closed||stopping)return;stopping=true;child.stdin.end(JSON.stringify({version:VERSION,type:'cancel'})+'\n');timer=setTimeout(()=>{child.kill();},4000);};
  const fault=()=>{problem=true;stop();};
  const finish=(result:JobOutcome)=>{if(closed)return;closed=true;if(timer)clearTimeout(timer);control.signal.removeEventListener('abort',stop);resolve(result);};
  child.stdin.on('error',()=>{if(!closed&&!frames.settled)fault();});
  child.stdout.on('data',data=>{if(!problem)try{frames.push(data);}catch{fault();}});
  // Helper stderr is diagnostics, never a command result or a control receipt.
  child.stderr.on('data',()=>{});
  child.once('error',()=>{if(child.pid===undefined)finish({state:'failed',reason:'The owned Windows command producer could not be started.'});else fault();});
  child.once('close',code=>{let result=uncertain();try{result=frames.finish(code);}catch{problem=true;}finish(problem?uncertain():result);});
  child.stdin.write(JSON.stringify({version:VERSION,command:row.spec.task})+'\n');
  control.signal.addEventListener('abort',stop,{once:true});if(control.signal.aborted)stop();
 });
}
