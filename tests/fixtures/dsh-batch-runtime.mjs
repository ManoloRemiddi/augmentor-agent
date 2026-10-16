// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {mkdir,writeFile,readFile} from 'node:fs/promises';import {join,resolve} from 'node:path';import {pathToFileURL} from 'node:url';import {createHash} from 'node:crypto';
import {planFixture} from './plans.mjs';import {authoredDshProject} from './dsh-project.mjs';
const {importDshProjects}=await import(pathToFileURL(resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.','dist/runtime/src/dsh-project-batch.js')));
export async function batchRuntimeFixture(t){
 const f=await planFixture(t,{policy:'read-only'}),existing='authored-existing';await f.call('session.create',{sessionId:existing,cwd:f.workspace,selection:f.selection});await f.prompt(existing,{kind:'read',tag:'EXISTING-NATIVE-WORK'});
 const inputs=[];
 for(const tag of ['A','B']){
  const cwd=join(f.workspace,'project-'+tag);await mkdir(cwd);const value=authoredDshProject(cwd),ids=new Map(value.workspace.sessionIds.map(id=>[id,tag+'-'+id]));value.workspace.title='Authored project '+tag;value.workspace.sessionIds=value.workspace.sessionIds.map(id=>ids.get(id));value.pinnedSessionIds=value.pinnedSessionIds.map(id=>ids.get(id));value.archivedSessionIds=value.archivedSessionIds.map(id=>ids.get(id));
  for(const s of value.sessions){s.opening.header.id=ids.get(s.opening.header.id);s.opening.projections.values.title=tag+' '+s.opening.projections.values.title;for(const {event:e} of s.records){const m=e.type==='user/message'?e.data:e.data.message;for(const part of m?.content??[])if(part.type==='text')part.text='PROJECT-'+tag+' '+part.text;}}
  const sourceFile=join(f.root,'source-'+tag+'.json'),raw=JSON.stringify(value);await writeFile(sourceFile,raw,{mode:0o600});inputs.push({sourceFile,options:{sourceSha256:createHash('sha256').update(raw).digest('hex'),selection:f.selection}});
 }
 return {...f,existing,inputs,importBatch:()=>importDshProjects(inputs,f.state),configBytes:()=>Promise.all(['settings.json','agent/models.json'].map(name=>readFile(join(f.config,name))))};
}
