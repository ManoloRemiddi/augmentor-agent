// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,mkdir,readFile,writeFile,readdir,rm} from 'node:fs/promises';import {existsSync} from 'node:fs';import {tmpdir} from 'node:os';import {join,resolve} from 'node:path';import {pathToFileURL} from 'node:url';import {createHash} from 'node:crypto';
import {authoredFramedSurfaceDshProject,checkpointFrame} from './fixtures/dsh-surface-project.mjs';
const root=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');
const {importDshProject}=await import(pathToFileURL(join(root,'dist/runtime/src/dsh-project-import.js')));
const {SessionManager}=await import('@earendil-works/pi-coding-agent');
async function fixture(t){const base=await mkdtemp(join(tmpdir(),'augmentor-checkpoint-frame-'));t.after(()=>rm(base,{recursive:true,force:true}));const cwd=join(base,'project');await mkdir(cwd);const f=await authoredFramedSurfaceDshProject(cwd);return {...f,base,source:join(base,'source.json'),state:join(base,'state')};}
async function save(f){const raw=JSON.stringify(f.value);await writeFile(f.source,raw,{mode:0o600});return {sourceSha256:createHash('sha256').update(raw).digest('hex'),selection:{provider:'fixture',model:'fixture'}};}
test('standard public DSH framed checkpoints retain exact summary blocks, nested surface order and immutable original archive',async t=>{
 const f=await fixture(t);for(const checkpoint of [f.first,f.second]){
  const extra={type:'text',text:'AUTHORED ADDITIONAL SUMMARY BLOCK '+checkpoint.summarySeq};f.session.records[checkpoint.summarySeq].event.data.summary.push(extra);f.session.records[checkpoint.checkpoint].event.data.content.splice(-1,0,structuredClone(extra));
 }
 const options=await save(f),before=await readFile(f.source),receipt=await importDshProject(f.source,f.state,options),row=receipt.sessions[0];
 assert.deepEqual(row.effectiveSourceSeqs,f.expectedSurface);assert.equal(row.sourceReplacements,3);
 const meta=JSON.parse(await readFile(join(f.state,'sessions',row.sessionId+'.meta.json'))),manager=SessionManager.open(meta.file),context=JSON.stringify(manager.buildSessionContext().messages);
 assert(context.includes('FINAL-SOURCE-CHECKPOINT'));assert(context.includes('CURRENT-SOURCE-QUESTION'));assert(!context.includes('SUPERSEDED-FIRST-CHECKPOINT'));assert(!context.includes('SUPERSEDED-SECOND-QUESTION'));
 assert.equal(context.split('<compacted-summary>').length-1,1);assert.equal(context.split('</compacted-summary>').length-1,1);
 assert(context.includes('AUTHORED ADDITIONAL SUMMARY BLOCK '+f.second.summarySeq));assert(!context.includes('AUTHORED ADDITIONAL SUMMARY BLOCK '+f.first.summarySeq));
 assert.deepEqual(await readFile(f.source),before);assert.deepEqual(await readFile(join(f.state,receipt.rawArchive)),before);
 const display=(await readFile(join(f.state,'sessions',row.sessionId+'.events.jsonl'),'utf8')).trim().split('\n').map(JSON.parse);
 const summaries=display.filter(e=>e.type==='compaction/summary');assert.equal(summaries.length,2);assert(summaries.every(e=>!JSON.stringify(e.data.summary).includes('<compacted-summary>')),'raw summaries are not rewritten into checkpoint framing');
});
for(const [name,mutate,pattern] of [
 ['changed opening instructions',c=>c[0].text+=' Extra instructions.',/exact replacement/],
 ['changed closing marker',c=>c.at(-1).text+='\n',/exact replacement/],
 ['same summary only as a substring',c=>c.splice(0,c.length,{type:'text',text:checkpointFrame.open+c[1].text+checkpointFrame.close}),/exact replacement/],
 ['injected middle block',c=>c.splice(1,0,{type:'text',text:'UNRELATED INJECTED CONTENT'}),/exact replacement/],
 ['changed middle summary',c=>c[1].text+=' Changed.',/exact replacement/],
 ['wrapper metadata not in the source framing',c=>c[0].unexpected='AUTHORED',/exact replacement/],
 ['reordered frame',c=>c.reverse(),/exact replacement/],
])test('framed import refuses '+name+' before destination publication',async t=>{
 const f=await fixture(t);mutate(f.session.records[f.first.checkpoint].event.data.content);
 const options=await save(f),before=await readFile(f.source);await assert.rejects(()=>importDshProject(f.source,f.state,options),pattern);
 assert(!existsSync(f.state));assert(!(await readdir(f.base)).some(n=>n.startsWith('.dsh-import-')));assert.deepEqual(await readFile(f.source),before);
});
