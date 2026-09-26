#!/usr/bin/env node
// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Compose a specialist from the installed Browser preset, retaining its harness,
// context management, tools and memory. Application files contain the specialization.
import {readFileSync,writeFileSync,mkdirSync,copyFileSync} from 'node:fs'
import {join,resolve} from 'node:path'
import {homedir} from 'node:os'
import {pathToFileURL,fileURLToPath} from 'node:url'
import {createHash} from 'node:crypto'
import {profileDirectory,validateProfile,profiles} from '../services/workspaces/profiles.mjs'
const source=process.argv[2];if(!source)throw Error('Usage: install-workspace-profile.mjs /absolute/profile.json')
const profile=validateProfile(JSON.parse(readFileSync(source,'utf8')))
const root=fileURLToPath(new URL('../',import.meta.url)),home=process.env.DSH_HOME||join(homedir(),'.dsh')
const directory=join(home,'.agent-presets',profile.preset);mkdirSync(directory,{recursive:true,mode:0o700})
const rows=JSON.parse(readFileSync(join(home,'.agent-presets','augmentor-browser-product','agent.cordis.yml'),'utf8').replace(/^#.*$/gm,''))
const persona=rows.find(row=>row.id==='persona');if(!persona)throw Error('Installed Browser preset is missing its persona')
const instructions=(profile.instructions||[]).map(file=>readFileSync(file,'utf8')).join('\n\n')
if(!instructions.trim())throw Error('A specialist needs an explicit job description')
persona.config={...persona.config,prefix:persona.config.prefix+'\n\n# Assigned workspace role\n'+instructions}
for(const [id,folder] of [['augmentor-memory','dsh-memory'],['augmentor-execution','dsh-execution']]){
 const row=rows.find(row=>row.id===id);if(!row)throw Error('Installed Browser preset is missing '+id);row.name=join(root,'adapters',folder,'index.mjs')
}
// Migration IDs must be explicitly supplied; never copy an app's old product override.
const composed=rows.filter(row=>!(profile.retiredPluginIds||[]).includes(row.id))
composed.push({id:"augmentor-workspace-context",name:join(root,"adapters/dsh-workspace/index.mjs")})
for(const plugin of profile.tools||[]){if(!plugin.id||!plugin.module?.startsWith('/'))throw Error('Tool modules must be installed local paths');const digest=createHash('sha256').update(readFileSync(plugin.module)).digest('hex').slice(0,12);const name=join(directory,plugin.id+'-'+digest+'.mjs');writeFileSync(name,'// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\nexport * from '+JSON.stringify(pathToFileURL(plugin.module).href+'?v='+digest)+';\n',{mode:0o600});composed.push({id:plugin.id,name,config:plugin.config||{}})}
for(const [name,value] of [['agent.cordis.yml',composed],['preset.yml',{name:profile.name,description:profile.description}]]){const target=join(directory,name);try{copyFileSync(target,target+'.before-workspace-'+Date.now())}catch(e){if(e.code!=='ENOENT')throw e}writeFileSync(target,JSON.stringify(value,null,2)+'\n',{mode:0o600})}
const registered=profiles(),dir=profileDirectory();mkdirSync(dir,{recursive:true,mode:0o700});writeFileSync(join(dir,profile.id+'.json'),JSON.stringify(profile,null,2)+'\n',{mode:0o600});writeFileSync(join(dir,'index.json'),JSON.stringify([...new Set([...registered.map(p=>p.id),profile.id])])+'\n',{mode:0o600})
console.log('Registered Augmentor workspace profile '+profile.id+'. Existing conversation IDs are preserved.')
