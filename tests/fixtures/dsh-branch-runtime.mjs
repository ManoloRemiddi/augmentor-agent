// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {writeFile,readFile,rename} from 'node:fs/promises';import {join,resolve} from 'node:path';import {pathToFileURL} from 'node:url';import {createHash} from 'node:crypto';
import {planFixture} from './plans.mjs';import {authoredSurfaceDshProject} from './dsh-surface-project.mjs';
const root=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');const {importDshProject}=await import(pathToFileURL(join(root,'dist/runtime/src/dsh-project-import.js')));
const sdk=join(root,'node_modules/@earendil-works/pi-coding-agent'),pkg=JSON.parse(await readFile(join(sdk,'package.json')));export const {SessionManager}=await import(pathToFileURL(resolve(sdk,pkg.exports['.'].import)));
export async function dshBranchFixture(t,make=authoredSurfaceDshProject){
 const f=await planFixture(t,{policy:'read-only'});await f.stop();await rename(f.state,f.state+'-before-import');const model=join(f.config,'agent/models.json'),settings=JSON.parse(await readFile(model));settings.providers.fixture.models[0].input=['text','image'];await writeFile(model,JSON.stringify(settings),{mode:0o600});
 const fixture=await make(f.workspace),value=fixture.value??fixture,bytes=JSON.stringify(value),file=join(f.root,'authored-branch-project.json');await writeFile(file,bytes,{mode:0o600});const receipt=await importDshProject(file,f.state,{sourceSha256:createHash('sha256').update(bytes).digest('hex'),selection:f.selection});await f.start();return {...f,...fixture,value,sourceBytes:bytes,receipt,sid:receipt.sessions[0].sessionId};
}
export async function preparedBranch(f,sid,seq,mode='reply'){const intent=await f.call('session.prepareBranch',{sessionId:sid,messageSeq:seq,mode});const branch=await f.call('session.branch',{...intent,prepared:true});return {intent,branch};}
