// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {existsSync, mkdtempSync, rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {checkAgent} from '../dist/codex-runtime/src/agent-check.js';
import {CodexHost} from '../dist/codex-runtime/src/host.js';
import {ProfileStore} from '../dist/codex-runtime/src/profiles.js';

async function fixture(t, mode='success') {
  const requests=[];
  let announceRequest;
  const firstRequest = new Promise(resolve => {announceRequest = resolve;});
  const server=createServer(async(req,res)=>{
    let raw='';for await(const chunk of req)raw+=chunk;const input=JSON.parse(raw);requests.push(input);
    announceRequest();
    if(mode==='wait'){return;}
    const toolOutput=input.input.find(item=>item.type==='function_call_output');
    const receipt=toolOutput?JSON.stringify(toolOutput.output).match(/[a-f0-9]{48}/)?.[0]:undefined;
    const nonce=JSON.stringify(input.input).match(/nonce ([a-f0-9]{32})/)?.[1];
    const item=mode==='skip'||toolOutput?
      {id:'answer',type:'message',role:'assistant',status:'completed',content:[{type:'output_text',text:mode==='skip'?'OK':receipt??'missing',annotations:[]}]}:
      {id:'tool',type:'function_call',call_id:'probe',name:'augmentor_connection_probe',arguments:JSON.stringify({nonce:mode==='wrong'?'wrong':nonce})};
    res.writeHead(200,{'content-type':'text/event-stream'});
    for(const event of [{type:'response.created',response:{id:'response-'+requests.length,status:'in_progress',output:[]}},
      {type:'response.output_item.added',output_index:0,item},{type:'response.output_item.done',output_index:0,item},
      {type:'response.completed',response:{id:'response-'+requests.length,status:'completed',output:[item]}}])res.write('data: '+JSON.stringify(event)+'\n\n');res.end();
  });await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  t.after(async()=>{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));});
  return {requests,firstRequest,connection:{kind:'local',model:'fixture',endpoint:`http://127.0.0.1:${server.address().port}/v1`}};
}
async function waitForRequest(f) {
  let timer;
  try {
    await Promise.race([f.firstRequest, new Promise((_, reject) => {timer = setTimeout(() => reject(Error('Pinned runtime did not reach the fixture provider')), 5000);})]);
  } finally {clearTimeout(timer);}
}
test('pinned Codex check verifies a synthetic tool receipt with no environment or user state', {timeout:10000}, async t=>{
  const f=await fixture(t);
  assert.deepEqual(await checkAgent(f.connection,AbortSignal.timeout(6000)),{valid:true,validation:'codex-tools',runtime:'0.159.2',toolsVerified:true});
  assert.equal(f.requests.length,2);
  const advertised=JSON.stringify(f.requests[0].tools);
  assert.match(advertised,/augmentor_connection_probe/);
  assert.doesNotMatch(advertised,/exec_command|shell_command|apply_patch|read_file|view_image|spawn_agent|browser_|home_|linux_desktop_/);
  const request=JSON.stringify(f.requests[0]);
  assert.doesNotMatch(request,/Augmentor input mode|Manolo|resonant_voice/);
  const tempPath=request.match(/[^\s"\\]*\/augmentor-codex-check-[a-zA-Z0-9]+/)?.[0];
  assert.ok(tempPath, 'provider context identifies the isolated check directory');
  assert.equal(existsSync(tempPath),false,'temporary state removed');
});
for(const mode of ['skip','wrong'])test(`Codex check rejects ${mode} tool behavior without declaring compatibility`, {timeout:10000},async t=>{
  const f=await fixture(t,mode);await assert.rejects(checkAgent(f.connection,AbortSignal.timeout(6000)),/could not verify/);
  assert.equal(f.requests.length,1);
});
test('Codex check cancellation closes the outstanding provider request without replay', {timeout:10000},async t=>{
  const f=await fixture(t,'wait'),abort=new AbortController();
  const pending=checkAgent(f.connection,abort.signal);
  await waitForRequest(f);
  assert.equal(f.requests.length,1);abort.abort();await assert.rejects(pending,/cancelled or timed out/);assert.equal(f.requests.length,1);
});

async function hostFixture(t, mode = 'success') {
  const f = await fixture(t, mode);
  const root = mkdtempSync(join(tmpdir(), 'codex-check-host-'));
  const profiles = new ProfileStore(join(root, 'profiles.json'), {});
  const profile = {id: 'local', name: 'Fixture model', ...f.connection};
  await profiles.upsert(profile);
  const host = new CodexHost({root, profiles, resolveProfile: id => profiles.resolve(id)});
  t.after(async () => {await host.close(); rmSync(root, {recursive: true, force: true});});
  return {...f, host, profiles, profile};
}

test('host records successful pinned Codex tool evidence without creating a user chat', {timeout:10000}, async t => {
  const f = await hostFixture(t);
  const checked = await f.host.dispatch('profiles.test', {id: 'local', capability: 'agent'});
  assert.equal(checked.scope, 'synthetic-codex-tool');
  assert.equal(checked.toolsVerified, true);
  assert.equal(f.profiles.list()[0].toolsVerified, true);
  assert.deepEqual((await f.host.dispatch('session.list', {})).items, []);
  assert.equal((await f.host.dispatch('host.describe', {})).workers, 0);
});

test('an outstanding tool check fences setup and maintenance, then shutdown cancels without validation or replay', {timeout:10000}, async t => {
  const f = await hostFixture(t, 'wait');
  const pending = f.host.dispatch('profiles.test', {id: 'local', capability: 'agent'});
  const rejected = assert.rejects(pending, /cancelled or timed out/);
  await waitForRequest(f);
  assert.equal(f.requests.length, 1);
  await assert.rejects(f.host.dispatch('profiles.configure', f.profile), /active Codex work/);
  await assert.rejects(f.host.dispatch('profiles.test', {id: 'local', capability: 'agent'}), /in progress/);
  await assert.rejects(f.host.dispatch('host.prepareShutdown', {}), /active or unconfirmed/);
  await f.host.close(); await rejected;
  assert.equal(f.profiles.list()[0].toolsVerified, false);
  assert.equal(f.requests.length, 1);
});
