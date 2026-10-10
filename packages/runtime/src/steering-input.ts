// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFileSync} from 'node:fs';
import {stripFrontmatter,type AgentSession} from '@earendil-works/pi-coding-agent';
import type {ImageContent} from '@earendil-works/pi-ai';
import {expandPromptTemplate} from '../vendor/pi/prompt-template.js';

export interface SteeringInput {action:'queued'|'handled';text?:string;images?:ImageContent[];handler:'continue'|'transform'|'handled';skill?:string;template?:string}
/** SDK-public input chain plus expansion over the session's approved resources.
 * The identified AgentMessage is built only after preparation, outside the SDK
 * string queue. This preserves exact ownership without touching private state.
 */
export function validateSteeringInput(session:AgentSession,text:string){
 if(!text.startsWith('/'))return;
 const space=text.indexOf(' '),name=space===-1?text.slice(1):text.slice(1,space);
 if(session.extensionRunner.getCommand(name))throw Error('Extension command "/'+name+'" cannot be queued as a correction.');
}
export async function prepareSteeringInput(session:AgentSession,text:string):Promise<SteeringInput>{
 const runner=session.extensionRunner;
 const processed=runner.hasHandlers('input')?await runner.emitInput(text,undefined,'rpc','steer'):{action:'continue' as const};
 if(processed.action==='handled')return {action:'handled',handler:'handled'};
 let expanded=processed.action==='transform'?processed.text:text;const images=processed.action==='transform'?processed.images:undefined;
 let skillName:string|undefined;
 if(expanded.startsWith('/skill:')){
  const space=expanded.indexOf(' '),name=space===-1?expanded.slice(7):expanded.slice(7,space),args=space===-1?'':expanded.slice(space+1).trim();
  const skill=session.resourceLoader.getSkills().skills.find(item=>item.name===name);
  if(skill)try{
   const body=stripFrontmatter(readFileSync(skill.filePath,'utf8')).trim();
   expanded='<skill name="'+skill.name+'" location="'+skill.filePath+'">\nReferences are relative to '+skill.baseDir+'.\n\n'+body+'\n</skill>'+(args?'\n\n'+args:'');skillName=skill.name;
  }catch(error){runner.emitError({extensionPath:skill.filePath,event:'skill_expansion',error:error instanceof Error?error.message:String(error)});}
 }
 const templates=[...session.promptTemplates],templateName=expanded.match(/^\/([^\s]+)(?:\s+[\s\S]*)?$/)?.[1];
 const template=templates.find(item=>item.name===templateName);expanded=expandPromptTemplate(expanded,templates);
 return {action:'queued',text:expanded,images,handler:processed.action,...(skillName?{skill:skillName}:{}),...(template?{template:template.name}:{})};
}
