// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored persistence fixtures; no private source/profile/history.
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,readdir,rm} from 'node:fs/promises';
import {join} from 'node:path';import {tmpdir} from 'node:os';import {createHash} from 'node:crypto';
import {unzipSync,strFromU8} from 'fflate';import sharp from 'sharp';
import {captureSessionArchive} from '../dist/runtime/src/session-archive.js';
import {PiAttachments} from '../dist/runtime/src/attachments.js';
import {ObservationStore,OBSERVATION_PROTOCOL} from '../dist/observation/src/store.js';
const sha=x=>createHash('sha256').update(x).digest('hex'),json=rows=>rows.map(row=>JSON.stringify(row)+'\n').join('');
async function fixture(t){
 const root=await mkdtemp(join(tmpdir(),'augmentor-session-archive-test-'));t.after(()=>rm(root,{recursive:true,force:true}));const state=join(root,'state'),sessions=join(state,'sessions'),spool=join(root,'spool');await mkdir(sessions,{recursive:true,mode:0o700});await mkdir(spool,{mode:0o700});
 const metas=new Map(),jobs=new Map(),attachments=new PiAttachments(state),observations=new ObservationStore(join(state,'observations'),()=>({capturePayloads:true,maxBytes:100*1024*1024,days:30}));
 const owner={dirs:{state,sessions},attachments,observations,getMeta(id){const m=metas.get(id);if(!m)throw Error('Conversation not found');return m;},jobs:{list(id){return [...jobs.values()].filter(job=>job.owner===id).map(job=>({...job,kind:job.spec.kind}));},lookup(id,key){const job=jobs.get(key);if(job?.owner!==id)throw Error('Job not found in this conversation');return job;}}};
 const create=async(id,patch={})=>{const file=join(sessions,id+'.pi.jsonl'),meta={id,file,title:'Authored '+id,cwd:join(root,'work'),selection:{provider:'fixture',model:'fixture'},policy:'read-only',saved:false,running:false,updatedAt:1,...patch};metas.set(id,meta);await writeFile(file,json([{type:'session',version:3,id:'native-'+id},{type:'message',id:'message-'+id,message:{role:'user',content:[{type:'text',text:'Exact café 🌊'}]}}]));return meta;};
 const display=(id,rows)=>writeFile(join(sessions,id+'.events.jsonl'),json(rows));
 const capture=(id='parent',signal=new AbortController().signal)=>captureSessionArchive(owner,id,signal,spool);
 const consume=async snapshot=>{const zip=unzipSync(new Uint8Array(await new Response(snapshot.stream()).arrayBuffer()));await snapshot.settled;return {zip,manifest:JSON.parse(strFromU8(zip['manifest.json']))};};
 await create('parent');return {root,state,sessions,spool,owner,metas,jobs,create,display,capture,consume};
}
test('archive retains exact originals and diagnostics, labels metadata and excludes unrelated files and unsubmitted uploads',async t=>{
 const f=await fixture(t),upload=await f.owner.attachments.upload('parent',Buffer.from('Declared binary\0\xff','latin1'),'declared.bin'),unused=await f.owner.attachments.upload('parent',Buffer.from('UNSENT_UPLOAD'),'unused.txt');
 await f.display('parent',[{seq:1,type:'user/message',data:{submittedContent:[{type:'file',attachment:upload.file}]}},{seq:2,type:'runtime/notice',data:{message:'literal /workspace/example is not an attachment'}}]);
 const event=f.owner.observations.append('parent','request/fixture',{count:1},{},{exact:'authored diagnostic 🌊'});await f.create('unrelated');await writeFile(join(f.state,'credentials.json'),'NEVER_INCLUDE');await writeFile(join(f.sessions,'parent.queue.json'),'UNSENT_QUEUE');
 const native=await readFile(f.metas.get('parent').file),display=await readFile(join(f.sessions,'parent.events.jsonl')),snapshot=await f.capture(),{zip,manifest}=await f.consume(snapshot);
 assert.deepEqual(Buffer.from(zip['session/pi.jsonl']),native);assert.deepEqual(Buffer.from(zip['session/display.jsonl']),display);assert.deepEqual(Buffer.from(zip['session/observations/'+event.id+'.payload.json']),await readFile(join(f.owner.observations.root,'parent',event.id+'.payload.json')));
 assert.deepEqual(Buffer.from(zip['files/'+upload.file.attachmentId.slice(7)+'/declared.bin']),Buffer.from('Declared binary\0\xff','latin1'));assert(!Object.keys(zip).some(path=>path.includes(unused.file.attachmentId.slice(7))||path.includes('unrelated')||path.includes('queue')||path.includes('credentials')));
 const meta=JSON.parse(strFromU8(zip['session/metadata.json']));assert.equal(meta.file,undefined);assert.equal(meta.id,'parent');assert.equal(manifest.files.find(x=>x.path==='session/metadata.json').origin,'serialized-runtime-metadata');assert.equal(manifest.information.sessions[0].nativeSessionId,'native-parent');assert.equal(manifest.information.sessions[0].nativeFormatVersion,3);assert.equal(manifest.information.attachmentObjects,1);for(const row of manifest.files){assert.equal(row.sha256,sha(zip[row.path]));assert.equal(row.bytes,zip[row.path].byteLength);}assert.deepEqual(await readdir(f.spool),[]);assert.deepEqual(await readFile(f.metas.get('parent').file),native);
});
test('normalized image and explicitly named original both retain exact stored bytes with no alias scan',async t=>{
 const f=await fixture(t),raw=await sharp({create:{width:5,height:3,channels:3,background:'#f80'}}).png().toBuffer(),upload=await f.owner.attachments.uploadImage('parent',raw,'photo.png','image/png');await f.display('parent',[{seq:1,type:'user/message',data:{content:[{type:'image',attachment:upload.attachment},{type:'image',attachment:upload.attachment}]}}]);const {zip,manifest}=await f.consume(await f.capture());assert.equal(manifest.information.attachmentObjects,2);const ref=upload.attachment;assert.deepEqual(Buffer.from(zip['files/'+ref.originalAttachmentId.slice(7)+'/photo.png']),raw);assert.equal(sha(zip['media/'+ref.attachmentId.slice(7)+'.png']),ref.attachmentId.slice(7));
});
test('only verified owned delegate/desktop descendants enter closure and ordinary forks stay outside',async t=>{
 const f=await fixture(t);await f.create('child',{delegation:{parentId:'parent',jobId:'job-child',resources:{secretConfiguration:'NO_CONFIGURATION'},allowedTools:[]}});await f.create('grandchild',{delegation:{parentId:'child',jobId:'job-grand'}});await f.create('ordinary-fork',{fork:{sessionId:'parent',messageSeq:1,mode:'reply'}});
 for(const job of [{id:'job-child',owner:'parent',childId:'child',spec:{kind:'delegate',task:'Authored child'},state:'completed'},{id:'job-grand',owner:'child',childId:'grandchild',spec:{kind:'desktop',task:'Authored desktop'},state:'failed'},{id:'shell',owner:'parent',spec:{kind:'shell',task:'Authored command'},state:'completed'},{id:'pending',owner:'parent',spec:{kind:'delegate'},state:'starting'}])f.jobs.set(job.id,job);
 const {zip,manifest}=await f.consume(await f.capture());assert.deepEqual(manifest.information.sessions.map(x=>x.sessionId),['parent','child','grandchild']);assert(zip['subagents/grandchild/pi.jsonl']);assert(!Object.keys(zip).some(x=>x.includes('ordinary-fork')));assert(!strFromU8(zip['subagents/child/metadata.json']).includes('secretConfiguration'));assert.deepEqual(manifest.information.pendingOrAbsentChildIdentities,[{parentId:'parent',jobId:'pending',state:'starting'}]);assert.equal(JSON.parse(strFromU8(zip['session/jobs/shell.json'])).spec.kind,'shell');await assert.rejects(f.capture('child'),/owning parent/);
});
test('absent retained bodies and journals are explicit gaps, incomplete tails remain original bytes',async t=>{
 const f=await fixture(t),event=f.owner.observations.append('parent','retained',{},{},{body:'soon expired'});await rm(join(f.owner.observations.root,'parent',event.id+'.payload.json'));const path=f.metas.get('parent').file,before=await readFile(path);await writeFile(path,Buffer.concat([before,Buffer.from('{"partial":')]));const {zip,manifest}=await f.consume(await f.capture());assert.deepEqual(Buffer.from(zip['session/pi.jsonl']),await readFile(path));assert.equal(manifest.files.find(x=>x.path==='session/pi.jsonl').jsonl.incompleteTailBytes,11);assert.deepEqual(manifest.unavailable.map(x=>x.path).sort(),['session/display.jsonl','session/observations/'+event.id+'.payload.json'].sort());assert.equal(manifest.information.sessions[0].observationRecords,1);
});
test('missing or corrupt declared uploads, malformed journals and redirected native originals refuse',async t=>{
 for(const mode of ['missing-upload','corrupt-upload','foreign-upload','malformed-display','malformed-native','malformed-observation','outside-native']){
  const f=await fixture(t);
  if(mode.endsWith('upload')){const upload=await f.owner.attachments.upload(mode==='foreign-upload'?'foreign':'parent',Buffer.from('Exact object'),'object.txt');await f.display('parent',[{seq:1,type:'user/message',data:{content:[{type:'file',attachment:upload.file}]}}]);const source=f.owner.attachments.archiveSources(mode==='foreign-upload'?'foreign':'parent',{type:'file',attachment:upload.file})[0];if(mode==='missing-upload')await rm(source.file);if(mode==='corrupt-upload'){await import('node:fs/promises').then(fs=>fs.chmod(source.file,0o600));await writeFile(source.file,'Wrong object');}}
  if(mode==='malformed-display')await f.display('parent',[{seq:1,type:'user/message',data:{}},{seq:1,type:'user/message',data:{}}]);
  if(mode==='malformed-native')await writeFile(f.metas.get('parent').file,'{"type":"not-a-session"}\n');
  if(mode==='malformed-observation'){const dir=join(f.owner.observations.root,'parent');await mkdir(dir,{recursive:true});await writeFile(join(dir,'events.jsonl'),json([{protocol:OBSERVATION_PROTOCOL,sessionId:'other',id:'event',seq:1,kind:'request'}]));}
  if(mode==='outside-native'){const path=join(f.root,'outside');await writeFile(path,'Outside');f.metas.get('parent').file=path;}
  await assert.rejects(f.capture(),undefined,mode);assert.deepEqual(await readdir(f.spool),[],mode);
 }
});
test('unverified catalogue, mismatched links and identity changes during finalization cannot produce a partial archive',async t=>{
 for(const mode of ['catalogue','owner','child','cycle','changed-native','changed-parent']){
  const f=await fixture(t);await f.create('child',{delegation:{parentId:'parent',jobId:'job'}});f.jobs.set('job',{id:'job',owner:'parent',childId:'child',state:'completed',spec:{kind:'delegate'}});
  if(mode==='catalogue')f.owner.jobs.problem='Invalid receipts';if(mode==='owner')f.owner.jobs.list=()=>[{id:'job',owner:'foreign',childId:'child',kind:'delegate'}];if(mode==='child')f.metas.get('child').delegation.jobId='wrong';if(mode==='cycle'){f.jobs.set('again',{id:'again',owner:'child',childId:'parent',state:'completed',spec:{kind:'delegate'}});}
  if(mode.startsWith('changed')){const original=f.owner.getMeta;let calls=0;f.owner.getMeta=id=>{const m=original(id);if(id==='parent'&&++calls===2){if(mode==='changed-native')m.file=join(f.sessions,'changed');else f.jobs.get('job').childId='other';}return m;};}
  await assert.rejects(f.capture(),undefined,mode);assert.deepEqual(await readdir(f.spool),[],mode);
 }
});
test('pre-native conversations are truthful and cancellation prepares no archive',async t=>{
 const f=await fixture(t);f.metas.get('parent').file=undefined;const {zip,manifest}=await f.consume(await f.capture());assert.equal(zip['session/pi.jsonl'],undefined);assert.equal(manifest.information.sessions[0].nativeState,'not-created-at-selection');const abort=new AbortController();abort.abort(Error('Authored preparation cancelled'));await assert.rejects(f.capture('parent',abort.signal),/cancelled/);assert.deepEqual(await readdir(f.spool),[]);
});
