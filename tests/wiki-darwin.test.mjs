// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,symlink,link,rename,rm,realpath,truncate,stat} from 'node:fs/promises';
import {tmpdir} from 'node:os';import {join} from 'node:path';
import {DarwinWikiFs} from '../dist/runtime/src/wiki-darwin.js';
const fixture=async(t)=>{const base=await mkdtemp(join(await realpath(tmpdir()),'wiki-native-')),root=join(base,'vault'),outside=join(base,'outside');await mkdir(root);await mkdir(outside);let clients=[];t.after(async()=>{for(const c of clients)await c.close();await rm(base,{recursive:true,force:true});});const client=async(write=true,path=root,createRoot=false)=>{let attempts=0;const c=new DarwinWikiFs(()=>attempts++);clients.push(c);await c.call('init',{root:path,write,createRoot});return {c,attempts:()=>attempts};};return {base,root,outside,client};};
const encoded=x=>Buffer.from(x).toString('base64');
test('native dir_fd helper refuses linked paths, hardlinks, traversal, read-only mutations and oversized reads',async t=>{
 const {root,outside,client}=await fixture(t);await writeFile(join(outside,'secret.md'),'OUTSIDE');await symlink(outside,join(root,'linked'));await symlink(join(outside,'secret.md'),join(root,'leaf.md'));await link(join(outside,'secret.md'),join(root,'hard.md'));
 const {c}=await client(false);for(const path of [['linked','secret.md'],['leaf.md'],['hard.md'],['..','outside','secret.md']])await assert.rejects(c.call('read',{path}));
 await assert.rejects(c.call('write',{path:['new.md'],data:encoded('NO')}),/cannot change/);await assert.rejects(c.call('mkdir',{path:['new']}),/cannot change/);
 const large=join(root,'large.md');await writeFile(large,'');await truncate(large,64*1024*1024+1);await assert.rejects(c.call('read',{path:['large.md']}),/oversized/);assert.equal(await readFile(join(outside,'secret.md'),'utf8'),'OUTSIDE');
});
test('native helper pins the admitted root across replacement and preserves archive collisions',async t=>{
 const {base,root,outside,client}=await fixture(t);const {c,attempts}=await client();await c.call('mkdir',{path:['.archive']});await c.call('write',{path:['.archive','source.txt'],data:encoded('ORIGINAL')});
 await assert.rejects(c.call('write',{path:['.archive','source.txt'],data:encoded('DIFFERENT')}),/different bytes/);assert.equal(await readFile(join(root,'.archive/source.txt'),'utf8'),'ORIGINAL');
 const moved=join(base,'pinned');await rename(root,moved);await symlink(outside,root);await c.call('write',{path:['inside.md'],data:encoded('INSIDE')});assert.equal(await readFile(join(moved,'inside.md'),'utf8'),'INSIDE');await assert.rejects(stat(join(outside,'inside.md')),e=>e.code==='ENOENT');assert(attempts()>0);
});
test('native exclusive lock handles, directory entries and missing-root scaffold retain filesystem semantics',async t=>{
 const {base,client}=await fixture(t);const path=join(base,'new-vault'),{c}=await client(true,path,true);await c.call('mkdir',{path:['wiki']});const h=await c.call('open',{path:['wiki','lock']});await assert.rejects(c.call('open',{path:['wiki','lock']}),e=>e.code==='EEXIST');await c.call('handleWrite',{handle:h,data:encoded('LOCK')});await c.call('handleClose',{handle:h});assert.equal(Buffer.from(await c.call('read',{path:['wiki','lock']}),'base64').toString(),'LOCK');const entries=await c.call('readdir',{path:['wiki']});assert.equal(entries[0].name,'lock');await c.call('rm',{path:['wiki','lock']});await c.call('rm',{path:['wiki','missing'],force:true});await c.close();await assert.rejects(c.call('read',{path:[]}),/closed/);
});
