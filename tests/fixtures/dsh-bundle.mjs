// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {mkdtemp,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';import {join,resolve} from 'node:path';import {execFile} from 'node:child_process';import {promisify} from 'node:util';import {createHash} from 'node:crypto';
export const application=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.'),sha=bytes=>createHash('sha256').update(bytes).digest('hex');
export async function bundleFixture(t,build){
 const base=await mkdtemp(join(tmpdir(),'augmentor-dsh-bundle-'));t.after(()=>rm(base,{recursive:true,force:true}));const cwd=join(base,'project');await mkdir(cwd);
 const authored=await build(cwd),value=authored.value??authored,input=join(base,'authored.json'),bundle=join(base,'bundle');await writeFile(input,JSON.stringify(value),{mode:0o600});
 const {stdout}=await promisify(execFile)(process.env.AUGMENTOR_PYTHON??'python3',[resolve('tests/fixtures/export-dsh-bundle.py'),application,input,bundle],{timeout:45000,maxBuffer:65536});
 const source=join(bundle,'project.json'),raw=await readFile(source),manifest=JSON.parse(raw),options={sourceSha256:sha(raw),selection:{provider:'fixture',model:'chosen-model'}};
 return {base,cwd,value,authored,input,bundle,source,raw,manifest,options,state:join(base,'state'),exportReport:JSON.parse(stdout)};
}
