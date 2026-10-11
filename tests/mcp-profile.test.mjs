// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm,readFile,writeFile,stat} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {pathToFileURL} from 'node:url';
import {once} from 'node:events';
import http from 'node:http';
const {prepareMcpProfile,readMcpProfile,saveMcpProfile}=await import(pathToFileURL(join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),'dist/runtime/src/mcp-profile.js')));
async function fixture(t){const root=await mkdtemp(join(tmpdir(),'augmentor-mcp-profile-'));t.after(()=>rm(root,{recursive:true,force:true}));return root;}
test('valid public registration preparation makes no HTTP request and executes neither stdio nor trusted configuration commands',async t=>{
 const root=await fixture(t),marker=join(root,'must-not-execute');let calls=0;const server=http.createServer((_req,res)=>{calls++;res.end('{}');});server.listen(0,'127.0.0.1');await once(server,'listening');t.after(()=>new Promise(resolve=>server.close(resolve)));
 const document={mcpServers:{web:{url:'http://127.0.0.1:'+server.address().port+'/mcp',exposure:'codemode-deferred'},stdio:{command:process.execPath,args:['-e','require("node:fs").writeFileSync('+JSON.stringify(marker)+',"executed")'],env:{AUTHORED:'!AUTHORED_MUST_NOT_EXECUTE'},enabled:true}},authoredUnrelated:{preserved:true}};
 const prepared=await prepareMcpProfile(JSON.stringify(document),root,root);assert.equal(prepared.servers.size,2);assert.equal(prepared.servers.get('web').exposure,'codemode');assert.equal(calls,0);assert.equal(existsSync(marker),false);assert.equal(prepared.servers.get('stdio').env.AUTHORED,'!AUTHORED_MUST_NOT_EXECUTE');
});
test('profile persistence rechecks the revision after public preparation and enforces formatted byte limits before any write attempt',async t=>{
 const root=await fixture(t),file=join(root,'mcp.json'),before=readMcpProfile(file),prepared=await prepareMcpProfile(JSON.stringify({mcpServers:{},unrelated:'retained'}),root,root);let attempted=false;
 await writeFile(file,JSON.stringify({mcpServers:{},external:'new'}));assert.throws(()=>saveMcpProfile(file,before.revision,prepared,()=>attempted=true),/changed/);assert.equal(attempted,false);assert.equal(JSON.parse(await readFile(file,'utf8')).external,'new');
 let current=readMcpProfile(file);const revision=saveMcpProfile(file,current.revision,prepared,()=>attempted=true);assert.equal(attempted,true);assert.equal(readMcpProfile(file).revision,revision);assert.equal(JSON.parse(await readFile(file,'utf8')).unrelated,'retained');if(process.platform!=='win32')assert.equal((await stat(file)).mode&0o777,0o600);
 const large=await prepareMcpProfile(JSON.stringify({mcpServers:{},unrelated:Array(250000).fill(0)}),root,root);attempted=false;current=readMcpProfile(file);assert.throws(()=>saveMcpProfile(file,current.revision,large,()=>attempted=true),/formatted/);assert.equal(attempted,false);assert.equal(readMcpProfile(file).revision,current.revision);
});
