// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import {readFileSync,lstatSync,existsSync} from 'node:fs';
import {join} from 'node:path';
import type {AgentSession} from '@earendil-works/pi-coding-agent';
import {identifier,type Data} from '../../protocol/src/index.js';
import {PiAttachments,promptAttachments,type PromptAttachment} from './attachments.js';
export const contentDigest=(content:unknown)=>createHash('sha256').update(JSON.stringify(content)).digest('hex');
export type RelocationRule={kind:'files';contentSha256:string;footer:string;files:PromptAttachment[]}|{kind:'dsh-archive';contentSha256:string;oldPath:string;archiveSha256:string};
export interface RelocationBindings {schema:'augmentor-native-relocation-bindings/1';sourceStateSha256:string;rules:RelocationRule[]}
const footerPrefix='\n\nAttached files (read their exact contents using the file tools):\n';
function footerPaths(footer:string){return footer.slice(footerPrefix.length).split('\n').map(line=>{const row=JSON.parse(line);if(typeof row.path!=='string'||row.path.length>8192)throw Error('Invalid managed attachment path.');return row.path as string;});}
export function relocationBindings(value:any):RelocationBindings{
 if(value?.schema!=='augmentor-native-relocation-bindings/1'||!/^[a-f0-9]{64}$/.test(value.sourceStateSha256)||!Array.isArray(value.rules)||value.rules.length>10000)throw Error('Invalid native relocation bindings.');
 const keys=new Set<string>();
 for(const rule of value.rules){
  if(!/^[a-f0-9]{64}$/.test(rule?.contentSha256)||keys.has(rule.contentSha256))throw Error('Ambiguous relocated message identity.');keys.add(rule.contentSha256);
  if(rule.kind==='files'){const files=promptAttachments(rule.files);if(!files.length||files.some(p=>p.type!=='file')||typeof rule.footer!=='string'||!rule.footer.startsWith(footerPrefix)||rule.footer.length>65536||footerPaths(rule.footer).length!==files.length)throw Error('Invalid relocated file footer.');}
  else if(rule.kind!=='dsh-archive'||typeof rule.oldPath!=='string'||rule.oldPath.length>4096||!/^[a-f0-9]{64}$/.test(rule.archiveSha256))throw Error('Unsupported native relocation rule.');
 }
 return value;
}
export function readRelocationBindings(state:string,sid:string):RelocationBindings|undefined{
 const path=join(state,'native-relocations',identifier(sid)+'.json');if(!existsSync(path))return;
 const stat=lstatSync(path);if(!stat.isFile()||stat.isSymbolicLink()||stat.uid!==process.getuid?.()||(stat.mode&0o077)||stat.size>1024*1024)throw Error('Relocation bindings need a bounded private owned file.');
 return relocationBindings(JSON.parse(readFileSync(path,'utf8')));
}
/** Bind app-owned references before resource transforms, on active context only.
 * Canonical native/display records and historical quotes remain unchanged.
 * Descendants still authorize every file against their own inherited receipts. */
export class PiNativeRelocationContext {
 private undo?:()=>void;
 constructor(private state:string,private sid:string,private attachments:PiAttachments,private ancestors:()=>string[]){}
 install(session:AgentSession){
  this.dispose();const previous=session.agent.transformContext;
  const hook:typeof previous=async(messages,signal)=>{
   const rules=new Map<string,RelocationRule>();let relocated=false;
   for(const sid of this.ancestors()){const bindings=readRelocationBindings(this.state,sid);if(bindings)relocated=true;for(const rule of bindings?.rules??[]){const old=rules.get(rule.contentSha256);if(old&&JSON.stringify(old)!==JSON.stringify(rule))throw Error('Relocated ancestry has conflicting bindings.');rules.set(rule.contentSha256,rule);}}
   if(!relocated)return previous?previous(messages,signal):messages;
   if(!session.model?.input.includes('image')&&messages.some(m=>'content' in m&&Array.isArray(m.content)&&m.content.some(p=>p.type==='image')))throw Error('Relocated history contains images. Select a model with image input before continuing.');
   const rebound=[];
   for(const message of messages){
    if(signal?.aborted)throw signal.reason??Error('Stopped during native reference binding.');
    if(message.role!=='user'&&message.role!=='custom'){rebound.push(message);continue;}
    const rule=rules.get(contentDigest(message.content));if(!rule){rebound.push(message);continue;}
    if(rule.kind==='files'){
     if(message.role!=='user')throw Error('Relocated file identity changed role.');
     const resolved=await this.attachments.resolve(this.sid,'',rule.files);
     let matched=0;
     const replace=(text:string)=>text.endsWith(rule.footer)?(matched++,text.slice(0,-rule.footer.length)+resolved.text):text;
     const content=typeof message.content==='string'?replace(message.content):message.content.map(part=>part.type==='text'?{...part,text:replace(part.text)}:part);
     if(matched!==1)throw Error('Relocated file footer is no longer exact.');rebound.push({...message,content});
    }else{
     const details=message.role==='custom'?message.details as Data:undefined;
     if(message.role!=='custom'||message.customType!=='augmentor.dsh-history.v1'||details?.boundary!=='end-of-import'||details.archiveSha256!==rule.archiveSha256||typeof message.content!=='string'||!message.content.endsWith(rule.oldPath))throw Error('Relocated archive boundary is no longer exact.');
     const path=join(this.state,'dsh-imports',rule.archiveSha256+'.json'),stat=lstatSync(path);if(!stat.isFile()||stat.isSymbolicLink()||stat.size>32*1024*1024||createHash('sha256').update(readFileSync(path)).digest('hex')!==rule.archiveSha256)throw Error('Relocated DSH archive is unavailable or changed.');
     rebound.push({...message,content:message.content.slice(0,-rule.oldPath.length)+path});
    }
   }
   // Summaries and tool transcripts can quote a former managed path after the
   // original upload message leaves active context. Keep those records intact;
   // supply a bounded, reverified map only for references still mentioned here.
   const activeText=rebound.flatMap(message=>[
    ...('content' in message?(typeof message.content==='string'?[message.content]:message.content.flatMap(part=>part.type==='text'?[part.text]:part.type==='toolCall'?[JSON.stringify(part.arguments)]:[])):[]),
    ...('summary' in message?[message.summary]:[]),...('output' in message?[message.output]:[])
   ]).join('\n'),paths=new Map<string,string>();
   for(const rule of rules.values())if(rule.kind==='files'){
    const old=footerPaths(rule.footer);if(!old.some(path=>activeText.includes(path)))continue;
    const resolved=await this.attachments.resolve(this.sid,'',rule.files),current=footerPaths(resolved.text);
    for(let i=0;i<old.length;i++)if(activeText.includes(old[i])){if(paths.has(old[i])&&paths.get(old[i])!==current[i])throw Error('Managed relocation paths conflict.');paths.set(old[i],current[i]);}
   }
   if(paths.size){
    const content='Managed attachments were copied into this profile. When reading a former managed path quoted in history, use its verified current path below. Historical actions were not repeated.\n'+JSON.stringify([...paths].map(([former,current])=>({former,current})));
    if(paths.size>256||Buffer.byteLength(content)>32768)throw Error('Active attachment relocation references exceed their bound.');
    const lastUser=rebound.findLastIndex(message=>message.role==='user');rebound.splice(lastUser<0?rebound.length:lastUser,0,{role:'custom',customType:'augmentor.native-relocation.v1',content,display:false,timestamp:Date.now()});
   }
   if(signal?.aborted)throw signal.reason??Error('Stopped during native reference binding.');
   return previous?previous(rebound,signal):rebound;
  };
  session.agent.transformContext=hook;this.undo=()=>{if(session.agent.transformContext===hook)session.agent.transformContext=previous;};
 }
 dispose(){this.undo?.();this.undo=undefined;}
}
