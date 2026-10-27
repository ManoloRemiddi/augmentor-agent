// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {Type} from 'typebox';
import type {ExtensionAPI} from '@earendil-works/pi-coding-agent';
export function artifactTools(open:(path:string,executorId:string|undefined,signal:AbortSignal|undefined)=>Promise<unknown>){return(pi:ExtensionAPI)=>{
 pi.registerTool({name:'open_artifact',label:'Open generated artifact',description:'Open an existing generated HTML or text file through Augmentor’s scoped local preview in a new visible browser tab. Use this instead of launching a GUI program in a foreground shell. The file is read through the existing verified preview path; the return distinguishes browser dispatch from document loading. executorId selects the intended browser when several profiles are connected.',parameters:Type.Object({path:Type.String({minLength:1,maxLength:4096}),executorId:Type.Optional(Type.String())}),
  execute:async(_id,args,signal)=>({content:[{type:'text' as const,text:JSON.stringify(await open(args.path,args.executorId,signal))}],details:{}})});
};}
