// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,rm,mkdir,writeFile,readFile,symlink,rename} from 'node:fs/promises';import {join} from 'node:path';import {tmpdir} from 'node:os';import {createHash} from 'node:crypto';
import {WorkspaceFileSearch} from '../dist/runtime/vendor/dsh-file-reference/search.js';
import {PiFileReferences} from '../dist/runtime/src/file-references.js';import {HarnessDrafts} from '../dist/runtime/src/harness-drafts.js';import {draftReferences} from '../dist/protocol/src/draft-references.js';import {formatFileMention} from '../dist/runtime/vendor/dsh-file-reference/grammar.js';import {fileReferenceSource} from '../apps/harness/dsh-file-references.mjs';
import {Host} from '../dist/runtime/src/host.js';
async function tree(t){const root=await mkdtemp(join(tmpdir(),'augmentor-file-references-'));t.after(()=>rm(root,{recursive:true,force:true}));return root;}
const signal=()=>new AbortController().signal;
const chip=(text,ref,appearance='file')=>({source:'reference',ref,label:(appearance==='folder'?ref.slice(1,-1):ref.replace(/^@"|"$/g,'')).split('/').at(-1)+(appearance==='folder'?'/':''),appearance,clipboardText:ref,offset:text.indexOf(ref),length:ref.length});
test('reviewed public MIT modules keep selected hashes and their original search/grammar guidance boundary',async()=>{
 const root=new URL('../packages/runtime/vendor/dsh-file-reference/',import.meta.url),record=JSON.parse(await readFile(new URL('SOURCE.json',root)));assert.equal(record.license,'MIT');assert.equal(record.ref,'d743267388641bc76f17c45ce8b4c231aed1d32c');assert.equal(record.files.length,4);for(const file of record.files)assert.equal(createHash('sha256').update(await readFile(new URL(file.path,root))).digest('hex'),file.sha256);assert.match(await readFile(new URL('LICENSE',root),'utf8'),/MIT License/);
});
test('original search ranks only workspace paths, excludes build/symlink escapes, drills and refreshes after invalidation',async t=>{
 const root=await tree(t),other=join(root,'other'),one=join(root,'one');await mkdir(one);await mkdir(other);await mkdir(join(one,'docs'));await mkdir(join(one,'node_modules'));await writeFile(join(one,'node_modules','omit.txt'),'not a candidate');await writeFile(join(one,'docs','a note.txt'),'AUTHORED_UNREAD_CONTENT');await writeFile(join(one,'note.md'),'authored');await writeFile(join(other,'foreign.txt'),'foreign');if(process.platform!=='win32')await symlink(other,join(one,'escape'));
 const refs=new PiFileReferences();t.after(()=>refs.close());const top=await refs.list('one',one,'',signal());assert(top.some(x=>x.path==='docs'&&x.kind==='directory'));assert(!top.some(x=>x.path==='node_modules'||x.path==='escape'));assert.deepEqual(await refs.list('one',one,'../other/',signal()),[]);assert.deepEqual(await refs.list('one',one,'escape/',signal()),[]);assert.deepEqual(await refs.list('one',one,'docs/',signal()),[{path:'docs/a note.txt',kind:'file'}]);assert.equal((await refs.list('one',one,'note',signal()))[0].path,'note.md');assert.equal(formatFileMention({path:'docs/a note.txt',kind:'file'},false),'@"docs/a note.txt"');
 await writeFile(join(one,'fresh.txt'),'fresh');refs.invalidate('one');await refs.list('one',one,'fresh',signal());let rows=[];for(let i=0;i<40&&!rows.length;i++){await new Promise(r=>setTimeout(r,5));rows=await refs.list('one',one,'fresh',signal());}assert.deepEqual(rows,[{path:'fresh.txt',kind:'file'}]);assert.deepEqual(await refs.list('one',other,'foreign',signal()),[{path:'foreign.txt',kind:'file'}]);await assert.rejects(refs.list('one',one,'x\n',signal()),/Invalid/);const aborted=new AbortController();aborted.abort();await assert.rejects(refs.list('one',one,'',aborted.signal),/abort/i);
});
test('external root additions, renames and removals are visible on the first repeated fuzzy lookup',async t=>{
 const root=await tree(t),refs=new PiFileReferences();t.after(()=>refs.close());
 await writeFile(join(root,'existing.xlsx'),'fixture');await refs.list('one',root,'existing',signal());
 assert.deepEqual(await refs.list('one',root,'added.xls',signal()),[]);
 await writeFile(join(root,'added.xls'),'fixture');
 assert.deepEqual(await refs.list('one',root,'added.xls',signal()),[{path:'added.xls',kind:'file'}]);
 await rename(join(root,'added.xls'),join(root,'renamed.xls'));
 assert.deepEqual(await refs.list('one',root,'added.xls',signal()),[]);
 assert.deepEqual(await refs.list('one',root,'renamed.xls',signal()),[{path:'renamed.xls',kind:'file'}]);
 await rm(join(root,'renamed.xls'));assert.deepEqual(await refs.list('one',root,'renamed.xls',signal()),[]);
 await rm(root,{recursive:true});await assert.rejects(refs.list('one',root,'existing',signal()),/ENOENT/);
});
test('nested external additions refresh on demand after ten seconds; tool invalidation waits for fresh results immediately',async t=>{
 t.mock.timers.enable({apis:['Date'],now:1_000_000});
 const root=await tree(t),refs=new PiFileReferences();t.after(()=>refs.close());await mkdir(join(root,'docs'));
 await writeFile(join(root,'docs','old.md'),'fixture');await refs.list('one',root,'old',signal());
 await writeFile(join(root,'docs','external.md'),'fixture');
 assert.deepEqual(await refs.list('one',root,'docs/external',signal()),[{path:'docs/external.md',kind:'file'}]);
 assert.deepEqual(await refs.list('one',root,'external',signal()),[]);
 t.mock.timers.tick(10_000);
 assert.deepEqual(await refs.list('one',root,'external',signal()),[{path:'docs/external.md',kind:'file'}]);
 await writeFile(join(root,'docs','tool.md'),'fixture');refs.invalidate('one');
 assert.deepEqual(await refs.list('one',root,'tool',signal()),[{path:'docs/tool.md',kind:'file'}]);
});
test('overlapping windows share a traversal while cancellation and concurrent invalidation retain their authority',async t=>{
 const root=await tree(t),refs=new PiFileReferences();t.after(()=>refs.close());await mkdir(join(root,'docs'));
 await writeFile(join(root,'docs','before.md'),'fixture');
 let enter,release,blocked=true;const entered=new Promise(r=>enter=r),gate=new Promise(r=>release=r),original=WorkspaceFileSearch.prototype.list;
 t.mock.method(WorkspaceFileSearch.prototype,'list',async function(query,abort){if(blocked){blocked=false;const rows=await original.call(this,query,abort);enter();await gate;return rows;}return original.call(this,query,abort);});
 const firstAbort=new AbortController(),first=refs.list('one',root,'after',firstAbort.signal),rejected=assert.rejects(first,/abort/i);
 await entered;const second=refs.list('one',root,'after',signal());await new Promise(r=>setImmediate(r));
 await writeFile(join(root,'docs','after.md'),'fixture');refs.invalidate('one');firstAbort.abort();await rejected;release();
 assert.deepEqual(await second,[{path:'docs/after.md',kind:'file'}]);
 assert.deepEqual(await refs.list('one',root,'before',signal()),[{path:'docs/before.md',kind:'file'}]);
});
test('closing, changing workspace and LRU eviction discard an in-flight session generation',async t=>{
 for(const action of ['close','cwd','evict']){
  const root=await tree(t),other=await tree(t),refs=new PiFileReferences();t.after(()=>refs.close());
  await writeFile(join(root,'old.md'),'fixture');await writeFile(join(other,'new.md'),'fixture');
  let enter,release,blocked=true;const entered=new Promise(r=>enter=r),gate=new Promise(r=>release=r),original=WorkspaceFileSearch.prototype.list;
  const mocked=t.mock.method(WorkspaceFileSearch.prototype,'list',async function(query,abort){if(blocked){blocked=false;enter();await gate;}return original.call(this,query,abort);});
  const pending=refs.list('one',root,'old',signal());await entered;
  if(action==='close')refs.close();
  if(action==='cwd')assert.deepEqual(await refs.list('one',other,'new',signal()),[{path:'new.md',kind:'file'}]);
  if(action==='evict')for(let i=0;i<8;i++)await refs.list(`other-${i}`,other,'',signal());
  release();assert.deepEqual(await pending,[]);mocked.mock.restore();
 }
});
test('reference metadata survives cold drafts, changes its text CAS even with identical clipboard text, and settles exact uncertainty',async t=>{
 const root=await tree(t),store=new HarnessDrafts(root),text='😀 Read @"docs/a note.txt" now.',ref=chip(text,'@"docs/a note.txt"');const saved=store.setText('one',0,text,[ref]);assert.deepEqual(new HarnessDrafts(root).describe('one'),saved);assert.deepEqual(store.describe('two').references,undefined);assert.throws(()=>store.setText('one',0,text,[]),/another window/);const plain=store.setText('one',1,text,[]);assert.equal(plain.textRevision,2);assert.equal(plain.references,undefined);const rich=store.setText('one',2,text,[ref]);assert.equal(rich.textRevision,3);const prepared=store.prepare('one',rich.revision,'owned','queue');assert.deepEqual(store.settle('one','owned',false).references,[ref]);const current=store.describe('one');store.prepare('one',current.revision,'accepted','queue');assert.equal(store.settle('one','accepted',true).references,undefined);assert.equal(store.dirtyCount(),0);assert(prepared.submission);
 for(const bad of [{...ref,offset:0},{...ref,source:'foreign'},{...ref,label:'wrong'},{...ref,length:1},{...ref,occurrenceId:1}])assert.throws(()=>draftReferences(text,[bad]),/Invalid/);assert.throws(()=>draftReferences(text,[ref,ref]),/Invalid/);
 const invalid=store.setText('invalid',0,text,[{...ref,invalid:true}]);assert.throws(()=>store.prepare('invalid',invalid.revision,'pending','queue'),/unavailable/);assert.deepEqual(store.describe('invalid'),invalid);
});
test('late lookup loses its session authority and propagates the supplier cancellation signal without inserting content',async()=>{
 let resolve,allowed=true,captured;const scope={sessionId:'one',epoch:1},controller={rpc:async(method,p,s)=>{captured={method,p,s};return new Promise(r=>resolve=r);}};
 const source=fileReferenceSource({controller,valid:()=>allowed,fileCandidate:r=>[r],crumbsFor:()=>undefined,parseCandidate:JSON.parse,t:x=>x},scope),abort=new AbortController(),pending=source.candidates(null,{query:'note',signal:abort.signal});allowed=false;resolve([{path:'note.txt',kind:'file'}]);assert.deepEqual(await pending,[]);assert.equal(captured.method,'session.fileReferences');assert.equal(captured.s,abort.signal);
 allowed=true;const picked=source.onPick({candidate:{value:JSON.stringify({kind:'file',fileKind:'directory',label:'a folder',mention:'@"a folder/'})},action:'pick'});assert.equal(picked.insert.ref,'@"a folder/"');assert.deepEqual(source.onPick({candidate:{value:JSON.stringify({kind:'file',fileKind:'directory',mention:'@"a folder/'})},action:'drill'}),{text:'@"a folder/',continue:true});
});
test('Host lookup lease blocks maintenance while metadata is pending, releases on abort, and refuses archived/browser authority before discovery',async()=>{
 // Component lifecycle evidence: a controlled metadata wait, no SDK/provider.
 const host=Object.assign(Object.create(Host.prototype),{dictation:{active:false},voice:{active:false,owns:()=>false},sessionExports:{active:0}}),meta={id:'one',cwd:'/authored-workspace',surface:'linux'},abort=new AbortController();let entered=0;
 Object.assign(host,{referenceRequests:0,quiescing:false,organization:{archived:()=>false},jobs:{busy:false},compactions:{busy:false},uploads:0,getMeta:()=>meta,fileReferences:{list:async(_sid,_cwd,_q,signal)=>{entered++;return new Promise((_,reject)=>signal.addEventListener('abort',()=>reject(Error('lookup aborted')),{once:true}));}}});
 const pending=host.listFileReferences('one','',abort.signal),rejection=assert.rejects(pending,/aborted/);assert.equal(host.referenceRequests,1);await assert.rejects(host.handle('host.prepareShutdown',{},'maintenance'),/file-reference lookups/);abort.abort();await rejection;assert.equal(host.referenceRequests,0);
 meta.surface='browser';await assert.rejects(host.listFileReferences('one',''),/unavailable/);meta.surface='linux';host.organization.archived=()=>true;await assert.rejects(host.listFileReferences('one',''),/unavailable/);assert.equal(entered,1);
});
