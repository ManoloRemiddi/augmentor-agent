// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {Type} from 'typebox';
import type {ExtensionAPI} from '@earendil-works/pi-coding-agent';
import {pythonExecutable,componentEnvironment} from '../../platform/src/index.js';
const helper=fileURLToPath(new URL('../../../services/desktop/client.py',import.meta.url));
export const definitions=[
 {name:'linux_desktop_connect',method:'connect',description:'Request desktop sharing through the OS consent dialog. The backend supports one monitor on KDE Plasma Wayland or macOS; macOS requires the installed native helper and Screen Recording and Accessibility permissions. An independent Stop desktop control button stays visible. Only this chat owns the connection. Screenshots are sent to the selected model when you observe. Never retry declined consent.',parameters:Type.Object({})},
 {name:'linux_desktop_snapshot',method:'capture',description:'Capture the consented desktop as an image, with fresh active-window identity and a single-use target token. Observe before every action and after it to verify the result. Activate the intended application first; do not guess coordinates from an older image.',parameters:Type.Object({})},
 {name:'linux_desktop_action',method:'action',description:'Send one click, key chord, or short text (ASCII on Linux, Unicode on macOS) to the freshly observed active application. Coordinates use the returned screenshot pixels. A token is consumed once. Stale/covered targets are refused. Text can be partial after Stop or focus changes; observe before continuing. This reports dispatch, not verified success.',parameters:Type.Object({token:Type.String(),kind:Type.Union([Type.Literal('click'),Type.Literal('key'),Type.Literal('type')]),x:Type.Optional(Type.Number()),y:Type.Optional(Type.Number()),keys:Type.Optional(Type.Array(Type.String(),{maxItems:3})),text:Type.Optional(Type.String({maxLength:256}))})},
 {name:'linux_desktop_stop',method:'stop',description:'Immediately close this chat’s desktop sharing session and release held keys. Stop is always available.',parameters:Type.Object({})},
] as const;
export function control(method:string,owner:string,params:unknown={},signal?:AbortSignal):Promise<any>{
 signal?.throwIfAborted();
 return new Promise((resolve,reject)=>{
  const child=spawn(pythonExecutable(),[helper],{stdio:['pipe','pipe','ignore'],env:componentEnvironment()});let out='',settled=false,cancelling=false;
  const finish=(error:Error|null,value?:unknown)=>{if(settled)return;settled=true;clearTimeout(timer);signal?.removeEventListener('abort',abort);error?reject(error):resolve(value)};
  const abort=async()=>{if(cancelling||settled)return;cancelling=true;if(method!=='stop')await control('stop',owner).catch(()=>{});child.kill();finish(new Error('Desktop control stopped. Inspect the application before continuing.'))};
  const timer=setTimeout(abort,method==='stop'?8000:105000);signal?.addEventListener('abort',abort,{once:true});
  if(signal?.aborted){abort();return}
  child.on('error',error=>finish(error));child.stdin.on('error',()=>{});
  child.stdout.on('data',value=>{out+=value;if(Buffer.byteLength(out)>2*1024*1024){abort()}});
  child.on('close',code=>{if(cancelling)return;if(code!==0){finish(new Error('Desktop executor disconnected. The action outcome may be unknown.'));return}try{const value=JSON.parse(out);if(!value.ok)throw Error(value.error);finish(null,value.result)}catch(error){finish(error as Error)}});
  child.stdin.end(JSON.stringify({method,owner,params}));
 });
}
export function desktopPackage(owner:string){return (pi:ExtensionAPI)=>{
 for(const d of definitions)pi.registerTool({name:d.name,label:d.name,description:d.description,parameters:d.parameters,
  execute:async(_id,args,signal,_update,ctx)=>{
   if(d.method==='capture'&&!ctx.model?.input.includes('image'))throw Error('Select a model configured for image input before capturing the desktop.');
   const value=await control(d.method,owner,args,signal);const {image,...metadata}=value;
   return {content:[{type:'text' as const,text:JSON.stringify(metadata)},...(image?[{type:'image' as const,data:image.data,mimeType:image.mimeType}]:[])],details:{}};
  }});
};}
