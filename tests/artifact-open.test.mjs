// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {HarnessServer} from '../dist/runtime/src/harness-server.js';
test('artifact URLs carry only a bounded snapshot capability and reject expired/altered requests',async t=>{
 const bytes=Buffer.from('<!doctype html><h1>Authored artifact</h1>');let reads=0;
 const server=new HarnessServer({previewFile:async(sid,kind,params,signal)=>{assert.equal(sid,'fixture');assert.equal(kind,'bytes');assert.equal(params.path,'/authored/page.html');signal.throwIfAborted();reads++;return {data:bytes,bytes:bytes.length,version:'authored-version'}}});
 t.after(()=>server.close());await server.start();const grant=await server.publishArtifact('fixture','/authored/page.html',new AbortController().signal);
 assert(!grant.url.includes(server.token));assert.equal(grant.verified,false);assert.equal(reads,1);
 const response=await fetch(grant.url);assert.equal(response.status,200);assert.equal(await response.text(),bytes.toString());assert.equal(response.headers.get('cache-control'),'no-store');assert.equal(response.headers.get('x-content-type-options'),'nosniff');assert.match(response.headers.get('content-security-policy'),/sandbox allow-scripts/);assert.match(response.headers.get('content-security-policy'),/connect-src 'none'/);
 for(const [url,options] of [[grant.url+'?query=1',{}],[grant.url,{method:'POST'}],[grant.url.slice(0,-1)+'x',{}]])assert.equal((await fetch(url,options)).status,404);
 const row=server.artifacts.values().next().value;row.expiresAt=0;assert.equal((await fetch(grant.url)).status,404);
 await assert.rejects(server.publishArtifact('fixture','/authored/program.exe',new AbortController().signal),/HTML or text/);assert.equal(reads,1);
});
