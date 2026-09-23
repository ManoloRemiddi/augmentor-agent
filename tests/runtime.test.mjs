// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import net from 'node:net';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,existsSync,statSync,appendFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {randomUUID} from 'node:crypto';
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,ms=10000){const end=Date.now()+ms;while(Date.now()<end){if(await fn())return;await delay(20);}throw new Error('Condition timed out');}
class Client {
 pending=new Map();events=[];buffer='';
 constructor(socket){this.socket=socket;socket.setEncoding('utf8');socket.on('data',s=>{this.buffer+=s;let i;while((i=this.buffer.indexOf('\n'))>=0){const frame=JSON.parse(this.buffer.slice(0,i));this.buffer=this.buffer.slice(i+1);if(frame.event)this.events.push(frame.event);else{const p=this.pending.get(frame.id);if(p){this.pending.delete(frame.id);frame.error?p.reject(new Error(frame.error.message)):p.resolve(frame.result);}}}});socket.on('error',()=>{});socket.on('close',()=>{for(const p of this.pending.values())p.reject(new Error('closed'));this.pending.clear();});}
 static async open(path,protocol='augmentor-pi/1'){const socket=net.createConnection(path);await once(socket,'connect');const client=new Client(socket);try{await client.call('host.hello',{protocol});return client;}catch(error){socket.destroy();throw error;}}
 call(method,params={},id=randomUUID()){return new Promise((resolve,reject)=>{this.pending.set(id,{resolve,reject});this.socket.write(JSON.stringify({id,method,params})+'\n');});}
 close(){this.socket.destroy();}
}

test('Pi host protocol, lifecycle, policy and crash recovery', {timeout:120000},async t=>{
 const root=mkdtempSync(join(tmpdir(),'augmentor-pi-contract-'));const config=join(root,'config'),state=join(root,'state'),cwd=join(root,'work');mkdirSync(join(config,'agent'),{recursive:true});mkdirSync(cwd);
 let requests=0;const received=[];
 const mock=http.createServer(async(req,res)=>{let raw='';for await(const chunk of req)raw+=chunk;
  if(req.url!='/v1/chat/completions'){res.writeHead(404).end();return;}
  const body=JSON.parse(raw);
  if(JSON.stringify(body.messages.filter(m=>m.role==='system')).includes('You maintain Augmentor')){
    res.writeHead(200,{'content-type':'text/event-stream'});
    res.end('data: '+JSON.stringify({id:'distill',object:'chat.completion.chunk',model:'test',choices:[{index:0,delta:{role:'assistant',content:JSON.stringify({summary:'',items:[]})},finish_reason:'stop'}]})+'\n\ndata: [DONE]\n\n');return;
  }
  requests++;received.push(body);const user=[...body.messages].reverse().find(m=>m.role==='user')?.content;
  const content=typeof user==='string'?user:JSON.stringify(user);
  if(content.includes('OUTAGE')){res.writeHead(503,{'content-type':'application/json'}).end(JSON.stringify({error:{message:'deliberate model outage'}}));return;}
  res.writeHead(200,{'content-type':'text/event-stream'});
  const chunk=(delta,finish=null)=>res.write('data: '+JSON.stringify({id:'mock',object:'chat.completion.chunk',created:1,model:'test',choices:[{index:0,delta,finish_reason:finish}]})+'\n\n');
  if(content.includes('SLOW')){const timer=setInterval(()=>chunk({content:'tick '}),60);res.on('close',()=>clearInterval(timer));return;}
  const tool=content.includes('DELEGATE_TEST')?'desktop_delegate':content.includes('BROWSER_TEST')?'browser_snapshot':content.includes('CLOCK')||content.includes('SHELL_CHANGE')?'bash':content.includes('WRITE')?'write':content.includes('QUESTION')?'ask_user':content.includes('PACKAGE')?'fixture_probe':null;
  if(tool&&body.messages.at(-1).role!=='tool'){
    const args=tool==='desktop_delegate'?{task:'Inspect the open window.',successCriteria:'Report the title.',constraints:'Do not change anything.'}:tool==='browser_snapshot'?{}:tool==='bash'?{command:content.includes('CLOCK')?"date '+%A, %B %d, %Y %H:%M:%S %Z'":'date > '+join(cwd,'shell-written.txt')}:tool==='write'?{path:join(cwd,'written.txt'),content:'verified π'}:tool==='ask_user'?{question:'Choose a colour',options:['blue','green']}:{};
    chunk({role:'assistant',tool_calls:[{index:0,id:'call_'+requests,type:'function',function:{name:tool,arguments:JSON.stringify(args)}}]});chunk({},'tool_calls');
  }else{chunk({role:'assistant',content:'Verified response π'});chunk({},'stop');}
  res.end('data: [DONE]\n\n');
 });mock.listen(0,'127.0.0.1');await once(mock,'listening');t.after(()=>{mock.closeAllConnections();mock.close();});
 const modelConfig={providers:{test:{baseUrl:`http://127.0.0.1:${mock.address().port}/v1`,api:'openai-completions',apiKey:'dummy',models:[{id:'test',name:'Test',reasoning:false,input:['text'],contextWindow:32000,maxTokens:2048}]}}};
 writeFileSync(join(config,'agent/models.json'),JSON.stringify(modelConfig));
 const env={...process.env,AUGMENTOR_PI_CONFIG:config,AUGMENTOR_PI_STATE:state,AUGMENTOR_SHARED_STATE:join(root,'shared-state'),AUGMENTOR_SHARED_DATA:join(root,'shared-data'),AUGMENTOR_PI_INTERACTION_TIMEOUT:'300',PI_OFFLINE:'1'};
 let child;let stderr='';
 const start=async()=>{child=spawn(process.execPath,['dist/runtime/src/main.js'],{cwd:resolve('.'),env,stdio:['ignore','pipe','pipe']});child.stderr.on('data',b=>stderr+=b);await until(async()=>{assert.equal(child.exitCode,null,stderr);if(!existsSync(join(state,'runtime.sock')))return false;try{const c=await Client.open(join(state,'runtime.sock'));c.close();return true;}catch{return false;}},20000);};
 const stop=async(signal='SIGTERM')=>{if(child&&child.exitCode===null){child.kill(signal);await once(child,'exit');}};
 t.after(()=>{child?.kill('SIGKILL');});await start();let client=await Client.open(join(state,'runtime.sock'));t.after(()=>client.close());
 const selection={provider:'test',model:'test'};
 const create=async(id,policy='workspace-write')=>{const settings=await client.call('settings.describe');await client.call('settings.mutate',{ns:'permission',expectedRevision:settings.namespaces[0].revision,ops:[{op:'set',path:['defaultPreset'],value:policy}]});await client.call('session.create',{sessionId:id,cwd,selection});await client.call('events.subscribe',{sessionId:id});};
 const prompt=(id,content,requestId)=>client.call('session.prompt',{sessionId:id,content:[{type:'text',text:content}]},requestId);
 const idle=async id=>until(async()=>!(await client.call('session.list')).items.find(m=>m.sessionId===id)?.running);
 const latest=(method)=>[...client.events].reverse().find(e=>e.method===method);
 await t.test('protocol rejects incompatible clients and keeps socket private',async()=>{await assert.rejects(Client.open(join(state,'runtime.sock'),'wrong'),/Incompatible/);assert.equal(statSync(join(state,'runtime.sock')).mode&0o777,0o600);});
 await t.test('catalog pins use the native picker contract and missing models never fall back',async()=>{await client.call('models.pin',{...selection,pinned:true});const catalog=await client.call('models.list');assert.deepEqual(catalog.pinned,['test/test']);assert.equal(catalog.groups.find(g=>g.provider==='test').models[0].location,'Local');await assert.rejects(client.call('models.validate',{...selection,model:'missing'}),/unavailable/);assert.equal(requests,0);});
 await t.test('stream, persist, history, rename, save and repeat request deduplication',async()=>{await create('basic');const id=randomUUID();await prompt('basic','hello',id);await idle('basic');assert(client.events.some(e=>e.payload?.event?.type==='assistant/chunk'));const before=requests;await prompt('basic','hello',id);assert.equal(requests,before);await client.call('session.rename',{sessionId:'basic',title:'Renamed'});await client.call('chats.saved',{sessionId:'basic',action:'save'});const row=(await client.call('session.list')).items.find(m=>m.sessionId==='basic');assert.equal(row.title,'Renamed');assert(row.saved);const history=await client.call('session.history',{sessionId:'basic'});assert(history.events.some(e=>e.event.type==='assistant/message'));});
 await t.test('desktop specialist is advertised by Linux Pi and refuses a text-only route before worker inference',async()=>{
  const description=await client.call('host.describe');assert.equal(description.desktopSpecialist.version,'augmentor-computer-use/1');assert.equal(description.desktopSpecialist.coreIntegration,false);
  await create('delegation-eligibility');const before=requests;await prompt('delegation-eligibility','DELEGATE_TEST');await idle('delegation-eligibility');
  const history=await client.call('session.history',{sessionId:'delegation-eligibility'});
  assert(history.events.some(({event})=>event.type==='tool/result'&&event.data.name==='desktop_delegate'&&event.data.isError&&JSON.stringify(event.data).includes('image input')));
  assert.equal(requests-before,2,'Only coordinator requests should run for an ineligible model');
 });
 await t.test('browser sessions use the SDK browser tools and only their attached executor can answer',async()=>{
  await client.call('session.create',{sessionId:'browser-contract',surface:'browser',cwd,selection:{provider:'test',model:'test'}});
  const bridge=await Client.open(join(state,'runtime.sock'));const stranger=await Client.open(join(state,'runtime.sock'));
  try{
   await bridge.call('events.subscribe',{sessionId:'browser-contract'});await bridge.call('browser.attach',{sessionId:'browser-contract'});
   await client.call('session.prompt',{sessionId:'browser-contract',content:[{type:'text',text:'BROWSER_TEST'}]});
   await until(()=>bridge.events.some(e=>e.method==='browser/execute'));
   const request=bridge.events.find(e=>e.method==='browser/execute').payload;
   assert.equal(request.params.action,'snapshot');
   await assert.rejects(stranger.call('browser.respond',{rpcId:request.id,result:{text:'wrong client'}}),/unowned/);
   await bridge.call('browser.respond',{rpcId:request.id,result:{text:'verified browser context'}});await idle('browser-contract');
   assert(received.at(-1).messages.some(m=>m.role==='tool'&&JSON.stringify(m).includes('verified browser context')));
   assert(!received.at(-1).tools.some(t=>t.function.name==='linux_browser_open'));
   assert(!received.at(-1).tools.some(t=>['bash','write','edit','read','ls','find','grep'].includes(t.function.name)));
   await client.call('session.prompt',{sessionId:'browser-contract',content:[{type:'text',text:'WRITE'}]});await idle('browser-contract');
   assert(!existsSync(join(cwd,'written.txt')),'An unadvertised OS tool ran from a browser chat');
  }finally{bridge.close();stranger.close();}
 });
 await t.test('native browser bridge denies Linux history, mutation and attachment',async()=>{
  const bridge=spawn(process.execPath,['apps/browser/pi-bridge.mjs'],{env,stdio:['pipe','pipe','pipe']});
  let buffer=Buffer.alloc(0),serial=0;const pending=new Map();
  bridge.stderr.resume();
  bridge.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4&&buffer.length>=buffer.readUInt32LE(0)+4){const n=buffer.readUInt32LE(0),frame=JSON.parse(buffer.subarray(4,n+4));buffer=buffer.subarray(n+4);pending.get(frame.id)?.(frame);pending.delete(frame.id);}});
  const call=(method,params={})=>new Promise((resolve,reject)=>{const id=String(++serial),b=Buffer.from(JSON.stringify({id,method,params})),h=Buffer.alloc(4);h.writeUInt32LE(b.length);const timer=setTimeout(()=>reject(Error('Bridge did not answer')),5000);pending.set(id,frame=>{clearTimeout(timer);resolve(frame)});bridge.stdin.write(Buffer.concat([h,b]));});
  try{
   await call('initialize',selection);
   for(const method of ['session.history','session.attach','session.prompt','session.cancel','session.rename','session.create']){
    const result=await call(method,{sessionId:'basic',title:'should not change',content:[{type:'text',text:'should not run'}]});
    assert.match(result.error.message,/cannot access a Linux chat/);
   }
   const rows=(await call('session.list')).result;assert.equal(rows.total,rows.items.length);assert(rows.items.every(r=>r.agentPreset==='augmentor-browser-pi'));
   assert((await call('session.history',{sessionId:'browser-contract'})).result.events.length);
   assert.equal((await client.call('session.list')).items.find(r=>r.sessionId==='basic').title,'Renamed');
  }finally{bridge.kill();await once(bridge,'exit');}
 });
 await t.test('prompt create/edit/rename/delete and names cannot escape the directory',async()=>{await client.call('prompts.save',{name:'one',content:'content'});await client.call('prompts.save',{name:'two',original:'one',content:'edited',expectedRevision:(await client.call('prompts.list')).prompts[0].revision});assert.equal((await client.call('prompts.list')).prompts[0].content,'edited');assert(!existsSync(join(config,'agent/prompts/one.md')));await assert.rejects(client.call('prompts.save',{name:'../escape',content:'bad'}),/shortcut name/);await client.call('prompts.delete',{name:'two',expectedRevision:(await client.call('prompts.list')).prompts[0].revision});assert.deepEqual((await client.call('prompts.list')).prompts,[]);});
 await t.test('prompt conflicts preserve edits instead of overwriting another client',async()=>{const first=await client.call('prompts.save',{name:'conflict',content:'first'});const revision=first.prompts.find(p=>p.name==='conflict').revision;await client.call('prompts.save',{name:'conflict',content:'second',expectedRevision:revision});await assert.rejects(client.call('prompts.save',{name:'conflict',content:'lost update',expectedRevision:revision}),/changed/);assert.equal((await client.call('prompts.list')).prompts.find(p=>p.name==='conflict').content,'second');});
 await t.test('read-only blocks a real Pi write tool',async()=>{await create('readonly','read-only');await prompt('readonly','WRITE');await idle('readonly');assert(!existsSync(join(cwd,'written.txt')));});
 await t.test('real Pi bash clock queries need no approval in manual and read-only chats',async()=>{
  for(const policy of ['workspace-write','read-only']){
   const sid='clock-'+policy;await create(sid,policy);client.events=[];await prompt(sid,'CLOCK');await idle(sid);
   assert(!latest('approval/requested'));
   const h=await client.call('session.history',{sessionId:sid});
   const result=h.events.find(e=>e.event.type==='tool/result'&&e.event.data.name==='bash')?.event.data;
   assert(result&&!result.isError,JSON.stringify(result));assert.match(JSON.stringify(result.result),/\d{2}:\d{2}:\d{2}/);
  }
 });
 await t.test('bash with output redirection still needs approval and read-only blocks it',async()=>{
  for(const policy of ['workspace-write','read-only']){
   const sid='shell-'+policy;await create(sid,policy);client.events=[];await prompt(sid,'SHELL_CHANGE');await idle(sid);
   assert.equal(!!latest('approval/requested'),policy==='workspace-write');
   assert(!existsSync(join(cwd,'shell-written.txt')));
   const h=await client.call('session.history',{sessionId:sid});assert(h.events.some(e=>e.event.type==='tool/result'&&e.event.data.isError));
  }
 });
 await t.test('manual approval can deny, expire, and allow actual writes',async()=>{await create('manual');client.events=[];await prompt('manual','WRITE');await until(()=>latest('approval/requested'));let frame=latest('approval/requested');await client.call('interaction.respond',{rpcId:frame.rpcId,sessionId:'manual',value:{outcome:'rejected'}});await idle('manual');assert(!existsSync(join(cwd,'written.txt')));
  client.events=[];await prompt('manual','WRITE');await idle('manual');assert(client.events.some(e=>e.method==='interaction/resolved'));assert(!existsSync(join(cwd,'written.txt')));
  client.events=[];await prompt('manual','WRITE');await until(()=>latest('approval/requested'));frame=latest('approval/requested');await client.call('interaction.respond',{rpcId:frame.rpcId,sessionId:'manual',value:{outcome:'allowed-once'}});await idle('manual');assert.equal(readFileSync(join(cwd,'written.txt'),'utf8'),'verified π');await assert.rejects(client.call('interaction.respond',{rpcId:frame.rpcId,sessionId:'manual',value:{outcome:'allowed-once'}}),/already resolved/);
 });
 await t.test('questions resolve through the Pi extension UI',async()=>{client.events=[];await create('question');await prompt('question','QUESTION');await until(()=>latest('question/requested'));const frame=latest('question/requested');await client.call('interaction.respond',{rpcId:frame.rpcId,sessionId:'question',value:{answer:{answers:[{id:'answer',selected:['blue']}]}}});await idle('question');assert(received.some(b=>b.messages.some(m=>m.role==='tool'&&String(m.content).includes('blue'))));});
 await t.test('two clients cannot execute the same conversation concurrently and Stop settles it',async()=>{await create('concurrent');const other=await Client.open(join(state,'runtime.sock'));try{await prompt('concurrent','SLOW');await until(()=>requests>0);await assert.rejects(other.call('session.branch',{sessionId:'concurrent',newSessionId:'busy-branch',messageSeq:1,mode:'reply'}),/Stop/);await assert.rejects(other.call('session.prompt',{sessionId:'concurrent',content:[{type:'text',text:'other'}]}),/already working/);await client.call('session.cancel',{sessionId:'concurrent'});await idle('concurrent');const h=await client.call('session.history',{sessionId:'concurrent'});assert.equal(h.events.at(-1).event.data.reason.kind,'aborted');}finally{other.close();}});
 await t.test('disconnect while approval is pending denies it without hanging',async()=>{await create('disconnect');client.events=[];await prompt('disconnect','WRITE');await until(()=>latest('approval/requested'));client.close();client=await Client.open(join(state,'runtime.sock'));await idle('disconnect');});
 await t.test('model outage reaches the transcript as an error',async()=>{await create('outage');await prompt('outage','OUTAGE');await idle('outage');const h=await client.call('session.history',{sessionId:'outage'});assert(h.events.some(e=>e.event.type==='runtime/error'));});
 await t.test('branching from an earlier reply preserves Pi context, original chat and policy',async()=>{
  await create('branch-source','read-only');await prompt('branch-source','FIRST_CONTEXT');await idle('branch-source');await prompt('branch-source','LATER_CONTEXT');await idle('branch-source');
  const history=await client.call('session.history',{sessionId:'branch-source'});
  const reply=history.events.find(e=>e.event.type==='assistant/message').event.seq;
  const meta=JSON.parse(readFileSync(join(state,'sessions/branch-source.meta.json'),'utf8'));
  const original=readFileSync(meta.file,'utf8');const before=requests;
  const params={sessionId:'branch-source',newSessionId:'branched',messageSeq:reply,mode:'reply'};
  const branch=await client.call('session.branch',params);assert.equal(branch.sessionId,'branched');assert.equal(requests,before);
  assert.deepEqual(await client.call('session.branch',params),branch);
  assert.equal(readFileSync(meta.file,'utf8'),original);
  assert.deepEqual(await client.call('session.history',{sessionId:'branch-source'}),history);
  assert.equal(JSON.parse(readFileSync(join(state,'sessions/branched.meta.json'),'utf8')).policy,'read-only');
  await client.call('events.subscribe',{sessionId:'branched'});await prompt('branched','FOLLOW_BRANCH');await idle('branched');
  const context=JSON.stringify(received.at(-1).messages);assert(context.includes('FIRST_CONTEXT'));assert(!context.includes('LATER_CONTEXT'));
  await prompt('branched','WRITE');await idle('branched');
  const h=await client.call('session.history',{sessionId:'branched'});assert(h.events.some(e=>e.event.type==='tool/result'&&e.event.data.isError));
 });
 await t.test('editing branches before the latest input, preserving the earlier context',async()=>{
  const h=await client.call('session.history',{sessionId:'branch-source'});const users=h.events.filter(e=>e.event.type==='user/message');
  await assert.rejects(client.call('session.branch',{sessionId:'branch-source',newSessionId:'stale-edit',messageSeq:users[0].event.seq,mode:'edit'}),/latest/);
  await client.call('session.branch',{sessionId:'branch-source',newSessionId:'edited',messageSeq:users.at(-1).event.seq,mode:'edit'});
  await client.call('events.subscribe',{sessionId:'edited'});await prompt('edited','REVISED_CONTEXT');await idle('edited');
  const context=JSON.stringify(received.at(-1).messages);assert(context.includes('FIRST_CONTEXT'));assert(context.includes('REVISED_CONTEXT'));assert(!context.includes('LATER_CONTEXT'));
  assert.deepEqual(await client.call('session.history',{sessionId:'branch-source'}),h);
  const edited=await client.call('session.history',{sessionId:'edited'});assert.equal(edited.events.filter(e=>e.event.type==='user/message').length,2);
 });
 await t.test('editing the first input starts clean; branch target validation never runs a prompt',async()=>{
  await create('first-edit');await prompt('first-edit','FIRST_OLD');await idle('first-edit');
  const h=await client.call('session.history',{sessionId:'first-edit'});const seq=h.events.find(e=>e.event.type==='user/message').event.seq;
  await client.call('session.branch',{sessionId:'first-edit',newSessionId:'first-revised',messageSeq:seq,mode:'edit'});
  await client.call('events.subscribe',{sessionId:'first-revised'});await prompt('first-revised','FIRST_NEW');await idle('first-revised');
  const context=JSON.stringify(received.at(-1).messages);assert(!context.includes('FIRST_OLD'));assert(context.includes('FIRST_NEW'));
  const before=requests;
  for(const patch of [{mode:'wrong'},{messageSeq:99999},{messageSeq:seq,mode:'reply'},{newSessionId:'branch-source'}]){
   await assert.rejects(client.call('session.branch',{sessionId:'first-edit',newSessionId:'invalid-branch',messageSeq:seq,mode:'edit',...patch}));
  }
  assert.equal(requests,before);
 });
 await t.test('branching keeps tool calls and results without executing them again',async()=>{
  const h=await client.call('session.history',{sessionId:'clock-workspace-write'});const seq=h.events.filter(e=>e.event.type==='assistant/message').at(-1).event.seq;
  const before=requests;await client.call('session.branch',{sessionId:'clock-workspace-write',newSessionId:'tools-branch',messageSeq:seq,mode:'reply'});assert.equal(requests,before);
  await client.call('events.subscribe',{sessionId:'tools-branch'});await prompt('tools-branch','CONTINUE_CONTEXT');await idle('tools-branch');
  assert(received.at(-1).messages.some(m=>m.role==='tool'&&/\d{2}:\d{2}:\d{2}/.test(String(m.content))));
 });
 await t.test('crash recovery never resends accepted prompts and Pi session resumes',async()=>{await create('crash');const requestId=randomUUID();await prompt('crash','SLOW',requestId);await delay(100);client.close();const before=requests;await stop('SIGKILL');await start();client=await Client.open(join(state,'runtime.sock'));assert.equal(requests,before);await prompt('crash','SLOW',requestId);assert.equal(requests,before);const h=await client.call('session.history',{sessionId:'crash'});assert.equal(h.events.at(-1).event.data.reason.kind,'interrupted');await client.call('events.subscribe',{sessionId:'basic'});await prompt('basic','resume hello');await idle('basic');assert(received.at(-1).messages.some(m=>m.role==='assistant'&&JSON.stringify(m.content).includes('Verified response')));});
 await t.test('saved branches resume after restart and a cold source can branch',async()=>{
  await client.call('events.subscribe',{sessionId:'edited'});await prompt('edited','AFTER_RESTART');await idle('edited');
  const context=JSON.stringify(received.at(-1).messages);assert(context.includes('FIRST_CONTEXT'));assert(context.includes('REVISED_CONTEXT'));assert(!context.includes('LATER_CONTEXT'));
  const h=await client.call('session.history',{sessionId:'branch-source'});const seq=h.events.find(e=>e.event.type==='assistant/message').event.seq;
  await client.call('session.branch',{sessionId:'branch-source',newSessionId:'cold-branch',messageSeq:seq,mode:'reply'});
  await client.call('events.subscribe',{sessionId:'cold-branch'});await prompt('cold-branch','COLD_FOLLOW');await idle('cold-branch');
  assert(JSON.stringify(received.at(-1).messages).includes('FIRST_CONTEXT'));assert(!JSON.stringify(received.at(-1).messages).includes('LATER_CONTEXT'));
 });
 await t.test('an explicit Pi package loads through the supported resource loader',async()=>{const pkg=join(root,'fixture-package');mkdirSync(pkg);writeFileSync(join(pkg,'package.json'),JSON.stringify({name:'fixture-package',type:'module',pi:{extensions:['./extension.js']}}));writeFileSync(join(pkg,'extension.js'),`export default pi=>pi.registerTool({name:'fixture_probe',label:'Fixture',description:'Return a fixture value',parameters:{type:'object',properties:{}},async execute(){return {content:[{type:'text',text:'PACKAGE_LOADED'}],details:{}};}});`);writeFileSync(join(config,'resources.json'),JSON.stringify({sources:[pkg],skills:[]}));await create('package','danger-full-access');await prompt('package','PACKAGE');await idle('package');assert(received.some(b=>b.messages.some(m=>m.role==='tool'&&String(m.content).includes('PACKAGE_LOADED'))));});
 await t.test('history pagination has stable non-overlapping sequences',async()=>{await create('paging');for(let i=0;i<14;i++){await prompt('paging','page '+i);await idle('paging');}const page=await client.call('session.history',{sessionId:'paging',maxMessages:3});assert(page.hasMore);const earlier=await client.call('session.history',{sessionId:'paging',maxMessages:3,beforeSeq:page.events[0].event.seq});assert(earlier.events.at(-1).event.seq<page.events[0].event.seq);assert.equal(page.events.filter(e=>e.event.type==='user/message').length,3);});
 await t.test('maintenance refuses active tasks and shuts down idle runtime without replay',async()=>{
  await create('maintenance');await prompt('maintenance','SLOW');
  await assert.rejects(client.call('host.shutdown'),/Stop active/);
  assert((await client.call('session.list')).items.find(s=>s.sessionId==='maintenance').running);
  await client.call('session.cancel',{sessionId:'maintenance'});await idle('maintenance');
  const before=requests;const ended=once(child,'exit');
  assert((await client.call('host.shutdown')).accepted);await ended;
  assert.equal(requests,before);assert(!existsSync(join(state,'runtime.sock')));
 });
 client.close();await stop();
});
