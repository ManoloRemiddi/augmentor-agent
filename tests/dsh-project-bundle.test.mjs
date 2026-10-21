// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {readFile,writeFile,readdir,rm,rename,symlink,link,chmod,mkdir} from 'node:fs/promises';import {existsSync} from 'node:fs';import {join} from 'node:path';import {pathToFileURL} from 'node:url';
import {bundleFixture,application,sha} from './fixtures/dsh-bundle.mjs';
import {authoredDshProject} from './fixtures/dsh-project.mjs';import {authoredRichDshProject} from './fixtures/dsh-rich-project.mjs';import {authoredDshFamily} from './fixtures/dsh-family-project.mjs';
const {importDshProject,prepareDshProject,dshHistoryCut}=await import(pathToFileURL(join(application,'dist/runtime/src/dsh-project-import.js')));
const {loadDshProjectArchive,dshRecordsDigest}=await import(pathToFileURL(join(application,'dist/runtime/src/dsh-project-archive.js')));
const {DshArchivedFamily}=await import(pathToFileURL(join(application,'dist/runtime/src/dsh-archived-family.js')));
const {importDshProjects}=await import(pathToFileURL(join(application,'dist/runtime/src/dsh-project-batch.js')));
const {inspectNativeProfile,importNativeProfile}=await import(pathToFileURL(join(application,'dist/runtime/src/native-profile-import.js')));
const sdk=JSON.parse(await readFile(join(application,'node_modules/@earendil-works/pi-coding-agent/package.json'))),{SessionManager}=await import(pathToFileURL(join(application,'node_modules/@earendil-works/pi-coding-agent',sdk.exports['.'].import)));
const check=(name,fn)=>test(name,{skip:process.platform!=='linux'},fn);
const display=async(state,id)=>(await readFile(join(state,'sessions',id+'.events.jsonl'),'utf8')).trim().split('\n').map(JSON.parse);
const binding=(manager)=>manager.getEntries().find(row=>row.type==='custom'&&row.customType==='augmentor.dsh-import.v1').data;
async function native(state,id){const meta=JSON.parse(await readFile(join(state,'sessions',id+'.meta.json')));return {meta,manager:SessionManager.open(meta.file)};}
check('real read-only exporter bundle cold-opens all parents, images and exact source objects without replay',async t=>{
 const f=await bundleFixture(t,authoredRichDshProject),prepared=prepareDshProject(f.source,f.options);assert(prepared.expandedBytes>f.raw.length);assert.equal(f.manifest.schema,'augmentor-dsh-project-export/2');
 assert.deepEqual(Object.keys(f.exportReport.readOnlyRequests).sort(),['session.list','session/follow','session/page','workspace.list']);
 const checked=loadDshProjectArchive(f.source,f.options.sourceSha256);assert.throws(()=>checked.readObject({sha256:'../private',bytes:1}),/bundle/);const valid=checked.objects.values().next().value;assert.throws(()=>checked.readObject({...valid,bytes:valid.bytes+1}),/bundle/);
 const hydrated=checked.source;assert.deepEqual(hydrated.sessions[0].records,f.value.sessions[0].records);assert.equal(dshRecordsDigest(hydrated.sessions[0].records),sha(JSON.stringify(f.value.sessions[0].records)));
 const receipt=await importDshProject(f.source,f.state,f.options);assert.equal(receipt.sessions.length,3);assert.deepEqual(await readFile(join(f.state,receipt.rawArchive)),f.raw);
 const sourceObjects=await readdir(join(f.bundle,'objects')),targetObjects=await readdir(join(f.state,'dsh-imports','objects'));assert.deepEqual(targetObjects.sort(),sourceObjects.sort());for(const name of sourceObjects)assert.deepEqual(await readFile(join(f.bundle,'objects',name)),await readFile(join(f.state,'dsh-imports','objects',name)));
 const {manager}=await native(f.state,receipt.sessions[0].sessionId),text=JSON.stringify(manager.buildSessionContext().messages);assert(text.includes('AUTHORED-REASONING'));assert(!text.includes('OPAQUE-REPLAY'));assert(!manager.buildSessionContext().messages.some(row=>row.role==='assistant'||row.role==='toolResult'));assert((await display(f.state,receipt.sessions[0].sessionId)).some(row=>row.type==='tool/result'));
 assert.equal(await readFile(f.source,'utf8'),f.raw.toString());
});
check('multi-segment history larger than v1 stays complete while tool context is bounded',async t=>{
 const f=await bundleFixture(t,cwd=>{const value=authoredDshProject(cwd);for(const session of value.sessions)session.records[4].event.data.message.content[0].text='HEAD '+('authored complete tool bytes '.repeat(450000))+' TAIL';return value;});
 assert(f.exportReport.receipt.expandedBytes>32*1024*1024);assert(f.raw.length<16384);assert(f.manifest.sessions.every(row=>row.segments.length>=3));
 const receipt=await importDshProject(f.source,f.state,f.options);for(const [i,row] of receipt.sessions.entries()){const events=await display(f.state,row.sessionId);assert.equal(events.find(e=>e.type==='tool/result').data.result.content[0].text,f.value.sessions[i].records[4].event.data.message.content[0].text);const {manager}=await native(f.state,row.sessionId);assert(JSON.stringify(manager.buildSessionContext().messages).length<20000);assert(row.toolPayloadCharsNotInContext>10000000);}
});
check('bundled child originals/images and historical cuts keep original ownership after cold native relocation',async t=>{
 const f=await bundleFixture(t,authoredDshFamily),receipt=await importDshProject(f.source,f.state,f.options),id=receipt.sessions[0].sessionId,{manager}=await native(f.state,id),events=await display(f.state,id),family=new DshArchivedFamily(f.state,id,binding(manager),events),child=family.items()[0],scope=family.scope(child.sessionId);
 assert.equal(family.items().length,2);assert.deepEqual((await family.image(scope,f.authored.attachment)).data,f.authored.bytes);const original=family.originals(scope,{limit:1}).entries[0];assert.equal(family.original(scope,{entryId:original.entryId,entryHash:original.entryHash}).text,JSON.stringify(f.value.relatedSessions[0].records.at(-1)));
 const source=loadDshProjectArchive(join(f.state,receipt.rawArchive),f.options.sourceSha256).source,root=source.sessions[0];const cut=dshHistoryCut(root,source,f.options.sourceSha256,f.state,root.opening.cursor);assert(cut.display.some(row=>row.type==='subagent/catalog'));assert(!cut.manager.buildSessionContext().messages.some(row=>row.role==='toolResult'));
 const target=join(f.base,'relocated'),inspection=inspectNativeProfile(f.state);await importNativeProfile(f.state,target,inspection.stateSha256);const moved=await native(target,id),movedFamily=new DshArchivedFamily(target,id,binding(moved.manager),await display(target,id));assert.equal(movedFamily.items().length,2);assert.deepEqual((await movedFamily.image(movedFamily.scope(movedFamily.items()[0].sessionId),f.authored.attachment)).data,f.authored.bytes);
});
check('v1 and bundled identical cuts retain existing native continuation without duplicate imports',async t=>{
 const f=await bundleFixture(t,authoredDshProject),legacy=join(f.base,'legacy.json');await writeFile(legacy,JSON.stringify(f.value),{mode:0o600});const first=await importDshProject(legacy,f.state,{...f.options,sourceSha256:sha(await readFile(legacy))}),n=await native(f.state,first.sessions[0].sessionId);n.manager.appendMessage({role:'user',content:'New retained human continuation',timestamp:1700001000000});const before=await readFile(n.meta.file);
 const receipt=await importDshProjects([{sourceFile:f.source,options:f.options}],f.state);assert.equal(receipt.result.createdSessions.length,0);assert.equal(receipt.result.retainedSessions.length,3);assert.deepEqual(await readFile(n.meta.file),before);
});
for(const kind of ['missing','changed','symbolic link','hard link','FIFO','segment count','segment sequence','oversized ref','traversal','object directory link','expanded budget'])check('bundled '+kind+' fails before any destination is published',async t=>{
 const f=await bundleFixture(t,authoredDshProject),ref=f.manifest.sessions[0].segments[0],path=join(f.bundle,'objects',ref.sha256);
 if(kind==='missing')await rm(path);
 if(kind==='changed')await writeFile(path,Buffer.alloc(ref.bytes,88));
 if(kind==='symbolic link'){const other=path+'.saved';await rename(path,other);await symlink(other,path);}
 if(kind==='hard link')await link(path,path+'.alias');
 if(kind==='FIFO'){await rm(path);const {execFileSync}=await import('node:child_process');execFileSync('mkfifo',[path]);}
 if(kind==='segment count'){ref.count++;await writeFile(f.source,JSON.stringify(f.manifest));}
 if(kind==='segment sequence'){ref.firstSeq++;await writeFile(f.source,JSON.stringify(f.manifest));}
 if(kind==='oversized ref'){ref.bytes=16*1024*1024+1;await writeFile(f.source,JSON.stringify(f.manifest));}
 if(kind==='traversal'){ref.sha256='../private';await writeFile(f.source,JSON.stringify(f.manifest));}
 if(kind==='expanded budget'){f.manifest.sessions[0].segments=Array.from({length:17},(_,i)=>({...ref,bytes:16*1024*1024,firstSeq:i,count:1}));await writeFile(f.source,JSON.stringify(f.manifest));}
 if(kind==='object directory link'){const directory=join(f.bundle,'objects');await rename(directory,directory+'.saved');await symlink(directory+'.saved',directory);}
 f.options.sourceSha256=sha(await readFile(f.source));await assert.rejects(()=>importDshProject(f.source,f.state,f.options));assert(!existsSync(f.state));assert(!(await readdir(f.base)).some(name=>name.startsWith('.dsh-import-')));
});
check('changing an object after preparation prevents staging and unlisted files are never copied',async t=>{
 const f=await bundleFixture(t,authoredDshProject),project=prepareDshProject(f.source,f.options),objects=join(f.bundle,'objects');await writeFile(join(objects,'unlisted-private-file'),'MUST NOT COPY',{mode:0o600});const stage=join(f.base,'stage');await mkdir(stage,{mode:0o700});await project.write(stage,f.state);assert(!(await readdir(join(stage,'dsh-imports','objects'))).includes('unlisted-private-file'));
 const g=await bundleFixture(t,authoredDshProject),prepared=prepareDshProject(g.source,g.options),ref=g.manifest.sessions[0].segments[0];await writeFile(join(g.bundle,'objects',ref.sha256),Buffer.alloc(ref.bytes,88));const failedStage=join(g.base,'stage');await mkdir(failedStage,{mode:0o700});await assert.rejects(()=>prepared.write(failedStage,g.state));assert(!existsSync(join(failedStage,'sessions','dsh-import-'+sha('authored-alpha').slice(0,24)+'.meta.json')));assert(!existsSync(g.state));
});

check('complete raw image collections exceed v1 without inline base64 or missing receipt bytes',async t=>{
 const {default:sharp}=await import('sharp');
 const f=await bundleFixture(t,async cwd=>{const value=authoredDshProject(cwd);value.attachments=[];
  for(let i=0;i<5;i++){const bytes=await sharp(Buffer.alloc(1500*1500*3,i*31),{raw:{width:1500,height:1500,channels:3}}).png({compressionLevel:0}).toBuffer(),attachment={attachmentId:'sha256:'+sha(bytes),bytes:bytes.length,mediaType:'image/png',width:1500,height:1500,name:'authored-'+i+'.png'};value.sessions[0].records[1].event.data.content.push({type:'image',attachment});value.attachments.push({attachmentId:attachment.attachmentId,bytes:bytes.length,data:bytes.toString('base64')});}return value;
 });
 assert(f.exportReport.receipt.expandedBytes>32*1024*1024);assert(f.raw.length<16384);assert(f.manifest.attachments.every(row=>!('data' in row)));
 const receipt=await importDshProject(f.source,f.state,f.options),id=receipt.sessions[0].sessionId,{PiAttachments}=await import(pathToFileURL(join(application,'dist/runtime/src/attachments.js'))),store=new PiAttachments(f.state);
 const images=(await display(f.state,id)).find(row=>row.type==='user/message').data.content.filter(row=>row.type==='image');assert.deepEqual(images,f.value.sessions[0].records[1].event.data.content.filter(row=>row.type==='image'));
 for(const part of images){const image=await store.image(id,part.attachment);assert.equal(sha(Buffer.from(image.data)),part.attachment.attachmentId.slice(7));}
});
check('combined bundle accounting refuses an expanded second project before reading its objects or publishing state',async t=>{
 const first=await bundleFixture(t,authoredDshProject),second=await bundleFixture(t,cwd=>{const value=authoredDshProject(cwd);value.sessions=value.sessions.slice(0,1);value.sessions[0].opening.header.id='authored-other';value.workspace.sessionIds=['authored-other'];value.pinnedSessionIds=[];value.archivedSessionIds=[];return value;});
 const segment=second.manifest.sessions[0].segments[0];second.manifest.sessions[0].segments=Array.from({length:16},(_,i)=>({...segment,bytes:16*1024*1024,firstSeq:i,count:1}));
 // Fifteen expanded 16 MiB references fit a single bundle; the first project
 // consumes the remaining batch space. Repeated refs cannot discount the budget.
 second.manifest.sessions[0].segments.pop();const payload=' '.repeat(17*1024*1024),large=JSON.stringify({...first.value,authoredIgnoredPadding:payload});await writeFile(first.input,large,{mode:0o600});await writeFile(second.source,JSON.stringify(second.manifest),{mode:0o600});
 const secondSha=sha(await readFile(second.source));
 await assert.rejects(()=>importDshProjects([{sourceFile:first.input,options:{...first.options,sourceSha256:sha(large)}},{sourceFile:second.source,options:{...second.options,sourceSha256:secondSha}}],join(first.base,'batch')),/256 MiB expanded/);
 assert(!existsSync(join(first.base,'batch')));
});
check('oversized bundled child history keeps a bounded preview and exact scoped source excerpts',async t=>{
 const f=await bundleFixture(t,async cwd=>{const authored=await authoredDshFamily(cwd);authored.value.relatedSessions[0].records[4].event.data.message.content[0].text='CHILD HEAD '+('complete child tool bytes '.repeat(100000))+' CHILD TAIL';return authored;}),receipt=await importDshProject(f.source,f.state,f.options),id=receipt.sessions[0].sessionId,{manager}=await native(f.state,id),family=new DshArchivedFamily(f.state,id,binding(manager),await display(f.state,id)),scope=family.scope(family.items()[0].sessionId),page=family.history(scope,{maxMessages:100}),preview=page.events.find(row=>row.event.type==='tool/result').event.data.historicalDisplayPreview;
 assert.equal(page.hasMore,false);assert.equal(preview.source,'dsh-archive');assert.equal(preview.entryId,'dsh-4');assert(preview.bytes>1024*1024);const head=family.original(scope,{entryId:preview.entryId,entryHash:preview.entryHash,limit:64}),tail=family.original(scope,{entryId:preview.entryId,entryHash:preview.entryHash,offset:preview.bytes-1024,limit:1024});assert.equal(head.available,true);assert(head.hasMore);assert(tail.text.includes('CHILD TAIL'));assert.deepEqual((await family.image(scope,f.authored.attachment)).data,f.authored.bytes);
});
