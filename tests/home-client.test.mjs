// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {once} from 'node:events';
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {homeTool,homeFetch,endpoint} from '../dist/home-client/src/index.js';
async function fixture(t,handler){
 const dir=mkdtempSync(join(tmpdir(),'home-client-'));
 const previous={connection:process.env.AUGMENTOR_HOME_CONNECTION,state:process.env.AUGMENTOR_HOME_CLIENT_STATE};
 process.env.AUGMENTOR_HOME_CONNECTION=join(dir,'home.json');process.env.AUGMENTOR_HOME_CLIENT_STATE=join(dir,'state.db');
 const server=createServer(handler);server.listen(0,'127.0.0.1');await once(server,'listening');
 const connection={url:`http://127.0.0.1:${server.address().port}`,token:'fixture-token-long-enough-only',name:'Test'};
 writeFileSync(process.env.AUGMENTOR_HOME_CONNECTION,JSON.stringify(connection),{mode:0o600});
 t.after(()=>{server.closeAllConnections();server.close();rmSync(dir,{recursive:true,force:true});for(const [key,value] of [['AUGMENTOR_HOME_CONNECTION',previous.connection],['AUGMENTOR_HOME_CLIENT_STATE',previous.state]]){if(value===undefined)delete process.env[key];else process.env[key]=value;}});
 return connection;
}
const json=(res,status,value)=>{res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(value));};
test('Home URL refuses remote cleartext, embedded credentials and URL overrides',()=>{
 for(const url of ['http://nas.local','https://user:secret@example.com','https://example.com/path','https://example.com?key=secret'])assert.throws(()=>endpoint(url));
 assert.equal(endpoint('https://home.example.com'),'https://home.example.com');
});
test('admitted request stays latched if result access is revoked; no second POST',async t=>{
 let asks=0;
 await fixture(t,(req,res)=>{if(req.url==='/ask'){asks++;json(res,202,{status:'accepted'});}else json(res,403,{error:'Access revoked'});});
 const first=await homeTool('home_request',{prompt:'Turn on test lamp'},'session','one');assert.equal(first.status,'unknown');
 const second=await homeTool('home_request',{prompt:'Turn on test lamp'},'session','two');assert.equal(second.request_id,first.request_id);assert.equal(asks,1);
});
test('explicit pre-admission refusal permits a later fresh request',async t=>{
 let asks=0;
 await fixture(t,(req,res)=>{if(req.url==='/ask'){asks++;json(res,asks===1?409:202,asks===1?{error:'busy'}:{status:'accepted'});}else json(res,200,{status:'finished',response:{status:'completed',reply:'done'}});});
 await assert.rejects(homeTool('home_request',{prompt:'test'},'session','one'),/busy/);
 const next=await homeTool('home_request',{prompt:'test'},'session','two');assert.equal(next.status,'completed');assert.equal(asks,2);
});
test('read requests carry authority and the same tool call cannot dispatch twice',async t=>{
 let asks=0,body;
 await fixture(t,async(req,res)=>{if(req.url==='/ask'){asks++;let raw='';for await(const chunk of req)raw+=chunk;body=JSON.parse(raw);json(res,202,{status:'accepted'});}else json(res,200,{status:'finished',response:{status:'completed',reply:'off'}});});
 await homeTool('home_read',{prompt:'Lamp state?'},'session','one');assert.equal(body.read_only,true);
 await homeTool('home_read',{prompt:'Lamp state?'},'session','one');assert.equal(asks,1);
});
test('oversized response is cancelled before JSON parsing',async t=>{
 const connection=await fixture(t,(_req,res)=>{res.writeHead(200);res.end('x'.repeat(1100000));});
 await assert.rejects(homeFetch(connection,'/capabilities'),/too large/);
});
