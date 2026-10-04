// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {test} from 'node:test'
import assert from 'node:assert/strict'
import {mkdtempSync,writeFileSync,rmSync,mkdirSync,copyFileSync} from 'node:fs'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {once} from 'node:events'
import {WebSocket} from 'ws'
import {createEmbedServer,nativeConnection} from '../apps/browser/embed/server.mjs'
import {spawn} from 'node:child_process'
const dir=mkdtempSync(join(tmpdir(),'augmentor-embed-test-'));process.env.AUGMENTOR_WORKSPACE_PROFILES=dir;process.env.XDG_STATE_HOME=dir
const profile={id:'fixture',name:'Fixture',preset:'augmentor-fixture',cwd:dir,memory:{person:'fixture-owner',project:dir},parentOrigin:'http://127.0.0.1:9999',publicPath:'/augmentor/',accessTokenFile:join(dir,'token'),legacyPresets:['older-role']}
writeFileSync(profile.accessTokenFile,'x'.repeat(48));writeFileSync(join(dir,'fixture.json'),JSON.stringify(profile));writeFileSync(join(dir,'index.json'),'["fixture"]');process.env.AUGMENTOR_WORKSPACE_PROFILE='fixture'
const {DshBoundary}=await import('../apps/browser/shared/dsh-boundary.mjs')
const {bindProfileMemory}=await import('../services/workspaces/memory.mjs')
test('workspace profile forces role/cwd and rejects outside history, mutation and memory',async()=>{
 const rows=[{sessionId:'inside',agentPreset:profile.preset,cwd:dir},{sessionId:'outside',agentPreset:profile.preset,cwd:'/tmp/elsewhere'},{sessionId:'legacy',agentPreset:'older-role',cwd:dir},{sessionId:'personal',agentPreset:'augmentor-browser-product',cwd:'/tmp/personal'}]
 const b=new DshBoundary(async()=>({items:rows}),async()=>({chatCwd:'/wrong'}))
 assert.deepEqual((await b.sessions()).items.map(r=>r.sessionId),['inside','legacy'])
 assert.deepEqual(await b.guard('session.create',{sessionId:'new',cwd:'/wrong',agentPreset:'wrong'}),{sessionId:'new',cwd:dir,agentPreset:profile.preset})
 for(const method of ['session.history','session.prompt','session.branch','session.resume'])await assert.rejects(b.guard(method,{sessionId:'outside'}),/another/)
 await assert.rejects(b.guard('augmentor/memory',{action:'dual.recall',session:'dsh:personal'}),/another/)
 await assert.rejects(b.guard('session.prompt',{sessionId:'legacy'}),/earlier role/)
 await b.guard('session.history',{sessionId:'legacy'})
 await b.guard('session.resume',{sessionId:'inside'})
 await assert.rejects(b.guard('session.resume',{sessionId:'legacy'}),/earlier role/)
})
test('memory binding supplies dedicated identity and fails closed on a prior personal binding',async()=>{
 let sent;await bindProfileMemory(profile,'dsh:new',undefined,async(method,p)=>{sent=p;return {person:p.person,project:p.project}});assert.equal(sent.person,'fixture-owner');assert.equal(sent.project,dir)
 await assert.rejects(bindProfileMemory(profile,'dsh:old',undefined,async()=>({person:'personal',project:dir})),/different workspace/)
})
test('official service authenticates proxies, serves the same UI and handles >1MiB history without queues',async()=>{
 const fixture=join(dir,'native.mjs');writeFileSync(fixture,`let b=Buffer.alloc(0);process.stdin.on('data',c=>{b=Buffer.concat([b,c]);while(b.length>=4){const n=b.readUInt32LE();if(b.length<n+4)return;const m=JSON.parse(b.subarray(4,n+4));b=b.subarray(n+4);const out=Buffer.from(JSON.stringify({id:m.id,result:'a'.repeat(1200000)}));const h=Buffer.alloc(4);h.writeUInt32LE(out.length);process.stdout.write(Buffer.concat([h,out]));}});`)
 const assetRoot=join(dir,'.managed-release','extension');mkdirSync(assetRoot,{recursive:true});copyFileSync(new URL('../apps/browser/extension/sidepanel.html',import.meta.url),join(assetRoot,'sidepanel.html'))
 let starts=0;const server=createEmbedServer({assetRoot,startNative:(ws,p)=>{starts++;nativeConnection(ws,p,{start:()=>spawn(process.execPath,[fixture],{stdio:['pipe','pipe','ignore']})})}})
 server.listen(0,'127.0.0.1');await once(server,'listening');const base='http://127.0.0.1:'+server.address().port+'/embed/fixture/',headers={authorization:'Bearer '+'x'.repeat(48),origin:profile.parentOrigin}
 try{
 assert.equal((await fetch(base+'sidepanel.html')).status,403)
 assert.equal((await fetch(base+'config.json',{headers:{...headers,origin:'https://evil.invalid'}})).status,403)
 const html=await (await fetch(base+'sidepanel.html',{headers})).text();assert.match(html,/embedded-entry.mjs/);assert.match(html,/sessionspop/)
 assert.equal((await fetch(base+'preferences',{method:'POST',headers:{...headers,'content-type':'application/json'},body:JSON.stringify({set:{'augmentor-session-id':'original'}})})).status,200)
 assert.equal((await (await fetch(base+'preferences',{headers})).json())['augmentor-session-id'],'original')
 const ws=new WebSocket(base.replace('http:','ws:')+'native',{headers});await once(ws,'open');ws.send(JSON.stringify({id:1,method:'session.history'}));const [raw]=await once(ws,'message');assert.equal(JSON.parse(raw).result.length,1200000);ws.close();await once(ws,'close')
 const next=new WebSocket(base.replace('http:','ws:')+'native',{headers});await once(next,'open');next.send(JSON.stringify({type:'embed/ping'}));const [pong]=await once(next,'message');assert.equal(JSON.parse(pong).type,'embed/pong');assert.equal(starts,2);next.close();await once(next,'close')
 }finally{await new Promise(resolve=>server.close(resolve))}
})
test.after(()=>rmSync(dir,{recursive:true,force:true}))
