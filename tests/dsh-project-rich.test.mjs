// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,mkdir,readFile,writeFile,rm,readdir,chmod} from 'node:fs/promises';import {existsSync} from 'node:fs';import {tmpdir} from 'node:os';import {resolve,join} from 'node:path';import {pathToFileURL} from 'node:url';import {createHash} from 'node:crypto';
import {authoredRichDshProject} from './fixtures/dsh-rich-project.mjs';
const root=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');
const {importDshProject}=await import(pathToFileURL(join(root,'dist/runtime/src/dsh-project-import.js')));
const {PiAttachments}=await import(pathToFileURL(join(root,'dist/runtime/src/attachments.js')));
const {PiDshHistoryMedia}=await import(pathToFileURL(join(root,'dist/runtime/src/dsh-history-media.js')));
const sdk=JSON.parse(await readFile(join(root,'node_modules/@earendil-works/pi-coding-agent/package.json')));
const {SessionManager}=await import(pathToFileURL(join(root,'node_modules/@earendil-works/pi-coding-agent',sdk.exports['.'].import)));
const sha=b=>createHash('sha256').update(b).digest('hex');
async function fixture(t){
 const base=await mkdtemp(join(tmpdir(),'augmentor-rich-import-'));t.after(()=>rm(base,{recursive:true,force:true}));const cwd=join(base,'project');await mkdir(cwd);
 const rich=await authoredRichDshProject(cwd),source=join(base,'source.json'),state=join(base,'state');
 const save=async()=>{const data=JSON.stringify(rich.value);await writeFile(source,data,{mode:0o600});return {sourceSha256:sha(data),selection:{provider:'fixture',model:'fixture-vision'}};};
 return {base,cwd,source,state,...rich,save};
}
async function native(f,receipt){const row=receipt.sessions[0],meta=JSON.parse(await readFile(join(f.state,'sessions',row.sessionId+'.meta.json')));return {sid:row.sessionId,file:meta.file,messages:SessionManager.open(meta.file).buildSessionContext().messages};}
test('reasoning and exact stored images cold-open without provider replay or inline duplication',async t=>{
 const f=await fixture(t),receipt=await importDshProject(f.source,f.state,await f.save()),n=await native(f,receipt),text=JSON.stringify(n.messages),store=new PiAttachments(f.state);
 assert(text.includes('AUTHORED-REASONING'));assert(!text.includes('OPAQUE-REPLAY'));assert(!text.includes(f.bytes.toString('base64')));assert(text.includes('augmentor-dsh-media/1'));
 assert.deepEqual(Buffer.from((await store.image(n.sid,f.attachment)).data),f.bytes);await assert.rejects(()=>store.image(receipt.sessions[1].sessionId,f.attachment),/belong/);
 const display=(await readFile(join(f.state,'sessions',n.sid+'.events.jsonl'),'utf8')).trim().split('\n').map(JSON.parse),user=display.find(e=>e.type==='user/message');
 assert.equal(user.data.content[1].offloaded,undefined);assert.equal(user.data.content[2].offloaded,true);assert(JSON.stringify(display).includes('AUTHORED-REASONING'));
 assert.deepEqual(await readFile(join(f.state,receipt.rawArchive)),await readFile(f.source));assert((await readFile(join(f.state,receipt.rawArchive),'utf8')).includes('OPAQUE-REPLAY'));
 assert.equal(JSON.parse(await readFile(join(store.root,n.sid+'.json'))).length,1,'repeated identical references share one receipt');
 const session={model:{input:['text','image']},agent:{transformContext:async m=>m}},binding=new PiDshHistoryMedia(store,n.sid);binding.install(session);
 const resolved=await session.agent.transformContext(n.messages,new AbortController().signal),inline=resolved.flatMap(m=>Array.isArray(m.content)?m.content:[]).filter(p=>p.type==='image');
 assert.equal(inline.length,2);assert(inline.every(p=>p.data===f.bytes.toString('base64')));assert(JSON.stringify(resolved).includes('explicitly offloaded'));assert.equal(JSON.stringify(n.messages),text,'request resolution never changes the canonical native history');binding.dispose();
});
for(const [name,mutate,pattern] of [
 ['missing blob',f=>{f.value.attachments=[];},/unavailable/],
 ['changed checksum',f=>{f.value.attachments[0].data=Buffer.alloc(f.bytes.length).toString('base64');},/checksum/],
 ['noncanonical base64',f=>{f.value.attachments[0].data+='\n';},/encoding/],
 ['duplicate blob',f=>{f.value.attachments.push({...f.value.attachments[0]});},/bundle/],
 ['wrong dimensions',f=>{f.value.sessions[0].records[1].event.data.content[1].attachment.width=7;},/metadata/],
 ['unsupported original',f=>{f.value.sessions[0].records[1].event.data.content[1].attachment.originalAttachmentId=f.attachment.attachmentId;},/metadata/],
 ['offload missing source',f=>{f.value.sessions[0].records[6].event.data.targets[0].seq=99;},/offload/],
 ['offload duplicate index',f=>{f.value.sessions[0].records[6].event.data.targets[0].imageIndexes=[1,1];},/offload/],
 ['opaque reasoning',f=>{f.value.sessions[0].records[2].event.data.message.content[0]={type:'reasoning',signature:'not plaintext'};},/reasoning/],
 ['malformed decoded image',f=>{const bytes=Buffer.from('Not actually an image'),id='sha256:'+sha(bytes);for(const row of f.value.sessions[0].records){const d=row.event.data,m=row.event.type==='user/message'?d:d.message;for(const p of m?.content??[])if(p.type==='image')p.attachment={...p.attachment,attachmentId:id,bytes:bytes.length};}f.value.attachments=[{attachmentId:id,bytes:bytes.length,data:bytes.toString('base64')}];},/malformed|image data/i],
])test('rich import rejects '+name+' and removes every partial conversation',async t=>{
 const f=await fixture(t);mutate(f);await assert.rejects(()=>f.save().then(options=>importDshProject(f.source,f.state,options)),pattern);assert(!existsSync(f.state));assert(!(await readdir(f.base)).some(name=>name.startsWith('.dsh-import-')));
});
test('media transform fails closed on text-only route, foreign authority, Stop and changed stored bytes',async t=>{
 const f=await fixture(t),receipt=await importDshProject(f.source,f.state,await f.save()),n=await native(f,receipt),store=new PiAttachments(f.state),session={model:{input:['text']},agent:{}};
 const binding=new PiDshHistoryMedia(store,n.sid);binding.install(session);await assert.rejects(()=>session.agent.transformContext(n.messages),/image input/);session.model.input.push('image');
 const abort=new AbortController();abort.abort(Error('Authored Stop'));await assert.rejects(()=>session.agent.transformContext(n.messages,abort.signal),/Authored Stop/);binding.dispose();
 const foreign=new PiDshHistoryMedia(store,receipt.sessions[1].sessionId);foreign.install(session);await assert.rejects(()=>session.agent.transformContext(n.messages),/belong/);foreign.dispose();
 const path=store.historicalImagePath(n.sid,f.attachment);await chmod(path,0o600);await writeFile(path,Buffer.alloc(f.bytes.length));binding.install(session);await assert.rejects(()=>session.agent.transformContext(n.messages),/corrupt|integrity/i);binding.dispose();assert.equal(session.agent.transformContext,undefined);
});
test('an all-offloaded history works with a text-only model and repeated media stays bounded',async t=>{
 const f=await fixture(t),receipt=await importDshProject(f.source,f.state,await f.save()),n=await native(f,receipt),store=new PiAttachments(f.state),session={model:{input:['text']},agent:{}};
 const messages=structuredClone(n.messages);for(const m of messages)for(const p of m.details?.images??[])p.offloaded=true;
 const binding=new PiDshHistoryMedia(store,n.sid);binding.install(session);const resolved=await session.agent.transformContext(messages);assert(!resolved.some(m=>Array.isArray(m.content)&&m.content.some(p=>p.type==='image')));assert(JSON.stringify(resolved).includes('Read-only stored image'));
 session.model.input.push('image');const m=n.messages.find(m=>m.details?.images);await assert.rejects(()=>session.agent.transformContext(Array(65).fill({...m,details:{...m.details,images:[m.details.images[0]]}})),/64 images/);binding.dispose();
});
