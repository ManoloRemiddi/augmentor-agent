// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn} from 'node:child_process';
import {Type} from 'typebox';
import type {ExtensionAPI} from '@earendil-works/pi-coding-agent';
import {pythonExecutable,componentEnvironment} from '../../platform/src/index.js';
export function runDesktop(backend:string, input:unknown, signal?:AbortSignal):Promise<unknown> {
  return new Promise((resolve,reject)=>{
    const child=spawn(pythonExecutable(),[backend],{stdio:['pipe','pipe','pipe'],signal,env:componentEnvironment()});
    let out='',settled=false;
    const finish=(error:Error|null,value?:unknown)=>{if(settled)return;settled=true;clearTimeout(timer);error?reject(error):resolve(value);};
    const timer=setTimeout(()=>{child.kill();finish(new Error('Desktop operation timed out'));},12000);
    child.stdout.on('data',data=>{out+=data;if(Buffer.byteLength(out)>256000){child.kill();finish(new Error('Desktop output exceeded limit'));}});
    child.stderr.resume();child.on('error',error=>finish(error));child.stdin.on('error',()=>{});
    child.on('close',code=>{if(code!==0)return finish(new Error('Desktop helper failed'));try{finish(null,JSON.parse(out));}catch{finish(new Error('Invalid desktop output'));}});
    child.stdin.end(JSON.stringify(input));
  });
}
export const linuxDefinitions=[
      {name:'linux_system_profile',description:'Read the actual operating system, desktop and dependency capabilities. The legacy tool name is retained for session compatibility. No app contents.',parameters:Type.Object({}),action:'profile'},
      {name:'linux_desktop_observe',description:'List accessible Linux applications, or inspect a bounded AT-SPI control tree for an appPid. Read-only; password fields are redacted.',parameters:Type.Object({appPid:Type.Optional(Type.Integer({minimum:1}))}),action:'observe'},
      {name:'linux_browser_open',description:'Open an HTTP(S) URL in a NEW visible Chromium tab in the existing user profile. Reports dispatch, not verified page loading. Never repeat an accepted launch just because verification is unavailable.',parameters:Type.Object({url:Type.String({maxLength:8192})}),action:'browser_open'},
    ];

export function linuxPackage(backend:string) {
  return (pi:ExtensionAPI)=>{
    for(const d of linuxDefinitions)pi.registerTool({name:d.name,label:d.name,description:d.description,parameters:d.parameters,
      async execute(_id,args,signal){const value=await runDesktop(backend,{action:d.action,...args},signal);return {content:[{type:'text',text:JSON.stringify(value)}],details:{}};}});
    pi.registerTool({name:'ask_user',label:'Ask user',description:'Ask the user for required missing information. Use for choices or clarification that cannot be inferred.',parameters:Type.Object({question:Type.String(),options:Type.Optional(Type.Array(Type.String()))}),
      async execute(_id,args,_signal,_update,ctx){const answer=args.options?.length?await ctx.ui.select(args.question,args.options):await ctx.ui.input(args.question);return {content:[{type:'text',text:answer===undefined?'User did not answer.':answer}],details:{}};}});
  };
}
