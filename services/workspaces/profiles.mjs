// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Owner-installed profiles specialize the existing product; they never own an agent loop.
import {readFileSync,realpathSync,writeFileSync,renameSync,existsSync} from 'node:fs'
import {join,resolve,isAbsolute} from 'node:path'
import {DatabaseSync} from 'node:sqlite'
import {randomUUID} from 'node:crypto'
import {homedir} from 'node:os'
import {privateDirectory} from './private.mjs'
export const profileDirectory=()=>process.env.AUGMENTOR_WORKSPACE_PROFILES||join(process.env.XDG_CONFIG_HOME||join(homedir(),'.config'),'augmentor','workspaces')
export function canonical(value){try{return realpathSync(value)}catch{return resolve(value)}}
export function validateProfile(p,id=p?.id){
 if(!p||!/^[a-z][a-z0-9-]{0,63}$/.test(id)||p.id!==id||!/^augmentor-[a-z0-9-]+$/.test(p.preset)||typeof p.cwd!=='string'||!isAbsolute(p.cwd)||!p.memory?.person||!p.memory?.project)throw Error('Invalid Augmentor workspace profile')
 if(p.harness!==undefined&&!['dsh','codex'].includes(p.harness))throw Error('Unsupported application workspace harness')
 if(p.harness==='codex'&&(!p.sdkProtocol||typeof p.connection!=='string'||!/^[A-Za-z0-9_.:-]{1,160}$/.test(p.connection)))throw Error('Codex workspaces require an explicit connection profile')
 if(p.harness==='codex'&&process.platform==='win32')throw Error('This release has no Windows Codex application adapter')
 if(p.sdkProtocol && (p.sdkProtocol!=='augmentor-app/1'||p.schemaVersion!==1||!p.policy||!Array.isArray(p.policy.tools)||p.policy.tools.some(n=>typeof n!=='string'||!/^[A-Za-z][A-Za-z0-9_]{0,127}$/.test(n))||typeof p.policy.voice!=='boolean'||p.policy.sharedSettings!==false))throw Error('Invalid SDK workspace policy')
 const parent=new URL(p.parentOrigin)
 if(parent.origin!==p.parentOrigin||!['http:','https:'].includes(parent.protocol))throw Error('Invalid workspace parent origin')
 if(!p.publicPath?.startsWith('/')||!p.publicPath.endsWith('/')||p.publicPath.includes('..')||!/^\/[a-zA-Z0-9/_-]+\/$/.test(p.publicPath))throw Error('Invalid workspace public path')
 return {...p,cwd:canonical(p.cwd),legacyPresets:p.legacyPresets||[]}
}
export function loadProfile(id=process.env.AUGMENTOR_WORKSPACE_PROFILE){
 if(!id)return null
 if(!/^[a-z][a-z0-9-]{0,63}$/.test(id))throw Error('Invalid workspace identifier')
 if(existsSync(join(profileDirectory(),id+'.installing')))throw Error('Workspace installation is incomplete; recover it before connecting')
 return validateProfile(JSON.parse(readFileSync(join(profileDirectory(),id+'.json'),'utf8')),id)
}
export function profiles(){
 // A single owner-controlled registry permits custom presets across the shared DSH host.
 let ids;try{ids=JSON.parse(readFileSync(join(profileDirectory(),'index.json'),'utf8'))}catch(e){if(e.code==='ENOENT')return [];throw e}
 if(!Array.isArray(ids)||ids.length>100)throw Error('Invalid workspace registry')
 return ids.filter(id=>!existsSync(join(profileDirectory(),id+'.installing'))).map(loadProfile)
}
export const profileForSession=row=>profiles().find(p=>row?.agentPreset===p.preset&&typeof row.cwd==='string'&&canonical(row.cwd)===p.cwd)
export const ownsProductSession=row=>row?.origin!=='subagent'&&(['augmentor-browser-product','augmentor-linux-product'].includes(row?.agentPreset)||!!profileForSession(row))
export const visibleInProfile=(p,row)=>row.origin!=='subagent'&&typeof row.cwd==='string'&&canonical(row.cwd)===p.cwd&&[p.preset,...p.legacyPresets].includes(row.agentPreset)
export function profileStatePath(p){const dir=join(process.env.XDG_STATE_HOME||join(homedir(),'.local/state'),'augmentor','workspaces',p.id);privateDirectory(dir);return join(dir,'preferences.json')}
export function preferences(p,update){
 const file=profileStatePath(p);let lock;
 // SQLite supplies a process-owned lock that the OS releases after a crash.
 // JSON remains the canonical format for compatibility with existing releases.
 if(update){lock=new DatabaseSync(file+'.lock.sqlite');try{lock.exec('PRAGMA busy_timeout=5000; BEGIN IMMEDIATE')}catch(error){lock.close();throw error}}
 try{let value={};try{value=JSON.parse(readFileSync(file,'utf8'))}catch(e){if(e.code!=='ENOENT')throw e}
 if(update){if(!update||typeof update!=='object'||Array.isArray(update)||update.set&&(typeof update.set!=='object'||Array.isArray(update.set))||update.remove&&(!Array.isArray(update.remove)||update.remove.some(k=>typeof k!=='string'))||Object.keys(update.set||{}).some(k=>['__proto__','constructor','prototype'].includes(k)))throw Error('Invalid workspace preferences');value={...value,...update.set};for(const k of update.remove||[])delete value[k];for(const key of Object.keys(value).filter(k=>k.startsWith('context:')).sort((a,b)=>(value[b]?.at||0)-(value[a]?.at||0)).slice(32))delete value[key];if(Buffer.byteLength(JSON.stringify(value))>1024*1024)throw Error('Workspace preferences too large');const tmp=file+'.'+randomUUID()+'.tmp';writeFileSync(tmp,JSON.stringify(value),{mode:0o600});renameSync(tmp,file)}
 return value
 }finally{lock?.close()}
}
