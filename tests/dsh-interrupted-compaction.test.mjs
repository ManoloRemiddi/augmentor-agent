// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import {mkdtemp,mkdir,readFile,writeFile,rm,readdir} from 'node:fs/promises';import {existsSync} from 'node:fs';import {join,resolve} from 'node:path';import {tmpdir} from 'node:os';import {pathToFileURL} from 'node:url';import {createHash} from 'node:crypto';
const root=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.'),{importDshProject,dshHistoryCut}=await import(pathToFileURL(join(root,'dist/runtime/src/dsh-project-import.js'))),{dshHistorySurface}=await import(pathToFileURL(join(root,'dist/runtime/src/dsh-history-surface.js')));
const sha=raw=>createHash('sha256').update(raw).digest('hex');
import {interruptedSeedProject} from './fixtures/dsh-interrupted-compaction-project.mjs';

async function fixture(t){const base=await mkdtemp(join(tmpdir(),'augmentor-interrupted-compaction-'));t.after(()=>rm(base,{recursive:true,force:true}));const cwd=join(base,'project');await mkdir(cwd);const value=interruptedSeedProject(cwd),source=join(base,'source.json'),state=join(base,'state');return {base,cwd,value,source,state,async save(){const raw=JSON.stringify(value);await writeFile(source,raw,{mode:0o600});return {sourceSha256:sha(raw),selection:{provider:'fixture',model:'chosen'}};}};}
test('interrupted turn immediately followed by seed retains an unknown historical compaction, never a fabricated completion',async t=>{
 const f=await fixture(t),options=await f.save(),events=f.value.sessions[0].records.map(r=>r.event),surface=dshHistorySurface(events,true);assert.deepEqual(surface.endedSeedCompactions,[2]);assert.deepEqual(surface.nodes,[1]);const receipt=await importDshProject(f.source,f.state,options),id=receipt.sessionId,display=(await readFile(join(f.state,'sessions',id+'.events.jsonl'),'utf8')).trim().split('\n').map(JSON.parse);assert(!display.some(e=>e.type==='compaction/end'));assert(display.some(e=>e.type==='dsh/history'&&e.data.originalType==='compaction/start'));assert.equal(display.find(e=>e.type==='turn/end').data.reason.kind,'interrupted');assert.deepEqual(receipt.sourceLineage.seedCuts,[]);assert.deepEqual(receipt.historicalInterruptedCompactions,[2]);
 const completed=dshHistoryCut(f.value.sessions[0],f.value,options.sourceSha256,f.state,4);assert(JSON.stringify(completed.manager.buildSessionContext().messages).includes('AUTHORED-PRE-INTERRUPTION-HISTORY'));assert.throws(()=>dshHistoryCut(f.value.sessions[0],f.value,options.sourceSha256,f.state,3),/unresolved compaction/);assert.equal(await readFile(f.source,'utf8'),JSON.stringify(f.value));
});
for(const [name,change] of [
 ['completed instead of interrupted',f=>{f.value.sessions[0].records[3].event.data.reason.kind='completed';}],
 ['no adjacent seed',f=>{f.value.sessions[0].records.pop();f.value.sessions[0].opening.cursor--;}],
 ['intervening metadata',f=>{const rows=f.value.sessions[0].records;rows.splice(4,0,{type:'event',event:{seq:4,time:1700000000004,type:'session/title',data:{title:'intervening'}}});rows.forEach((r,i)=>r.event.seq=i);f.value.sessions[0].opening.cursor++;}],
 ['malformed seed',f=>{f.value.sessions[0].records[4].event.data.inherited=false;}],
 ['untyped legacy source',f=>{delete f.value.sessions[0].opening.header.version;}],
 ['different ending turn',f=>{f.value.sessions[0].records[3].event.data.turn=2;}],
])test('interrupted-compaction exception refuses '+name+' without any target',async t=>{const f=await fixture(t);change(f);const options=await f.save();await assert.rejects(()=>importDshProject(f.source,f.state,options));assert(!existsSync(f.state));assert(!(await readdir(f.base)).some(name=>name.startsWith('.dsh-import-')));});
