// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm,readFile,writeFile,stat,chmod} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import sharp from 'sharp';
import {PiAttachments} from '../dist/runtime/src/attachments.js';
import {PiPromptQueue} from '../dist/runtime/src/queue.js';
import {DshAttachments} from '../apps/harness/dsh-attachments.mjs';
import {DshPiController} from '../apps/harness/dsh-pi-controller.mjs';
import {HarnessServer} from '../dist/runtime/src/harness-server.js';
const pixel=()=>sharp({create:{width:3,height:2,channels:3,background:'#f00'}}).png().toBuffer();
async function fixture(t){const root=await mkdtemp(join(tmpdir(),'augmentor-attachments-'));t.after(()=>rm(root,{recursive:true,force:true}));return {root,store:new PiAttachments(root)};}
test('public DSH storage keeps exact file bytes and private conversation receipts across restart',async t=>{
 const {root,store}=await fixture(t),bytes=Buffer.from('Exact synthetic attachment.\n'),upload=await store.upload('a',bytes,'../../note.txt');assert.equal(upload.file.name,'note.txt');
 const content=[{type:'text',text:'Read this.'},{type:'file',...upload,attachment:upload.file}],admitted=await store.admit('a',content),cold=new PiAttachments(root),resolved=await cold.resolve('a',admitted.input,admitted.attachments);
 const path=JSON.parse(resolved.text.split('\n').at(-1)).path;assert.deepEqual(await readFile(path),bytes);assert.equal((await stat(join(store.root,'a.json'))).mode&0o777,0o600);
 await assert.rejects(()=>cold.admit('b',content),/receipt/);await assert.rejects(()=>cold.resolve('b','',admitted.attachments),/belong/);
 await chmod(path,0o600);await writeFile(path,'Corrupt');await assert.rejects(()=>cold.resolve('a','',admitted.attachments),/integrity|corrupt/i);
});
test('images are fully decoded, verified and passed inline; original bytes remain separate from normalization',async t=>{
 const {root,store}=await fixture(t),data=await pixel(),uploaded=await store.uploadImage('a',data,'red.png','image/png');
 const admitted=await store.admit('a',[{type:'image',...uploaded}]),cold=new PiAttachments(root),resolved=await cold.resolve('a','',admitted.attachments);
 assert.equal(resolved.images[0].mimeType,'image/png');assert.deepEqual(Buffer.from(resolved.images[0].data,'base64'),data);assert.equal(uploaded.attachment.width,3);assert.equal(uploaded.attachment.height,2);
 const receipts=JSON.parse(await readFile(join(store.root,'a.json'),'utf8'));assert(receipts[0].original);assert.equal(receipts[0].original.bytes,data.length);assert.equal(uploaded.attachment.originalAttachmentId,receipts[0].original.attachmentId);
 const q=new PiPromptQueue(join(root,'image-identity.json'),'a');q.enqueue('image','',true,undefined,admitted.attachments);assert.throws(()=>q.lookup('image','',[{type:'image',attachment:{...uploaded.attachment,originalAttachmentId:'sha256:'+'a'.repeat(64)}}]),/different input/);
 await assert.rejects(()=>store.uploadImage('a',Buffer.from('not a picture'),'bad.png','image/png'));
 await assert.rejects(()=>store.uploadImage('a',data,'false.jpg','image/jpeg'),/type/i);
 await assert.rejects(()=>store.admit('a',Array(9).fill({type:'image',...uploaded})),/limit/);
 const inherited=new PiAttachments(root,(sid,part)=>sid==='fork'&&JSON.stringify(part)===JSON.stringify(admitted.attachments[0]));assert.equal((await inherited.image('fork',uploaded.attachment)).data.length,data.length);await assert.rejects(()=>inherited.image('foreign',uploaded.attachment),/belong/);
});
test('attachment identity survives Stop, restart, text editing and terminal deduplication without replay',async t=>{
 const {root,store}=await fixture(t),upload=await store.upload('a',Buffer.from('queued'),'queued.txt'),{attachments}=await store.admit('a',[{type:'file',...upload,attachment:upload.file}]);
 const path=join(root,'queue.json'),q=new PiPromptQueue(path,'a');q.enqueue('first','',true,undefined,attachments);q.pause();const cold=new PiPromptQueue(path,'a');cold.recover();assert(cold.paused);assert.deepEqual(cold.snapshot().items[0].message.content,attachments);
 cold.replaceWaiting('first','edited','Read it now.',cold.snapshot().revision);assert.deepEqual(cold.read('edited').attachments,attachments);cold.resume();cold.dispatch('edited','turn');cold.accepted('edited');
 const died=new PiPromptQueue(path,'a');died.recover();assert(died.uncertain);assert.deepEqual(died.read('edited').attachments,attachments);assert.throws(()=>died.resume(),/unknown/);died.resolve('edited');assert.equal(died.lookup('edited','Read it now.',attachments).status,'cancelled');assert.throws(()=>died.lookup('edited','Read it now.',[]),/different input/);
});
test('browser upload and prompt failures retain exact attachment identity and never retry automatically',async()=>{
 const controller=new DshPiController('fixture');controller.update({sessionId:'a',phase:'ready'});const drafts=new DshAttachments(controller);let uploads=0;controller.fetcher=async()=>{uploads++;throw Error('Lost upload reply');};const file=new File(['synthetic'],'held.txt');drafts.add([file]);while(drafts.draft().uploads[drafts.draft().items[0].id]?.status==='uploading')await new Promise(r=>setTimeout(r,5));const item=drafts.draft().items[0];assert.equal(uploads,1);assert.equal(drafts.draft().uploads[item.id].status,'error');assert.equal(drafts.draft().items.length,1);
 drafts.retry(item.id);while(drafts.draft().uploads[item.id]?.status==='uploading')await new Promise(r=>setTimeout(r,5));assert.equal(uploads,2);
 const part={type:'file',receiptId:'synthetic',attachment:{attachmentId:'sha256:'+'a'.repeat(64),name:'held.txt',bytes:9}};let sends=0;controller.rpc=async()=>{sends++;throw Error('Lost prompt reply');};await assert.rejects(()=>controller.send('Read','queue',[part]),/unconfirmed/);assert.deepEqual(controller.pending.get('a').attachments,[part]);await assert.rejects(()=>controller.send('Read','queue',[part]),/unconfirmed/);assert.equal(sends,1);drafts.remove(item.id);assert.equal(drafts.draft().items.length,0);
});
test('binary upload/image carrier enforces bearer, browser origin and exact inspection scope',async t=>{
 const {store}=await fixture(t),data=await pixel();let writes=0;
 const host={getMeta:id=>{if(!['a','b'].includes(id))throw Error('Unknown conversation');return {id};},receiveAttachmentUpload:async(sid,read,name,mediaType)=>{const bytes=await read();writes++;return mediaType?store.uploadImage(sid,bytes,name,mediaType):store.upload(sid,bytes,name);},attachmentImage:(sid,ref)=>store.image(sid,ref)};
 const server=new HarnessServer(host),link=await server.start();t.after(()=>server.close());const url=link.origin+'/api/attachments/upload?sessionId=a&name=red.png&mediaType=image/png',options={method:'POST',body:data,headers:{Authorization:'Bearer '+server.token}};
 assert.equal((await fetch(url,{...options,headers:{}})).status,401);assert.equal((await fetch(url,{...options,headers:{...options.headers,Origin:'https://foreign.invalid'}})).status,403);assert.equal(writes,0);
 const upload=await (await fetch(url,options)).json(),own=server.openInspection('a'),foreign=server.openInspection('b'),token=x=>new URLSearchParams(new URL(x.url).hash.slice(1)).get('token');
 assert.equal((await fetch(url,{...options,headers:{Authorization:'Bearer '+token(own)}})).status,400);assert.equal(writes,1);
 const image=link.origin+'/api/attachments/image?'+new URLSearchParams({sessionId:'a',ref:JSON.stringify(upload.attachment)}),response=await fetch(image,{headers:{Authorization:'Bearer '+token(own)}});assert.equal(response.status,200);assert.equal(response.headers.get('content-type'),'image/png');assert.deepEqual(Buffer.from(await response.arrayBuffer()),data);
 assert.equal((await fetch(image,{headers:{Authorization:'Bearer '+token(foreign)}})).status,400);assert.equal((await fetch(image.replace('sessionId=a','sessionId=b'),{headers:options.headers})).status,400);
});
