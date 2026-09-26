// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Owner-installed profiles specialize the existing product; they never own an agent loop.
import {readFileSync,realpathSync,mkdirSync,writeFileSync,renameSync} from 'node:fs'
import {join,resolve} from 'node:path'
import {homedir} from 'node:os'
export const profileDirectory=()=>process.env.AUGMENTOR_WORKSPACE_PROFILES||join(process.env.XDG_CONFIG_HOME||join(homedir(),'.config'),'augmentor','workspaces')
export function canonical(value){try{return realpathSync(value)}catch{return resolve(value)}}
export function validateProfile(p,id=p?.id){
 if(!p||!/^[a-z][a-z0-9-]{0,63}$/.test(id)||p.id!==id||!/^augmentor-[a-z0-9-]+$/.test(p.preset)||!p.cwd?.startsWith('/')||!p.memory?.person||!p.memory?.project)throw Error('Invalid Augmentor workspace profile')
 const parent=new URL(p.parentOrigin)
 if(parent.origin!==p.parentOrigin||!['http:','https:'].includes(parent.protocol))throw Error('Invalid workspace parent origin')
 if(!p.publicPath?.startsWith('/')||!p.publicPath.endsWith('/')||p.publicPath.includes('..')||!/^\/[a-zA-Z0-9/_-]+\/$/.test(p.publicPath))throw Error('Invalid workspace public path')
 return {...p,cwd:canonical(p.cwd),legacyPresets:p.legacyPresets||[]}
}
export function loadProfile(id=process.env.AUGMENTOR_WORKSPACE_PROFILE){
 if(!id)return null
 if(!/^[a-z][a-z0-9-]{0,63}$/.test(id))throw Error('Invalid workspace identifier')
 return validateProfile(JSON.parse(readFileSync(join(profileDirectory(),id+'.json'),'utf8')),id)
}
export function profiles(){
 // A single owner-controlled registry permits custom presets across the shared DSH host.
 let ids;try{ids=JSON.parse(readFileSync(join(profileDirectory(),'index.json'),'utf8'))}catch(e){if(e.code==='ENOENT')return [];throw e}
 if(!Array.isArray(ids)||ids.length>100)throw Error('Invalid workspace registry')
 return ids.map(loadProfile)
}
export const profileForSession=row=>profiles().find(p=>row?.agentPreset===p.preset&&typeof row.cwd==='string'&&canonical(row.cwd)===p.cwd)
export const ownsProductSession=row=>row?.origin!=='subagent'&&(['augmentor-browser-product','augmentor-linux-product'].includes(row?.agentPreset)||!!profileForSession(row))
export const visibleInProfile=(p,row)=>row.origin!=='subagent'&&typeof row.cwd==='string'&&canonical(row.cwd)===p.cwd&&[p.preset,...p.legacyPresets].includes(row.agentPreset)
export function profileStatePath(p){const dir=join(process.env.XDG_STATE_HOME||join(homedir(),'.local/state'),'augmentor','workspaces',p.id);mkdirSync(dir,{recursive:true,mode:0o700});return join(dir,'preferences.json')}
export function preferences(p,update){
 const file=profileStatePath(p);let value={};try{value=JSON.parse(readFileSync(file,'utf8'))}catch(e){if(e.code!=='ENOENT')throw e}
 if(update){if(!update||typeof update!=='object'||Array.isArray(update)||Object.keys(update.set||{}).some(k=>['__proto__','constructor','prototype'].includes(k)))throw Error('Invalid workspace preferences');value={...value,...update.set};for(const k of update.remove||[])delete value[k];for(const key of Object.keys(value).filter(k=>k.startsWith('context:')).sort((a,b)=>(value[b]?.at||0)-(value[a]?.at||0)).slice(32))delete value[key];if(Buffer.byteLength(JSON.stringify(value))>1024*1024)throw Error('Workspace preferences too large');const tmp=file+'.tmp';writeFileSync(tmp,JSON.stringify(value),{mode:0o600});renameSync(tmp,file)}
 return value
}
