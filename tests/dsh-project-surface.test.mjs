// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,mkdir,readFile,writeFile,readdir,rm} from 'node:fs/promises';import {existsSync} from 'node:fs';import {tmpdir} from 'node:os';import {join,resolve} from 'node:path';import {pathToFileURL} from 'node:url';import {createHash} from 'node:crypto';
import {authoredSurfaceDshProject} from './fixtures/dsh-surface-project.mjs';
const root=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.'),sdk=JSON.parse(await readFile(join(root,'node_modules/@earendil-works/pi-coding-agent/package.json')));
const {SessionManager}=await import(pathToFileURL(join(root,'node_modules/@earendil-works/pi-coding-agent',sdk.exports['.'].import)));
const {importDshProject}=await import(pathToFileURL(join(root,'dist/runtime/src/dsh-project-import.js')));
const {dshHistorySurface}=await import(pathToFileURL(join(root,'dist/runtime/src/dsh-history-surface.js')));
const {projectChat}=await import(pathToFileURL(join(root,'apps/harness/chat-projection.js')));
async function fixture(t){const base=await mkdtemp(join(tmpdir(),'augmentor-source-surface-'));t.after(()=>rm(base,{recursive:true,force:true}));const cwd=join(base,'project');await mkdir(cwd);const rich=await authoredSurfaceDshProject(cwd),source=join(base,'source.json'),state=join(base,'state');const save=async()=>{const raw=JSON.stringify(rich.value);await writeFile(source,raw,{mode:0o600});return {sourceSha256:createHash('sha256').update(raw).digest('hex'),selection:{provider:'fixture',model:'fixture'}};};return {base,source,state,...rich,save};}
const events=f=>f.session.records.map(r=>r.event);
test('nested compactions use surface order and preserve original GUI transcript, exact archive and fork provenance',async t=>{
 const f=await fixture(t),receipt=await importDshProject(f.source,f.state,await f.save()),row=receipt.sessions[0],meta=JSON.parse(await readFile(join(f.state,'sessions',row.sessionId+'.meta.json'))),manager=SessionManager.open(meta.file),context=JSON.stringify(manager.buildSessionContext().messages);
 assert.deepEqual(row.effectiveSourceSeqs,f.expectedSurface);assert.equal(row.sourceReplacements,3);assert.equal(row.sourceLineage.parentSession,'authored-ancestor');assert.deepEqual(row.sourceLineage.seedCuts,[f.seedCut]);
 assert(context.includes('FINAL-SOURCE-CHECKPOINT'));assert(context.includes('CURRENT-SOURCE-QUESTION'));assert(context.includes('CURRENT-SOURCE-ANSWER'));for(const old of ['SUPERSEDED','NATIVE-HISTORY-ALPHA','PRUNED-HISTORICAL','augmentor-dsh-media/1'])assert(!context.includes(old),old+' is historical display/archive, not current context');
 assert.deepEqual(manager.getEntries().find(e=>e.type==='custom'&&e.customType==='augmentor.dsh-surface.v1').data.nodes,f.expectedSurface);
 const display=(await readFile(join(f.state,'sessions',row.sessionId+'.events.jsonl'),'utf8')).trim().split('\n').map(JSON.parse),chat=projectChat(display);
 assert.equal(chat.filter(x=>x.kind==='compaction').length,2);assert.equal(chat.filter(x=>x.kind==='user').length,3,'replacement checkpoints are not extra human prompts');assert.equal(display.filter(x=>x.type==='tool/result').length,1,'pruning never appends a duplicate tool settlement');assert(JSON.stringify(display).includes('SUPERSEDED-SECOND-QUESTION'));assert(JSON.stringify(display).includes('PRUNED-HISTORICAL-TOOL-EXCERPT'));
 assert.equal(display.find(e=>e.seq===f.second.checkpoint+1).data.marker.summaryEventSeq,f.second.summarySeq+1);assert.deepEqual(await readFile(join(f.state,receipt.rawArchive)),await readFile(f.source));
 const fold=dshHistorySurface(events(f),true);assert(fold.replacements[2].start>fold.replacements[2].end,'position ranges can have decreasing numeric seqs');assert.deepEqual(fold.nodes,f.expectedSurface);
});
for(const [name,mutate,pattern] of [
 ['missing surface marker',f=>{delete events(f)[1].surfaceOp;},/surface operation/],
 ['missing replacement source',f=>{events(f)[f.first.checkpoint].sourceEventSeqs=[1];},/citations/],
 ['stale replacement target',f=>{events(f)[f.second.checkpoint].surfaceOp.startSeq=1;},/boundaries/],
 ['reversed surface positions',f=>{const op=events(f)[f.second.checkpoint].surfaceOp;[op.startSeq,op.endSeq]=[op.endSeq,op.startSeq];},/boundaries/],
 ['false summary range',f=>{events(f)[f.first.summarySeq].data.shadowedSeqs=[1];},/pricing/],
 ['unpaired summary',f=>{events(f)[f.first.checkpoint].data.content[0].text='A different checkpoint';},/exact replacement/],
 ['wrong checkpoint owner',f=>{events(f)[f.first.checkpoint].data.source.compactionId='foreign';},/exact replacement/],
 ['changed tool identity',f=>{events(f)[f.pruneSeq].data.message.isError=true;},/only one result content/],
 ['future citation',f=>{events(f)[f.first.checkpoint].sourceEventSeqs.push(999);},/earlier events/],
 ['orphan checkpoint',f=>{events(f)[f.first.summarySeq].type='compaction/prune';},/adjacent summary/],
 ['dangling compaction',f=>{const seq=f.session.records.length;f.session.records.push({type:'event',event:{seq,time:1700000001000,type:'compaction/start',data:{compactionId:'authored-unfinished',turn:null}}});f.session.opening.cursor=seq;},/unresolved lifecycle/],
 ['unknown required event',f=>{events(f)[f.seedCut].type='plugin:unknown/context-rewrite';},/unknown required/],
 ['log surface marker',f=>{events(f)[f.seedCut].surfaceOp='append';},/log-only/],
 ['future source version',f=>{f.session.opening.header.version=5;},/format version/],
 ['invalid lineage marker',f=>{f.session.opening.header.isSeeded='true';},/lineage marker/],
 ['self lineage',f=>{f.session.opening.header.parentSession=f.session.opening.header.id;},/lineage/],
 ['missing inherited boundary',f=>{events(f)[f.seedCut].data={};},/inherited boundary/],
])test('source surface rejects '+name+' atomically',async t=>{
 const f=await fixture(t);mutate(f);await assert.rejects(()=>f.save().then(options=>importDshProject(f.source,f.state,options)),pattern);assert(!existsSync(f.state));assert(!(await readdir(f.base)).some(name=>name.startsWith('.dsh-import-')));
});
test('unknown explicitly ignorable source records stay archived without altering the effective messages',async t=>{
 const f=await fixture(t);events(f)[f.seedCut].type='plugin:unknown/diagnostic';events(f)[f.seedCut].ignorable=true;f.session.opening.header.isSeeded=false;
 const receipt=await importDshProject(f.source,f.state,await f.save());assert.deepEqual(receipt.sessions[0].effectiveSourceSeqs,f.expectedSurface);assert((await readFile(join(f.state,receipt.rawArchive),'utf8')).includes('plugin:unknown/diagnostic'));
});

test('a source lifecycle boundary ends an inherited incomplete compaction without starting new work',async t=>{
 const f=await fixture(t);events(f)[f.second.checkpoint+1].type='session/title';
 const receipt=await importDshProject(f.source,f.state,await f.save());assert.deepEqual(receipt.sessions[0].effectiveSourceSeqs,f.expectedSurface);
 const fold=dshHistorySurface(events(f),true);assert.deepEqual(fold.endedSeedCompactions,[f.second.summarySeq-1]);
});
test('a source user edit replaces current context at its original position without adding a new transcript turn',async t=>{
 const f=await fixture(t),target=f.expectedSurface[1],seq=f.session.records.length;
 f.session.records.push({type:'event',event:{seq,time:1700000001000,type:'user/message',data:{role:'user',source:{kind:'user'},content:[{type:'text',text:'EDITED-CURRENT-SOURCE-QUESTION'}]},surfaceOp:{op:'replace',startSeq:target,endSeq:target},sourceEventSeqs:[target]}});f.session.opening.cursor=seq;
 const receipt=await importDshProject(f.source,f.state,await f.save()),row=receipt.sessions[0],meta=JSON.parse(await readFile(join(f.state,'sessions',row.sessionId+'.meta.json'))),messages=SessionManager.open(meta.file).buildSessionContext().messages;
 assert.deepEqual(row.effectiveSourceSeqs,[f.expectedSurface[0],seq,f.expectedSurface[2]]);assert(messages.some(m=>m.role==='user'&&JSON.stringify(m.content).includes('EDITED-CURRENT')));assert(!messages.some(m=>m.role==='user'&&JSON.stringify(m.content).includes('CURRENT-SOURCE-QUESTION')&&!JSON.stringify(m.content).includes('EDITED-CURRENT')));
 const display=(await readFile(join(f.state,'sessions',row.sessionId+'.events.jsonl'),'utf8')).trim().split('\n').map(JSON.parse);assert.equal(projectChat(display).filter(m=>m.kind==='user').length,3);assert.equal(display.find(e=>e.seq===seq+1).type,'dsh/history');
});
