// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {spawn} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import {pythonExecutable,componentEnvironment} from '../../../dist/platform/src/index.js'
const helper=fileURLToPath(new URL('../../../services/browser/executor.py',import.meta.url))
export function connectedBrowser(owner,params,signal){
 signal?.throwIfAborted()
 return new Promise((resolve,reject)=>{
  const child=spawn(pythonExecutable(),['-I','-X','utf8','-B',helper],{windowsHide:true,stdio:['pipe','pipe','inherit'],env:componentEnvironment()})
  child.stdout.setEncoding('utf8')
  let output='',settled=false
  const finish=(error,value)=>{if(settled)return;settled=true;clearTimeout(timer);signal?.removeEventListener('abort',abort);error?reject(error):resolve(value)}
  const abort=()=>{child.kill();if(params.action!=='stop')void connectedBrowser(owner,{action:'stop',...(params.executorId?{executorId:params.executorId}:{})}).catch(()=>{});finish(Error('Browser operation cancelled. Its outcome may be partial; inspect before continuing.'))}
  const timer=setTimeout(abort,25000);timer.unref?.();signal?.addEventListener('abort',abort,{once:true})
  child.on('error',error=>finish(error));child.stdin.on('error',()=>{})
  child.stdout.on('data',bytes=>{output+=bytes;if(Buffer.byteLength(output)>8*1024*1024){child.kill();finish(Error('Browser response exceeded its bound.'))}})
  child.on('close',code=>{if(settled)return;try{if(code!==0)throw Error('Browser executor disconnected; inspect the action outcome.');const value=JSON.parse(output);if(!value.ok)throw Error(value.error);finish(null,value.result)}catch(error){finish(error)}})
  child.stdin.end(JSON.stringify({owner,params,expiresAt:Date.now()+23000}))
 })
}
export function registerConnectedBrowserHost(send,{busy=()=>false}={}){
 const child=spawn(pythonExecutable(),['-I','-X','utf8','-B',helper,'serve'],{windowsHide:true,stdio:['pipe','pipe','inherit'],env:componentEnvironment()})
 child.stdout.setEncoding('utf8')
 let buffer='',closed=false;const pending=new Set()
 const answer=(id,error,result)=>{if(!closed&&!child.stdin.destroyed)child.stdin.write(JSON.stringify({id,error,result})+'\n')}
 child.stdout.on('data',bytes=>{
  buffer+=bytes
  if(buffer.length>2*8*1024*1024){close();return}
  let at
  while((at=buffer.indexOf('\n'))>=0){
   const raw=buffer.slice(0,at);buffer=buffer.slice(at+1)
   try{
    const message=JSON.parse(raw);if(message.type!=='request')continue
    const id='connected-browser-'+message.id
    if(busy()||Date.now()>message.expiresAt){answer(message.id,'Browser is not ready, the request expired, or maintenance is active; no request was sent.');continue}
    pending.add(id);send({id,method:'browser/execute',params:{...message.params,owner:message.owner,expiresAt:message.expiresAt}})
   }catch{close();return}
  }
 })
 child.on('error',()=>close());child.on('close',()=>close());child.stdin.on('error',()=>close())
 function receive(frame){
  if(typeof frame.id!=='string'||!frame.id.startsWith('connected-browser-'))return false
  if(pending.delete(frame.id))answer(frame.id.slice('connected-browser-'.length),frame.error?(frame.error.message??String(frame.error)):undefined,frame.result)
  return true // Late/duplicate replies never leak into a harness child.
 }
 function close(){if(closed)return;closed=true;pending.clear();child.stdin.end();const timer=setTimeout(()=>child.kill(),3000);timer.unref?.();child.once('close',()=>clearTimeout(timer))}
 return {receive,close,get active(){return pending.size}}
}
