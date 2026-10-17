// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import {readFileSync,lstatSync,existsSync} from 'node:fs';
import {join,isAbsolute,resolve,sep} from 'node:path';
import {fileLeafName} from '../vendor/dsh-attachment/file-store.js';
import type {AgentSession} from '@earendil-works/pi-coding-agent';
import {identifier,type Data} from '../../protocol/src/index.js';
import {PiAttachments,promptAttachments,type PromptAttachment} from './attachments.js';
export const contentDigest=(content:unknown)=>createHash('sha256').update(JSON.stringify(content)).digest('hex');
export type HistoricalFileRule={kind:'dsh-file';identitySha256:string;file:Extract<PromptAttachment,{type:'file'}>;formerPaths:string[]};
export type RelocationRule={kind:'files';contentSha256:string;footer:string;files:PromptAttachment[]}|{kind:'dsh-archive';contentSha256:string;oldPath:string;archiveSha256:string}|HistoricalFileRule;
export interface RelocationBindings {schema:'augmentor-native-relocation-bindings/1';sourceStateSha256:string;rules:RelocationRule[]}
export const FILE_FOOTER_PREFIX='\n\nAttached files (read their exact contents using the file tools):\n';
function footerPaths(footer:string){return footer.slice(FILE_FOOTER_PREFIX.length).split('\n').map(line=>{const row=JSON.parse(line);if(typeof row.path!=='string'||row.path.length>8192)throw Error('Invalid managed attachment path.');return row.path as string;});}
/** File hints describe an attested stored reference, never a native message
 * replacement. Their separate key cannot impersonate a content digest. */
export function historicalFilePart(value:unknown):HistoricalFileRule['file']{
 const part=promptAttachments([value])[0];
 if(part.type!=='file'||Object.keys(part).sort().join(',')!=='attachment,type'||Object.keys(part.attachment).sort().join(',')!=='attachmentId,bytes,name'||typeof part.attachment.name!=='string'||part.attachment.name!==fileLeafName(part.attachment.name))throw Error('Invalid historical file binding.');
 return {type:'file',attachment:{attachmentId:part.attachment.attachmentId,name:part.attachment.name,bytes:part.attachment.bytes}};
}
export const historicalFileIdentity=(part:unknown)=>createHash('sha256').update('augmentor.dsh-file-hint/1\0'+JSON.stringify(historicalFilePart(part))).digest('hex');
export const relocationRuleKey=(rule:RelocationRule)=>rule.kind==='dsh-file'?'dsh-file:'+rule.identitySha256:rule.contentSha256;
function checkedHistoricalRule(rule:HistoricalFileRule):HistoricalFileRule{
 const file=historicalFilePart(rule.file),a=file.attachment,sha=a.attachmentId.slice(7),suffix=sep+join('attachments','v1','files',sha.slice(0,2),sha,a.name);
 if(Object.keys(rule).sort().join(',')!=='file,formerPaths,identitySha256,kind'||rule.identitySha256!==historicalFileIdentity(file)||!Array.isArray(rule.formerPaths)||!rule.formerPaths.length||rule.formerPaths.length>128||new Set(rule.formerPaths).size!==rule.formerPaths.length||rule.formerPaths.some(path=>typeof path!=='string'||path.length>8192||path.includes('\0')||!isAbsolute(path)||resolve(path)!==path||!path.endsWith(suffix)))throw Error('Invalid historical file path binding.');
 return {kind:'dsh-file',identitySha256:rule.identitySha256,file,formerPaths:[...rule.formerPaths].sort()};
}
export function mergeRelocationRule(rules:Map<string,RelocationRule>,incoming:RelocationRule){
 const rule=incoming.kind==='dsh-file'?checkedHistoricalRule(incoming):incoming,key=relocationRuleKey(rule),old=rules.get(key);
 if(old&&old.kind==='dsh-file'&&rule.kind==='dsh-file'){
  if(JSON.stringify(historicalFilePart(old.file))!==JSON.stringify(rule.file))throw Error('Historical relocation identities conflict.');
  rules.set(key,checkedHistoricalRule({...rule,formerPaths:[...new Set([...old.formerPaths,...rule.formerPaths])]}));
 }else{if(old&&JSON.stringify(old)!==JSON.stringify(rule))throw Error('Relocated ancestry has conflicting bindings.');rules.set(key,rule);}
}
export function relocationBindings(value:any):RelocationBindings{
 if(value?.schema!=='augmentor-native-relocation-bindings/1'||!/^[a-f0-9]{64}$/.test(value.sourceStateSha256)||!Array.isArray(value.rules)||value.rules.length>10000)throw Error('Invalid native relocation bindings.');
 const keys=new Set<string>();
 for(const rule of value.rules){
  if(!rule||typeof rule!=='object')throw Error('Invalid relocated binding.');
  if(rule.kind==='dsh-file')checkedHistoricalRule(rule);else if(!/^[a-f0-9]{64}$/.test(rule.contentSha256))throw Error('Invalid relocated message identity.');
  const key=relocationRuleKey(rule);if(keys.has(key))throw Error('Ambiguous relocated message identity.');keys.add(key);
  if(rule.kind==='dsh-file')continue;
  if(rule.kind==='files'){const files=promptAttachments(rule.files);if(!files.length||files.some(p=>p.type!=='file')||typeof rule.footer!=='string'||!rule.footer.startsWith(FILE_FOOTER_PREFIX)||rule.footer.length>65536||footerPaths(rule.footer).length!==files.length)throw Error('Invalid relocated file footer.');}
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
   for(const sid of this.ancestors()){const bindings=readRelocationBindings(this.state,sid);if(bindings)relocated=true;for(const rule of bindings?.rules??[])mergeRelocationRule(rules,rule);}
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
    }else if(rule.kind==='dsh-archive'){
     const details=message.role==='custom'?message.details as Data:undefined;
     if(message.role!=='custom'||message.customType!=='augmentor.dsh-history.v1'||details?.boundary!=='end-of-import'||details.archiveSha256!==rule.archiveSha256||typeof message.content!=='string'||!message.content.endsWith(rule.oldPath))throw Error('Relocated archive boundary is no longer exact.');
     const path=join(this.state,'dsh-imports',rule.archiveSha256+'.json'),stat=lstatSync(path);if(!stat.isFile()||stat.isSymbolicLink()||stat.size>32*1024*1024||createHash('sha256').update(readFileSync(path)).digest('hex')!==rule.archiveSha256)throw Error('Relocated DSH archive is unavailable or changed.');
     rebound.push({...message,content:message.content.slice(0,-rule.oldPath.length)+path});
    }else rebound.push(message);
   }
   // Summaries and tool transcripts can quote a former managed path after the
   // original upload message leaves active context. Keep those records intact;
   // supply a bounded, reverified map only for references still mentioned here.
   const activeText=rebound.flatMap(message=>[
    ...('content' in message?(typeof message.content==='string'?[message.content]:message.content.flatMap(part=>part.type==='text'?[part.text]:part.type==='toolCall'?[JSON.stringify(part.arguments)]:[])):[]),
    ...('summary' in message?[message.summary]:[]),...('output' in message?[message.output]:[])
   ]).join('\n'),paths=new Map<string,string>();
   const addPath=(former:string,current:string)=>{if(paths.has(former)&&paths.get(former)!==current)throw Error('Managed relocation paths conflict.');paths.set(former,current);if(paths.size>256)throw Error('Active attachment relocation references exceed their bound.');};
   for(const rule of rules.values())if(rule.kind==='files'){
    const old=footerPaths(rule.footer);if(!old.some(path=>activeText.includes(path)))continue;
    const resolved=await this.attachments.resolve(this.sid,'',rule.files),current=footerPaths(resolved.text);
    for(let i=0;i<old.length;i++)if(activeText.includes(old[i]))addPath(old[i],current[i]);
   }
   for(const rule of rules.values())if(rule.kind==='dsh-file'){
    const quoted=rule.formerPaths.filter(path=>activeText.includes(path));if(!quoted.length||!this.attachments.hasReference(this.sid,rule.file))continue;
    // Resolve on the descendant's authority, not on the ancestor carrying hints.
    const resolved=await this.attachments.resolve(this.sid,'',[rule.file]),current=footerPaths(resolved.text)[0];
    if(signal?.aborted)throw signal.reason??Error('Stopped during historical file binding.');
    for(const former of quoted)addPath(former,current);
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
