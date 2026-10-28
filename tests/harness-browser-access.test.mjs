// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,readFileSync,chmodSync,symlinkSync,linkSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {browserAccess} from '../apps/harness/browser-access.js';
import {savedHarnessAccess} from '../dist/runtime/src/harness-access.js';
import {HarnessServer} from '../dist/runtime/src/harness-server.js';
import {privateDir,atomicJson} from '../dist/runtime/src/storage.js';
import {planFixture} from './fixtures/plans.mjs';
const key='augmentor-harness-operator-token',tabKey='augmentor-harness-token';
const store=()=>{const values=new Map();return {getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v)};};
const token='a'.repeat(64),inspector='b'.repeat(64);
test('an authenticated operator can reopen a bare URL in a separate tab',()=>{
 const browser=store(),tab=store(),first=browserAccess(new URLSearchParams({token}),tab,browser);
 assert.equal(browser.getItem(key),null,'unverified links are not remembered');
 first.confirm({mode:'operator'});assert.equal(browser.getItem(key),token);
 const secondTab=store(),second=browserAccess(new URLSearchParams(),secondTab,browser);
 assert.equal(second.token,token);assert.equal(secondTab.getItem(tabKey),token);
});
test('explicit inspection and expired tab credentials never fall back to remembered operator authority',()=>{
 const browser=store(),tab=store();browser.setItem(key,token);tab.setItem(tabKey,token);
 const access=browserAccess(new URLSearchParams({token:inspector}),tab,browser);assert.equal(access.token,inspector);
 access.confirm({mode:'read-only'});assert.equal(browser.getItem(key),token);assert.equal(tab.getItem(tabKey),inspector);
 assert.equal(browserAccess(new URLSearchParams(),tab,browser).token,inspector,'no automatic retry/upgrade after a denied inspector');
 assert.equal(browserAccess(new URLSearchParams({token:''}),store(),browser).token,'','explicit empty links do not upgrade');
});
test('missing or disabled browser storage keeps private-link authentication available',()=>{
 const denied={getItem(){throw Error('blocked');},setItem(){throw Error('blocked');}};
 assert.equal(browserAccess(new URLSearchParams(),store(),store()).token,null);
 const access=browserAccess(new URLSearchParams({token}),denied,denied);assert.equal(access.token,token);assert.doesNotThrow(()=>access.confirm({mode:'operator'}));
});
function descriptor(t,value={pid:123,url:'http://127.0.0.1:39121/#token='+token,origin:'http://127.0.0.1:39121'}){
 const root=mkdtempSync(join(tmpdir(),'augmentor-browser-key-')),path=join(root,'harness.json');
 t.after(()=>rmSync(root,{recursive:true,force:true}));privateDir(root);atomicJson(path,value);return {root,path};
}
test('a private legacy owner descriptor supplies the same bounded credential and port without rewriting it',t=>{
 const {path}=descriptor(t),before=readFileSync(path);assert.deepEqual(savedHarnessAccess(path),{token,port:39121});assert.deepEqual(readFileSync(path),before);assert.equal(savedHarnessAccess(path+'.missing'),undefined);
});
test('a persistent browser record has explicit bounded identity rather than a live-owner claim',t=>{
 const {path}=descriptor(t,{schema:'augmentor-harness-browser-access/1',token,port:39121});
 assert.deepEqual(savedHarnessAccess(path),{token,port:39121});
 writeFileSync(path,JSON.stringify({schema:'augmentor-harness-browser-access/2',token,port:39121}));assert.throws(()=>savedHarnessAccess(path),/identity/);
});
test('foreign-writable, linked, hard-linked and oversized connection records refuse unchanged',{skip:process.platform==='win32'},t=>{
 const {path}=descriptor(t),before=readFileSync(path);chmodSync(path,0o644);assert.throws(()=>savedHarnessAccess(path),/invalid private/);chmodSync(path,0o600);
 symlinkSync(path,path+'.link');assert.throws(()=>savedHarnessAccess(path+'.link'),/invalid private/);
 linkSync(path,path+'.hard');assert.throws(()=>savedHarnessAccess(path),/invalid private/);rmSync(path+'.hard');
 assert.deepEqual(readFileSync(path),before);writeFileSync(path,'x'.repeat(8193));assert.throws(()=>savedHarnessAccess(path),/invalid private/);assert.equal(readFileSync(path).length,8193);
});
test('remote, inconsistent, malformed and scoped identities refuse rather than silently rotating a bookmark',t=>{
 const {path}=descriptor(t);const rows=[{pid:1,url:'https://example.invalid/#token='+token,origin:'https://example.invalid'},
 {pid:1,url:'http://127.0.0.1:39121/#token='+token,origin:'http://127.0.0.1:39122'},
 {pid:1,url:'http://127.0.0.1:39121/#token='+token+'&session=private',origin:'http://127.0.0.1:39121'},
 {pid:1,url:'http://127.0.0.1:39121/#token=wrong',origin:'http://127.0.0.1:39121'}];
 for(const row of rows){writeFileSync(path,JSON.stringify(row));const before=readFileSync(path);assert.throws(()=>savedHarnessAccess(path),/invalid Harness connection identity/);assert.deepEqual(readFileSync(path),before);}
 writeFileSync(path,'{');assert.throws(()=>savedHarnessAccess(path),/malformed/);
});
test('a restarted real Host keeps the bookmark and bearer while anonymous requests remain refused',{timeout:30000},async t=>{
 const f=await planFixture(t),first=await f.call('harness.open'),credential=new URLSearchParams(new URL(first.url).hash.slice(1)).get('token');
 const access=async origin=>fetch(origin+'/api/access',{headers:{Authorization:'Bearer '+credential}});
 assert.equal((await access(first.origin)).status,200);assert.equal((await fetch(first.origin+'/api/access')).status,401);
 await f.stop();await f.start();const second=await f.call('harness.open');assert.equal(second.origin,first.origin);assert.equal(second.url,first.url);
 assert.equal((await access(second.origin)).status,200);assert.equal((await fetch(second.origin+'/api/access')).status,401);assert.equal(f.requests.length,0);
});
test('invalid supplied operator identities cannot weaken the HTTP transport',()=>{
 assert.throws(()=>new HarnessServer({},undefined,'wrong'),/exact private/);
});
