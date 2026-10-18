// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored profiles; actual sealed Host/SDK and desktop validation.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,rename,stat,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {once} from 'node:events';
import {managedReviewFixture} from './fixtures/harness-review.mjs';
import {PiConnection} from '../dist/client/src/socket.js';
import {localConnect} from '../dist/platform/src/transport.js';
import {until} from './fixtures/plans.mjs';
async function connect(path){const socket=localConnect(path);await once(socket,'connect');const peer=new PiConnection(socket,()=>{});await peer.call('host.hello',{protocol:'augmentor-pi/1'});return peer;}

test('MX registered review reopens the actual profile warm/cold without replay, rejects an unconfirmed live owner and installs only owned stable menu entries',{skip:process.platform!=='linux',timeout:180000},async t=>{
 const f=await managedReviewFixture(t),sid='authored-review-session';await f.call('session.create',{sessionId:sid,cwd:f.workspace,selection:f.selection});
 await f.prompt(sid,{kind:'read'});const before=await f.native(sid),history=await f.call('session.history',{sessionId:sid,maxMessages:100}),initial=await f.call('host.describe');assert.equal(f.requests.length,2);
 const args=(id,revision,extras=[])=>['register',id,'--release',f.release,'--profile',f.input,'--title','Authored Harness '+id,'--expected-revision',String(revision),...extras];
 await t.test('warm reopen returns a current scoped private link and default browser output never leaks it',async()=>{
  f.profile.sessionId=sid;await writeFile(f.input,JSON.stringify(f.profile),{mode:0o600});assert.equal(JSON.parse((await f.run(args('main',0))).stdout).revision,1);
  const {stdout}=await f.run(['open','main','--print-url']);const link=new URL(stdout.trim());assert.equal(new URLSearchParams(link.hash.slice(1)).get('session'),sid);assert.equal((await f.call('host.describe')).pid,initial.pid);
  const bin=join(f.root,'fake-bin');await mkdir(bin,{mode:0o700});const captured=join(f.root,'opened-url');await writeFile(join(bin,'xdg-open'),'#!/bin/sh\nprintf "%s" "$1" > "$HARNESS_AUTHORED_URL"\nprintf "%s" "$1"\nprintf "%s" "$1" >&2\n',{mode:0o700});
  const opened=await f.run(['open','main'],{PATH:bin+':'+process.env.PATH,HARNESS_AUTHORED_URL:captured});assert.equal(opened.stdout,'');assert.equal(opened.stderr,'');assert.equal(await readFile(captured,'utf8'),stdout.trim());assert(!JSON.stringify(JSON.parse(await readFile(join(f.registry,'reviews.json')))).includes('token='));
  assert((await f.native(sid)).bytes.equals(before.bytes));assert.deepEqual(await f.call('session.history',{sessionId:sid,maxMessages:100}),history);assert.equal(f.requests.length,2);
 });
 await t.test('a pending managed deployment blocks warm private-link opening without disturbing the actual owner',async()=>{
  const fence=join(f.base,'dsh-preservation.json');await writeFile(fence,'AUTHORED PENDING PUBLICATION',{mode:0o600});
  try{await assert.rejects(f.run(['open','main','--print-url']),error=>/requires recovery/.test(error.stderr)&&error.stdout==='');}
  finally{await rm(fence);}
  assert.equal((await f.call('host.describe')).pid,initial.pid);assert.equal(f.requests.length,2);
  assert((await f.native(sid)).bytes.equals(before.bytes));
 });
 await t.test('a conflicting profile or missing socket with a live exact owner cannot start a replacement',async()=>{
  const foreign=join(f.root,'foreign-config');await mkdir(foreign,{mode:0o700});const other=join(f.root,'foreign.json');await writeFile(other,JSON.stringify({...f.profile,config:foreign}),{mode:0o600});const bad=args('foreign',1);bad[bad.indexOf('--profile')+1]=other;
  await assert.rejects(f.run(bad),error=>error.stderr.includes('does not match'));assert.equal(JSON.parse((await f.run(['status'])).stdout).revision,1);
  await rename(f.profile.socket,f.profile.socket+'.held');try{await assert.rejects(f.run(['open','main','--print-url']),error=>error.stderr.includes('live process'));assert.equal((await f.call('host.describe')).pid,initial.pid);}finally{await rename(f.profile.socket+'.held',f.profile.socket);}
  assert((await f.native(sid)).bytes.equals(before.bytes));assert.equal(f.requests.length,2);
 });
 let cold;
 await t.test('two cold opens converge on one actual sealed runtime and retain native history without a model call',async()=>{
  const oldUrl=(await f.run(['open','main','--print-url'])).stdout.trim();await f.stop();
  const results=await Promise.all([f.run(['open','main','--print-url'],{OPENAI_API_KEY:'CALLER-KEY-MUST-NOT-BE-FORWARDED'}),f.run(['open','main','--print-url'])]);assert.equal(results[0].stdout,results[1].stdout);assert.equal(results[0].stdout.trim(),oldUrl,'the owner profile keeps its authenticated bookmark across a confirmed cold restart');const reopened=new URL(oldUrl),credential=new URLSearchParams(reopened.hash.slice(1)).get('token');assert.equal((await fetch(reopened.origin+'/api/access')).status,401);assert.equal((await fetch(reopened.origin+'/api/access',{headers:{Authorization:'Bearer '+credential}})).status,200);
  cold=await connect(f.profile.socket);t.after(()=>cold?.close());const status=await cold.call('host.describe');assert.notEqual(status.pid,initial.pid);assert.equal(status.stateDir,f.state);assert.equal(status.configDir,f.config);
  const env=await readFile('/proc/'+status.pid+'/environ','utf8');assert(!env.includes('CALLER-KEY-MUST-NOT-BE-FORWARDED'));assert(env.includes('PI_TELEMETRY=0'));
  assert((await f.native(sid)).bytes.equals(before.bytes));assert.deepEqual(await cold.call('session.history',{sessionId:sid,maxMessages:100}),history);assert.equal(f.requests.length,2);
 });
 await t.test('sealed installer writes stable token-free menu entries, preserves collisions, and removal leaves the running profile intact',async()=>{
  const menu=join(f.root,'menu-data'),env={XDG_DATA_HOME:menu};const result=JSON.parse((await f.runSealed(args('main',1,['--install']),env)).stdout);assert.equal(result.revision,2);assert.equal(result.menuInstalled,true);
  const registry=JSON.parse(await readFile(join(f.registry,'reviews.json'))),desktop=registry.entries.main.menuFiles[0],text=await readFile(desktop,'utf8');assert(text.includes(join(f.root,'.local/bin/augmentor-harness-review')));assert(!text.includes(f.release));assert(!text.includes('token='));assert.equal((await stat(join(f.root,'.local/bin/augmentor-harness-review'))).mode&0o777,0o700);
  await writeFile(desktop,'KEEP-OWNER-EDIT');await assert.rejects(f.runSealed(['remove','main','--expected-revision','2'],env),error=>error.stderr.includes('edited'));assert.equal(await readFile(desktop,'utf8'),'KEEP-OWNER-EDIT');await writeFile(desktop,text);assert.equal(JSON.parse((await f.runSealed(['remove','main','--expected-revision','2'],env)).stdout).revision,3);
  assert((await f.native(sid)).bytes.equals(before.bytes));assert.equal(f.requests.length,2);assert.equal((await cold.call('session.list')).items.length,1);
 });
 assert(cold);await cold.call('host.shutdown');await until(async()=>{try{const status=await cold.call('host.describe');return !status.pid;}catch{return true;}},'cold owner shutdown acknowledgement');cold.close();cold=undefined;
});
