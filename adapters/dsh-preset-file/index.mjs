// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// DSH composition helper for owner-authored preset files. The UI never edits them.
import {readFileSync,watchFile,unwatchFile} from 'node:fs'
import {createRequire} from 'node:module'
import {join,isAbsolute} from 'node:path'
export const name='augmentor-preset-file'
export const inject=['agentPresets']
export async function apply(ctx,{id,directory,runtimeRoot}={}){
 if(typeof id!=='string'||! /^[A-Za-z0-9_.-]{1,128}$/.test(id)||!isAbsolute(directory||'')||!isAbsolute(runtimeRoot||''))throw Error('An explicit DSH preset ID, directory and runtime are required')
 const {parse}=createRequire(join(runtimeRoot,'package.json'))('yaml')
 const options={customTags:[{tag:'tag:yaml.org,2002:js',resolve:text=>({__jsExpr:text})}]}
 const file=join(directory,'agent.cordis.yml'),metadata=join(directory,'preset.yml')
 let release,closed=false,queue=Promise.resolve()
 const mount=async()=>{
  // A missing or malformed replacement must not leave a stale definition selectable.
  await release?.();release=undefined
  const plugins=parse(readFileSync(file,'utf8'),options),description=parse(readFileSync(metadata,'utf8'),options)
  if(!Array.isArray(plugins)||!description||typeof description!=='object')throw Error('Invalid owner-authored DSH preset files')
  if(!closed)release=await ctx.agentPresets.register({id,name:description.name,description:description.description,plugins})
 }
 await mount()
 const changed=()=>{queue=queue.then(mount).catch(error=>{console.error('[augmentor-preset-file] Could not reload selected preset:',id,error.message)})}
 watchFile(file,{interval:1000},changed);watchFile(metadata,{interval:1000},changed)
 ctx.effect(()=>async()=>{closed=true;unwatchFile(file,changed);unwatchFile(metadata,changed);await queue;await release?.()})
}
