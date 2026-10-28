// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual private Host, approved commands, and independent read-only kernel handles.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {readFile,writeFile,stat} from 'node:fs/promises';
import {join} from 'node:path';
import {pythonExecutable} from '../dist/platform/src/index.js';
import {planFixture,until} from './fixtures/plans.mjs';
const windows={skip:process.platform!=='win32'&&'requires actual Windows Job objects',timeout:60000};
const observerCode=`import json,sys
import win32api,win32con,win32event
handles=[]
try:
 for pid in json.loads(sys.argv[1]):handles.append(win32api.OpenProcess(win32con.SYNCHRONIZE,False,pid))
 print(json.dumps({'ready':True}),flush=True)
 for line in sys.stdin:
  if line.strip()=='wait':print(json.dumps({'exited':[win32event.WaitForSingleObject(h,5000)==win32event.WAIT_OBJECT_0 for h in handles]}),flush=True)
  elif line.strip()=='poll':print(json.dumps({'exited':[win32event.WaitForSingleObject(h,0)==win32event.WAIT_OBJECT_0 for h in handles]}),flush=True)
finally:
 for handle in handles:handle.Close()
`;
async function observe(t,pids){
 const child=spawn(pythonExecutable(),['-I','-Xutf8','-B','-c',observerCode,JSON.stringify(pids)],{windowsHide:true,stdio:['pipe','pipe','pipe']});let bytes='',errors='';const messages=[];
 child.stdout.on('data',data=>{bytes+=data;let i;while((i=bytes.indexOf('\n'))>=0){messages.push(JSON.parse(bytes.slice(0,i)));bytes=bytes.slice(i+1);}});child.stderr.on('data',data=>errors+=data);
 const next=async()=>{await until(()=>{assert.equal(child.exitCode,null,errors);return messages.length>0;},'read-only kernel observer');return messages.shift();};
 t.after(async()=>{child.stdin.end();if(child.exitCode===null){await new Promise(resolve=>child.once('exit',resolve));}assert.equal(child.exitCode,0,errors);});
 assert.equal((await next()).ready,true);return async(operation='wait')=>{child.stdin.write(operation+'\n');return (await next()).exited;};
}
async function fixture(t,policy='danger-full-access'){
 const f=await planFixture(t,{jobMode:{},policy}),sid='windows-command-parent';await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});await f.prompt(sid,{kind:'read'});return {...f,sid};
}
const row=(f,id)=>f.call('session.job',{sessionId:f.sid,jobId:id}).then(result=>result.job);
async function done(f,id){await until(async()=>['completed','failed','cancelled','unknown'].includes((await row(f,id)).state),'Windows command settled');return row(f,id);}
async function command(f,{leaderExits=false}={}){
 const childPath=join(f.workspace,'detached child café.cjs'),leaderPath=join(f.workspace,'command leader café.cjs'),record=join(f.workspace,'owned-identities.json'),release=join(f.workspace,'leader-release'),late=join(f.workspace,'unwanted-late-write');const nonce=crypto.randomUUID();
 await writeFile(childPath,'setTimeout(()=>require("node:fs").writeFileSync('+JSON.stringify(late)+',"Unwanted late effect"),10000);setInterval(()=>{},1000);');
 await writeFile(leaderPath,'const fs=require("node:fs"),{spawn}=require("node:child_process");const child=spawn(process.execPath,['+JSON.stringify(childPath)+'],{detached:true,stdio:"ignore"});child.unref();fs.writeFileSync('+JSON.stringify(record)+',JSON.stringify({nonce:'+JSON.stringify(nonce)+',pids:[process.pid,child.pid]}));console.log("owned-command-started");'+(leaderExits?'const timer=setInterval(()=>{if(fs.existsSync('+JSON.stringify(release)+'))clearInterval(timer);},20);':'setInterval(()=>{},1000);'));
 const spec={requestId:crypto.randomUUID(),kind:'shell',task:'"'+process.execPath+'" "'+leaderPath+'"',allowedTools:[],limits:{timeoutMs:30000}};
 const result=await f.call('session.startJob',{sessionId:f.sid,spec});await until(async()=>(await row(f,result.job.id)).output.chunks.some(c=>c.text.includes('owned-command-started')),'actual command stdout');
 const identities=JSON.parse(await readFile(record,'utf8'));assert.equal(identities.nonce,nonce);return {id:result.job.id,spec,pids:identities.pids,release,late};
}
test('actual parent and individual Stop drain detached Windows descendants',windows,async t=>{
 const f=await fixture(t);
 for(const parent of [false,true]){const c=await command(f),exited=await observe(t,c.pids);assert.deepEqual(await exited('poll'),[false,false]);await f.call(parent?'session.cancel':'session.cancelJob',{sessionId:f.sid,...(!parent?{jobId:c.id}:{})});assert.equal((await done(f,c.id)).state,'cancelled');assert.deepEqual(await exited(),[true,true]);await assert.rejects(stat(c.late),{code:'ENOENT'});}
 assert.equal(f.errors(),'');
});
test('leader exit retains capacity and individual Stop drains its surviving Windows descendant',windows,async t=>{
 const f=await fixture(t),c=await command(f,{leaderExits:true}),exited=await observe(t,c.pids);await writeFile(c.release,'Synthetic leader exit');await until(async()=>(await exited('poll'))[0],'held leader exit');assert.deepEqual(await exited('poll'),[true,false]);assert.equal((await row(f,c.id)).state,'running');await f.call('session.cancelJob',{sessionId:f.sid,jobId:c.id});assert.equal((await done(f,c.id)).state,'cancelled');assert.deepEqual(await exited(),[true,true]);await assert.rejects(stat(c.late),{code:'ENOENT'});
});
test('actual Host crash closes the producer lease and recovery never replays the command',windows,async t=>{
 const f=await fixture(t),c=await command(f),exited=await observe(t,c.pids);const count=f.requests.length;await f.crash();assert.deepEqual(await exited(),[true,true]);await f.start();assert.equal((await row(f,c.id)).state,'unknown');const duplicate=await f.call('session.startJob',{sessionId:f.sid,spec:c.spec});assert.equal(duplicate.duplicate,true);assert.equal(duplicate.job.state,'unknown');assert.equal(f.requests.length,count);await assert.rejects(stat(c.late),{code:'ENOENT'});assert.equal(f.errors(),'');
});
test('read-only Windows parent refuses a command before starting a producer',windows,async t=>{
 const f=await fixture(t,'read-only'),path=join(f.workspace,'denied');await assert.rejects(f.call('session.startJob',{sessionId:f.sid,spec:{requestId:'readonly-windows-command',kind:'shell',task:'echo denied > "'+path+'"',allowedTools:[]}}),/Read-only/);assert.equal((await f.call('session.jobs',{sessionId:f.sid})).items.length,0);await assert.rejects(stat(path),{code:'ENOENT'});
});
