// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFileSync,writeFileSync,mkdirSync,existsSync,openSync,closeSync,unlinkSync,renameSync,fsyncSync} from 'node:fs'
import {join,isAbsolute} from 'node:path'
import {pathToFileURL} from 'node:url'
import {randomUUID,createHash} from 'node:crypto'
import {validateProfile} from './profiles.mjs'
const read=(p,fallback)=>{try{return JSON.parse(readFileSync(p,'utf8'))}catch(e){if(e.code==='ENOENT')return fallback;throw e}}
function atomic(file,bytes){const temp=file+'.'+randomUUID()+'.tmp';const fd=openSync(temp,'wx',0o600);try{writeFileSync(fd,bytes);fsyncSync(fd)}finally{closeSync(fd)}renameSync(temp,file)}
function acquire(dir){mkdirSync(dir,{recursive:true,mode:0o700});const file=join(dir,'.install.lock');let fd;try{fd=openSync(file,'wx',0o600)}catch{throw Error('Another profile install is active or interrupted. Recover an interrupted install before retrying.')};writeFileSync(fd,JSON.stringify({pid:process.pid}));closeSync(fd);return ()=>unlinkSync(file)}
function rollback(journal){for(const f of journal.files){if(f.before===null){try{unlinkSync(f.path)}catch(e){if(e.code!=='ENOENT')throw e}}else atomic(f.path,Buffer.from(f.before,'base64'))}try{unlinkSync(journal.marker)}catch(e){if(e.code!=='ENOENT')throw e}}
export function recoverInstall({profilesDir}){
 const file=join(profilesDir,'.install.lock'),lock=read(file,null);if(!lock)return false
 try{process.kill(lock.pid,0);throw Error('The installer is still running')}catch(e){if(e.code!=='ESRCH')throw e}
 const journalFile=join(profilesDir,'.install-journal.json'),journal=read(journalFile,null)
 if(journal){rollback(journal);unlinkSync(journalFile)}
 unlinkSync(file);return true
}
export function installProfile(input,{root,home,profilesDir,fault=()=>{}}){
 const profile=validateProfile(input),releaseLock=acquire(profilesDir),journalFile=join(profilesDir,'.install-journal.json');let journal
 try{
  if(existsSync(journalFile))throw Error('An incomplete profile transaction needs recovery')
  const ids=read(join(profilesDir,'index.json'),[])
  if(!Array.isArray(ids)||ids.length>=100&&!ids.includes(profile.id))throw Error('Invalid or full workspace registry')
  for(const id of ids){
   const old=validateProfile(read(join(profilesDir,id+'.json'),null),id)
   if(id!==profile.id&&(old.preset===profile.preset||(old.memory.person===profile.memory.person&&old.memory.project===profile.memory.project)))throw Error('Preset or memory identity already belongs to another workspace')
   if(id===profile.id&&['preset','cwd'].some(k=>old[k]!==profile[k]))throw Error('Workspace identity migration requires an explicit separate migration')
   if(id===profile.id&&(old.memory.person!==profile.memory.person||old.memory.project!==profile.memory.project))throw Error('Existing workspace memory identity must be preserved')
  }
  const directory=join(home,'.agent-presets',profile.preset)
  if(!ids.includes(profile.id)&&existsSync(directory))throw Error('Preset directory already exists outside this workspace registry')
  const rows=JSON.parse(readFileSync(join(home,'.agent-presets','augmentor-browser-product','agent.cordis.yml'),'utf8').replace(/^#.*$/gm,''))
  const persona=rows.find(row=>row.id==='persona');if(!persona)throw Error('Installed Browser preset is missing its persona')
  const instructions=(profile.instructions||[]).map(file=>readFileSync(file,'utf8')).join('\n\n');if(!instructions.trim())throw Error('An explicit application role is required')
  persona.config={...persona.config,prefix:persona.config.prefix+'\n\n# Assigned workspace role\n'+instructions}
  const relocate=rows=>{for(const row of rows){if(typeof row.name==='string'&&row.name.includes('/adapters/')){const target=join(root,'adapters',row.name.split('/adapters/').at(-1));if(existsSync(target))row.name=target}if(Array.isArray(row.config))relocate(row.config)}};relocate(rows)
  const composed=rows.filter(row=>!(profile.retiredPluginIds||[]).includes(row.id));composed.push({id:'augmentor-workspace-context',name:join(root,'adapters/dsh-workspace/index.mjs')})
  const planned=[]
  if(profile.sdkProtocol)composed.push({id:'augmentor-workspace-policy',name:join(root,'adapters/dsh-workspace/policy.mjs'),config:{profileId:profile.id}})
  const pluginIds=new Set(composed.map(row=>row.id))
  for(const plugin of profile.tools||[]){
   if(!/^[a-z][a-z0-9-]{0,63}$/.test(plugin.id)||pluginIds.has(plugin.id)||!isAbsolute(plugin.module))throw Error('Invalid or duplicate application tool plugin')
   pluginIds.add(plugin.id);const digest=createHash('sha256').update(readFileSync(plugin.module)).digest('hex').slice(0,12),name=join(directory,plugin.id+'-'+digest+'.mjs')
   planned.push({path:name,bytes:'// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\nexport * from '+JSON.stringify(pathToFileURL(plugin.module).href+'?v='+digest)+';\n'})
   composed.push({id:plugin.id,name,config:plugin.config||{}})
  }
  planned.push(...[['agent.cordis.yml',composed],['preset.yml',{name:profile.name,description:profile.description}]].map(([n,v])=>({path:join(directory,n),bytes:JSON.stringify(v,null,2)+'\n'})))
  planned.push({path:join(profilesDir,profile.id+'.json'),bytes:JSON.stringify(profile,null,2)+'\n'},{path:join(profilesDir,'index.json'),bytes:JSON.stringify([...new Set([...ids,profile.id])])+'\n'})
  mkdirSync(directory,{recursive:true,mode:0o700})
  journal={marker:join(profilesDir,profile.id+'.installing'),files:planned.map(f=>({...f,before:existsSync(f.path)?readFileSync(f.path).toString('base64'):null}))}
  const backups=join(profilesDir,'.backups');mkdirSync(backups,{recursive:true,mode:0o700});
  atomic(join(backups,Date.now()+'-'+profile.id+'-'+randomUUID()+'.json'),JSON.stringify(journal));
  atomic(journalFile,JSON.stringify(journal));atomic(journal.marker,'Installation in progress\n')
  for(let i=0;i<planned.length;i++){atomic(planned[i].path,planned[i].bytes);fault(i)}
  unlinkSync(journal.marker);unlinkSync(journalFile);journal=null
  return profile
 }catch(error){if(journal){rollback(journal);unlinkSync(journalFile)}throw error}finally{if(!existsSync(journalFile))releaseLock()}
}
