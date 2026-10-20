// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn,spawnSync,type ChildProcessWithoutNullStreams} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {isAbsolute} from 'node:path';
const helper=fileURLToPath(new URL('./wiki-native.py',import.meta.url));
const env={PATH:'/usr/bin:/bin:/usr/sbin:/sbin',PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'};
function python(){const value=process.env.AUGMENTOR_PYTHON||'/usr/bin/python3';if(!isAbsolute(value))throw Error('Wiki requires an absolute Python runtime.');return value;}
function failure(value:any){return Object.assign(Error(value.message||'Wiki IO helper failed.'),{code:value.code||'EWIKI'});}
export function darwinWikiIdentity(pid:number){
 const result=spawnSync(python(),['-I','-B',helper,'identity',String(pid)],{env,encoding:'utf8',timeout:5000,maxBuffer:16384});
 if(result.error)throw Error('Wiki process identity helper could not run.');
 let data;try{data=JSON.parse(result.stdout);}catch{throw Error('Wiki process identity could not be verified.');}
 if(data.error)throw failure(data.error);if(result.status!==0||!data.result||!/^\d+$/.test(data.result.processStart)||!/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(data.result.bootId))throw Error('Wiki process identity is invalid.');
 return data.result as {processStart:string;bootId:string};
}
export class DarwinWikiFs {
 private child:ChildProcessWithoutNullStreams;
 private pending=new Map<number,{resolve:(v:any)=>void;reject:(e:Error)=>void;timer:NodeJS.Timeout}>();
 private buffer='';private next=0;private ended=false;private end:Promise<void>;
 constructor(private attempted:()=>void){
  this.child=spawn(python(),['-I','-B',helper],{env,stdio:['pipe','pipe','pipe']});
  this.end=new Promise(resolve=>this.child.once('close',()=>{this.fail(Error('Wiki IO helper closed before confirmation.'));resolve();}));
  this.child.on('error',()=>this.fail(Error('Wiki IO helper could not start.')));
  this.child.stdin.on('error',()=>this.fail(Error('Wiki IO request could not be confirmed.')));
  this.child.stderr.on('data',()=>{/* Private helper diagnostics never enter model output or public logs. */});
  this.child.stdout.setEncoding('utf8');this.child.stdout.on('data',(part:string)=>{
   this.buffer+=part;if(this.buffer.length>90*1024*1024){this.fail(Error('Wiki IO response exceeds its bound.'));this.child.kill('SIGTERM');return;}
   let at;while((at=this.buffer.indexOf('\n'))>=0){const line=this.buffer.slice(0,at);this.buffer=this.buffer.slice(at+1);let frame;try{frame=JSON.parse(line);}catch{this.fail(Error('Wiki IO response is invalid.'));this.child.kill('SIGTERM');return;}
    if(frame.attempt===true){this.attempted();continue;}const request=this.pending.get(frame.id);if(!request){this.fail(Error('Wiki IO response identity is invalid.'));this.child.kill('SIGTERM');return;}this.pending.delete(frame.id);clearTimeout(request.timer);frame.error?request.reject(failure(frame.error)):request.resolve(frame.result);
   }
  });
 }
 private fail(error:Error){this.ended=true;for(const p of this.pending.values()){clearTimeout(p.timer);p.reject(error);}this.pending.clear();}
 call(op:string,value:Record<string,unknown>={}){
  if(this.ended)return Promise.reject(Error('Wiki IO helper is closed; nothing was replayed.'));
  const id=++this.next;return new Promise<any>((resolve,reject)=>{const timer=setTimeout(()=>{this.fail(Error('Wiki IO timed out; its outcome is unconfirmed.'));this.child.kill('SIGTERM');},15000);this.pending.set(id,{resolve,reject,timer});this.child.stdin.write(JSON.stringify({id,op,...value})+'\n');});
 }
 async close(){this.child.stdin.end();const timer=setTimeout(()=>this.child.kill('SIGTERM'),2000);try{await this.end;}finally{clearTimeout(timer);}}
}
export function wikiStat(value:any){return {...value,isFile:()=>((value.mode&0o170000)===0o100000),isDirectory:()=>((value.mode&0o170000)===0o040000),isSymbolicLink:()=>((value.mode&0o170000)===0o120000)};}
