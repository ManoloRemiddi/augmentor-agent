// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFile,writeFile,rename} from 'node:fs/promises';import {resolve,join} from 'node:path';import {pathToFileURL} from 'node:url';import {createHash} from 'node:crypto';
import {bundleFixture} from './dsh-bundle.mjs';
import {planFixture} from './plans.mjs';import {authoredRichDshProject} from './dsh-rich-project.mjs';
const {importDshProject}=await import(pathToFileURL(resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.','dist/runtime/src/dsh-project-import.js')));
export async function richRuntimeFixture(t,{vision=true,projectFactory=authoredRichDshProject,bundle=false,fixtureOptions={}}={}){
 const f=await planFixture(t,{policy:'read-only',...fixtureOptions});await f.stop();await rename(f.state,f.state+'-before-rich-import');
 const modelFile=join(f.config,'agent/models.json'),models=JSON.parse(await readFile(modelFile));models.providers.fixture.models[0].input=vision?['text','image']:['text'];await writeFile(modelFile,JSON.stringify(models),{mode:0o600});
 const rich=await projectFactory(f.workspace);let raw=JSON.stringify(rich.value),source=join(f.root,'authored-rich-project.json');
 if(bundle){const exported=await bundleFixture(t,()=>rich);raw=exported.raw.toString();source=exported.source;}else await writeFile(source,raw,{mode:0o600});
 const receipt=await importDshProject(source,f.state,{sourceSha256:createHash('sha256').update(raw).digest('hex'),selection:f.selection});await f.start();return {...f,...rich,source,raw,receipt,sid:receipt.sessionId??receipt.sessions[0].sessionId};
}
