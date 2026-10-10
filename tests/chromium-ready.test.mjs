// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {once} from 'node:events';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {chromiumPort} from './fixtures/chromium-ready.mjs';
test('empty/partial/invalid Chromium port files cannot pass readiness before an actual page response',async t=>{
 const profile=await mkdtemp(join(tmpdir(),'augmentor-chrome-ready-'));let requests=0,ready=false;
 const server=http.createServer((_,res)=>{requests++;res.writeHead(200,{'content-type':'application/json'}).end(JSON.stringify(ready?[{type:'page',webSocketDebuggerUrl:'ws://authored.invalid/page'}]:[]));});server.listen(0,'127.0.0.1');await once(server,'listening');
 t.after(async()=>{server.closeAllConnections();await new Promise(done=>server.close(done));await rm(profile,{recursive:true,force:true});});
 for(const value of ['', '0\n/devtools/browser/authored\n','65536\n/devtools/browser/authored\n',server.address().port+'\n']){await writeFile(join(profile,'DevToolsActivePort'),value);assert.equal(await chromiumPort(profile),undefined);}
 assert.equal(requests,0);await writeFile(join(profile,'DevToolsActivePort'),server.address().port+'\n/devtools/browser/authored\n');assert.equal(await chromiumPort(profile),undefined);ready=true;assert.equal(await chromiumPort(profile),String(server.address().port));assert.equal(requests,2);
});
