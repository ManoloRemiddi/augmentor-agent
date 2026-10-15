// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {constants} from 'node:fs';
import {open,stat} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {stripFrontmatter} from '@earendil-works/pi-coding-agent';

export interface ApprovedSkill {name:string;description:string;filePath:string;baseDir:string;source?:string;disableModelInvocation?:boolean}
export const SKILL_SOURCE_LIMIT=1024*1024;
export const SKILL_COMMAND_NAMES=new Set(['file','goal','plan','compact','permission','model','prompts','jobs','context','inspect','export','feedback']);
const sha=(value:string|Uint8Array)=>createHash('sha256').update(value).digest('hex');
const alias=(name:string)=>/^[\w-]+$/.test(name)&&!SKILL_COMMAND_NAMES.has(name);
export function skillSelector(input:string){
 const match=/^\/([^\s]+)(?:\s+([\s\S]*))?$/.exec(input.trim());
 if(!match)return;
 const explicit=match[1]!.startsWith('skill:'),name=explicit?match[1]!.slice(6):match[1]!;
 if(!name||!explicit&&!alias(name))return;
 return {name,args:match[2]?.trim()??'',explicit};
}
export function skillCatalog(skills:readonly ApprovedSkill[],occupied:(name:string)=>boolean=()=>false){
 if(skills.length>2048)throw Error('The approved skill catalog exceeds the bounded discovery limit. Explicit SDK skill commands remain available.');
 const rows=skills.map(skill=>({name:skill.name,path:skill.filePath,description:skill.description,command:alias(skill.name)&&!occupied(skill.name)?'/'+skill.name:'/skill:'+skill.name,modelInvocable:skill.disableModelInvocation!==true}));
 const encoded=JSON.stringify(rows);if(Buffer.byteLength(encoded)>SKILL_SOURCE_LIMIT)throw Error('The approved skill metadata exceeds the bounded discovery limit.');
 return {available:true,revision:sha(encoded),skills:rows,origin:'current public SDK resource catalog; no skill bodies read'};
}
export interface SkillReceipt {version:1;name:string;path:string;sourceSha256:string;instructionsSha256:string;expandedInputSha256:string;sourceBytes:number;instructionCharacters:number;instructionCharacterUnits:'unicode-code-points';boundary:'managed-input-read; delivered-sdk-user-message'}
export interface PreparedSkill {text:string;receipt:SkillReceipt}
const identity=(s:any)=>[s.dev,s.ino,s.size,s.mtimeNs,s.ctimeNs].map(String).join(':');
/** Read only the exact resource already approved by the SDK loader. The public
 * input transform uses the pinned SDK's skill-block format; AgentSession still
 * owns delivery, templates, context, model and tools. A receipt is published only
 * when the actual delivered user text matches this complete expansion. */
export async function prepareApprovedSkill(skills:readonly ApprovedSkill[],input:string,occupied:(name:string)=>boolean=()=>false):Promise<PreparedSkill|undefined>{
 const selected=skillSelector(input);if(!selected||!selected.explicit&&occupied(selected.name))return;
 const skill=skills.find(row=>row.name===selected.name);if(!skill)return;
 const handle=await open(skill.filePath,constants.O_RDONLY|(constants.O_NONBLOCK??0));
 try{
  const before=await handle.stat({bigint:true});if(!before.isFile()||before.size>BigInt(SKILL_SOURCE_LIMIT))throw Error('The approved skill source is not a regular file within its one MiB limit.');
  const buffer=Buffer.alloc(Number(before.size)+1);let used=0;
  while(used<buffer.length){const read=await handle.read(buffer,used,buffer.length-used,used);if(!read.bytesRead)break;used+=read.bytesRead;}
  if(used!==Number(before.size)||identity(before)!==identity(await handle.stat({bigint:true}))||identity(before)!==identity(await stat(skill.filePath,{bigint:true})))throw Error('The approved skill source changed during input preparation. Nothing was sent to the model.');
  const bytes=buffer.subarray(0,used),source=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(bytes),body=stripFrontmatter(source).trim();
  const block='<skill name="'+skill.name+'" location="'+skill.filePath+'">\nReferences are relative to '+skill.baseDir+'.\n\n'+body+'\n</skill>',text=block+(selected.args?'\n\n'+selected.args:'');
  let instructionCharacters=0;for(const _ of body)instructionCharacters++;
  return {text,receipt:{version:1,name:skill.name,path:skill.filePath,sourceSha256:sha(bytes),instructionsSha256:sha(body),expandedInputSha256:sha(text),sourceBytes:bytes.length,instructionCharacters,instructionCharacterUnits:'unicode-code-points',boundary:'managed-input-read; delivered-sdk-user-message'}};
 }finally{await handle.close();}
}
export function deliveredSkill(prepared:PreparedSkill|undefined,content:unknown){
 if(!prepared||!Array.isArray(content))return;
 const text=content.filter(row=>row?.type==='text').map(row=>row.text).join('\n');
 return text===prepared.text?structuredClone(prepared.receipt):undefined;
}
