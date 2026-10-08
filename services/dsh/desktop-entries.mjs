// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Native presentation ownership grants no tools, instructions or memory.
import {readFileSync,realpathSync} from 'node:fs'
import {join,resolve,isAbsolute} from 'node:path'
import {homedir} from 'node:os'
import {ownsProductSession} from '../workspaces/profiles.mjs'
const canonical=p=>{try{return realpathSync(p)}catch{return resolve(p)}}
export function desktopEntries(retained=false){
 const path=process.env.AUGMENTOR_AGENT_ENTRIES||join(process.env.XDG_CONFIG_HOME||join(homedir(),'.config'),'augmentor','agents.json')
 let value;try{value=JSON.parse(readFileSync(path,'utf8'))}catch(e){if(e.code==='ENOENT')return [];throw e}
 if(value.version!==1||!Array.isArray(value.entries)||!Array.isArray(value.retained))throw Error('Invalid desktop Agents registry')
 return [...value.entries,...retained?value.retained:[]].filter(e=>typeof e.preset==='string'&&/^[A-Za-z0-9_.-]{1,128}$/.test(e.preset)&&typeof e.cwd==='string'&&isAbsolute(e.cwd))
}
export function ownsNativeSession(row,{retained=false}={}){
 if(ownsProductSession(row))return true
 return row?.origin!=='subagent'&&typeof row?.cwd==='string'&&desktopEntries(retained).some(e=>e.preset===row.agentPreset&&canonical(e.cwd)===canonical(row.cwd))
}
