// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {mkdtempSync, mkdirSync, rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {CodexRpc} from '../dist/codex-runtime/src/rpc.js';
import {runtimeOptions} from '../dist/codex-runtime/src/config.js';
import {nativeHistory} from '../dist/codex-runtime/src/history.js';
import {branchBoundary, verifyBranchHistory} from '../dist/codex-runtime/src/branch.js';
import {chatEvents} from '../dist/codex-runtime/src/events.js';

test('pinned forks retain exact turn boundaries and tools across independent workers in one native store', {timeout: 20000}, async t => {
  const root=mkdtempSync(join(tmpdir(),'codex-fork-')),state=join(root,'state'),clients=[],requests=[];
  mkdirSync(state,{mode:0o700});let toolCalls=0;
  const server=createServer(async(req,res)=>{
    let raw='';for await(const chunk of req)raw+=chunk;requests.push(JSON.parse(raw));
    const number=requests.length;
    const item=number===1?{id:'tool-item',type:'function_call',call_id:'tool-call',name:'fixture_tool',arguments:'{}'}:
      {id:'answer-'+number,type:'message',role:'assistant',status:'completed',content:[{type:'output_text',text:'Fixture answer '+number,annotations:[]}]};
    res.writeHead(200,{'content-type':'text/event-stream'});
    for(const frame of [{type:'response.created',response:{id:'r'+number,status:'in_progress',output:[]}},{type:'response.output_item.added',output_index:0,item},{type:'response.output_item.done',output_index:0,item},{type:'response.completed',response:{id:'r'+number,status:'completed',output:[item]}}])res.write('data: '+JSON.stringify(frame)+'\n\n');
    res.end();
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  t.after(async()=>{for(const client of clients)await client.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));rmSync(root,{recursive:true,force:true});});
  const connection={kind:'local',model:'fixture',endpoint:`http://127.0.0.1:${server.address().port}/v1`};
  async function open(){
    const rpc=new CodexRpc({...runtimeOptions(connection,state,root),experimentalApi:true});clients.push(rpc);await rpc.initialize();
    rpc.on('request',request=>{assert.equal(request.method,'item/tool/call');toolCalls++;rpc.respond(request.id,{success:true,contentItems:[{type:'inputText',text:'SYNTHETIC_TOOL_RESULT'}]});});
    return rpc;
  }
  async function turn(rpc,threadId,text){
    const completed=Promise.withResolvers();
    const handler=frame=>{if(frame.method==='turn/completed'&&frame.params.threadId===threadId){rpc.off('notification',handler);completed.resolve(frame.params.turn);}};
    rpc.on('notification',handler);
    const result=await rpc.call('turn/start',{threadId,clientUserMessageId:text,input:[{type:'text',text}]});
    assert.equal((await completed.promise).status,'completed');return result.turn.id;
  }
  const parent=await open();
  const {thread}=await parent.call('thread/start',{cwd:root,developerInstructions:'SYNTHETIC_FORK_PERSONA',dynamicTools:[{name:'fixture_tool',description:'Synthetic fixture tool',inputSchema:{type:'object',properties:{}}}]});
  const first=await turn(parent,thread.id,'SYNTHETIC_FIRST_TURN');
  const second=await turn(parent,thread.id,'SYNTHETIC_LATER_TURN');
  assert.equal(toolCalls,1);
  const source=await nativeHistory(parent,thread.id,1);
  function boundary(turnIndex,itemIndex,mode){
    const turn=source[turnIndex],item=turn.items[itemIndex];
    const [event]=chatEvents({method:'item/completed',params:{threadId:thread.id,turnId:turn.id,item}});
    return branchBoundary(source,{...event,seq:1},mode);
  }
  const replyBoundary=boundary(0,source[0].items.length-1,'reply');
  const editBoundary=boundary(1,0,'edit');
  const emptyBoundary=boundary(0,0,'edit');
  const creator=await open();
  const fork=await creator.call('thread/fork',{threadId:thread.id,...replyBoundary.params,excludeTurns:true,deferGoalContinuation:true});
  const edit=await creator.call('thread/fork',{threadId:thread.id,...editBoundary.params,excludeTurns:true,deferGoalContinuation:true});
  const empty=await creator.call('thread/fork',{threadId:thread.id,...emptyBoundary.params,excludeTurns:true,deferGoalContinuation:true});
  verifyBranchHistory(emptyBoundary,await nativeHistory(creator,empty.thread.id));
  assert.equal(requests.length,3,'fork creation does not invoke inference');
  assert.equal(toolCalls,1,'fork creation does not repeat actions');
  for(const value of [fork,edit]) {
    const history=await nativeHistory(parent,value.thread.id,1);
    verifyBranchHistory(value===fork?replyBoundary:editBoundary,history);
    assert.deepEqual(history.map(turn=>turn.id),[first]);
    assert.ok(history[0].items.some(item=>item.type==='dynamicToolCall'));
  }
  await creator.close();
  const child=await open(); // Concurrent independent app-server, same supported native store.
  await child.call('thread/resume',{threadId:fork.thread.id,excludeTurns:true});
  await turn(child,fork.thread.id,'SYNTHETIC_CHILD_TURN');
  assert.match(JSON.stringify(requests.at(-1).input),/SYNTHETIC_TOOL_RESULT/);
  assert.doesNotMatch(JSON.stringify(requests.at(-1).input),/SYNTHETIC_LATER_TURN/);
  assert.match(JSON.stringify(requests.at(-1)),/SYNTHETIC_FORK_PERSONA/);
  assert.ok(requests.at(-1).tools.some(tool=>tool.name==='fixture_tool'));
  await child.call('thread/resume',{threadId:empty.thread.id,excludeTurns:true});
  await turn(child,empty.thread.id,'SYNTHETIC_EDITED_FIRST');
  assert.doesNotMatch(JSON.stringify(requests.at(-1).input),/SYNTHETIC_FIRST_TURN|SYNTHETIC_LATER_TURN|SYNTHETIC_TOOL_RESULT/);
  assert.ok(requests.at(-1).tools.some(tool=>tool.name==='fixture_tool'));
  assert.equal(toolCalls,1);
  assert.deepEqual((await nativeHistory(parent,thread.id)).map(turn=>turn.id),[first,second]);
  await child.close();const restarted=await open();
  await restarted.call('thread/resume',{threadId:fork.thread.id,excludeTurns:true});
  assert.equal((await nativeHistory(restarted,fork.thread.id)).length,2);
});

test('host branches preserve native ownership, retry identity and independent histories after restart', {timeout:30000}, async t=>{
  const {CodexHost}=await import('../dist/codex-runtime/src/host.js');
  const root=mkdtempSync(join(tmpdir(),'codex-host-fork-')),hosts=[],requests=[];
  let forkCalls=0,loseForkReply=false,corruptForkHistory=false,profileRevision=1;
  const server=createServer(async(req,res)=>{
    let raw='';for await(const chunk of req)raw+=chunk;requests.push(JSON.parse(raw));
    const item={id:'answer-'+requests.length,type:'message',role:'assistant',status:'completed',content:[{type:'output_text',text:'Answer '+requests.length,annotations:[]}]};
    res.writeHead(200,{'content-type':'text/event-stream'});
    for(const frame of [{type:'response.created',response:{id:'r',status:'in_progress',output:[]}},{type:'response.output_item.added',output_index:0,item},{type:'response.output_item.done',output_index:0,item},{type:'response.completed',response:{id:'r',status:'completed',output:[item]}}])res.write('data: '+JSON.stringify(frame)+'\n\n');
    res.end();
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  t.after(async()=>{for(const host of hosts)await host.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));rmSync(root,{recursive:true,force:true});});
  const connection={kind:'local',model:'fixture',endpoint:`http://127.0.0.1:${server.address().port}/v1`};
  function open(){
    const host=new CodexHost({root:join(root,'host'),maxWorkers:8,resolveProfile:async id=>({id,revision:profileRevision,connection}),createRpc:options=>{
      const rpc=new CodexRpc(options),call=rpc.call.bind(rpc);let isCreator=false;
      rpc.call=async(method,params)=>{
        if(method==='thread/fork'){forkCalls++;isCreator=true;}
        const result=await call(method,params);
        if(method==='thread/fork'&&loseForkReply)throw Error('Synthetic lost fork acknowledgment');
        if(isCreator&&corruptForkHistory&&method==='thread/turns/list')result.data[0].status='interrupted';
        return result;
      };
      return rpc;
    }});hosts.push(host);return host;
  }
  let host=open();
  async function prompt(id,text){
    const done=Promise.withResolvers();
    const handler=(sessionId,frame)=>{if(sessionId===id&&frame.payload?.event?.type==='turn/end'){host.off('event',handler);done.resolve();}};
    host.on('event',handler);
    await host.dispatch('session.prompt',{sessionId:id,requestId:text,content:[{type:'text',text}]});await done.promise;
  }
  const history=id=>host.dispatch('session.history',{sessionId:id,maxMessages:100});
  await host.create({sessionId:'parent',profileId:'fixture',cwd:root});
  await prompt('parent','SYNTHETIC_SOURCE_FIRST');await prompt('parent','SYNTHETIC_SOURCE_SECOND');
  await host.dispatch('session.cancel',{sessionId:'parent'});
  await host.dispatch('session.prompt',{sessionId:'parent',requestId:'paused-followup',content:[{type:'text',text:'SYNTHETIC_PARENT_QUEUE'}]});
  const before=await history('parent');
  const events=before.events.map(entry=>entry.event);
  assert.ok(Array.isArray(events),JSON.stringify(before));
  const reply=events.find(event=>event.type==='assistant/message'),user=events.find(event=>event.type==='user/message');
  const params={sessionId:'parent',newSessionId:'child',messageSeq:reply.seq,mode:'reply'};
  const first=host.dispatch('session.branch',params),duplicate=host.dispatch('session.branch',params);
  assert.equal((await host.dispatch('session.branchStatus',{newSessionId:'child'})).status,'creating');
  assert.equal((await host.dispatch('session.branchStatus',{newSessionId:'missing'})).status,'absent');
  await assert.rejects(host.dispatch('session.prompt',{sessionId:'parent',requestId:'blocked',content:[{type:'text',text:'must not enter source'}]}),/branch/);
  await assert.rejects(host.dispatch('host.prepareShutdown',{}),/active/);
  const [child,repeated]=await Promise.all([first,duplicate]);assert.deepEqual(child,repeated);assert.equal(forkCalls,1);
  assert.equal(requests.length,2);
  assert.equal((await host.dispatch('session.queue',{sessionId:'parent'})).items.length,1);
  assert.equal((await host.dispatch('session.queue',{sessionId:'child'})).operations.length,0);
  await host.dispatch('session.branch',params);assert.equal(forkCalls,1);
  assert.equal((await host.dispatch('session.branchStatus',{newSessionId:'child'})).status,'ready');
  await assert.rejects(host.dispatch('session.branch',{...params,messageSeq:user.seq,mode:'edit'}),/different request/);
  assert.deepEqual(await history('parent'),before);
  assert.doesNotMatch(JSON.stringify(await history('child')),/SYNTHETIC_SOURCE_SECOND/);
  await prompt('child','SYNTHETIC_CHILD');
  assert.match(JSON.stringify(requests.at(-1).input),/SYNTHETIC_SOURCE_FIRST/);
  assert.doesNotMatch(JSON.stringify(requests.at(-1).input),/SYNTHETIC_SOURCE_SECOND/);
  const childHistory=await history('child');
  await host.dispatch('session.branch',{sessionId:'parent',newSessionId:'empty',messageSeq:user.seq,mode:'edit'});
  await prompt('empty','SYNTHETIC_EDIT');
  assert.doesNotMatch(JSON.stringify(requests.at(-1).input),/SYNTHETIC_SOURCE_FIRST|SYNTHETIC_SOURCE_SECOND/);
  await host.close();host=open();
  await host.dispatch('session.create',{sessionId:'child',profileId:'fixture',cwd:root});
  assert.deepEqual(await history('child'),childHistory);
  const childMeta=await host.dispatch('session.describe',{sessionId:'child'});assert.equal(childMeta.nativeOwner,'parent');
  const childEvents=childHistory.events.map(entry=>entry.event);
  await host.dispatch('session.branch',{sessionId:'child',newSessionId:'grandchild',messageSeq:childEvents.filter(event=>event.type==='assistant/message').at(-1).seq,mode:'reply'});
  assert.equal((await host.dispatch('session.describe',{sessionId:'grandchild'})).nativeOwner,'parent');
  profileRevision=2;
  await assert.rejects(host.dispatch('session.branch',{...params,newSessionId:'wrong-profile'}),/profile changed/);
  profileRevision=1;corruptForkHistory=true;
  await assert.rejects(host.dispatch('session.branch',{...params,newSessionId:'mismatch'}),/history differs/);
  const mismatch=await host.dispatch('session.describe',{sessionId:'mismatch'});
  assert.equal(mismatch.status,'creating');assert.ok(mismatch.threadId);
  const beforeMismatchRetry=forkCalls;
  await assert.rejects(host.dispatch('session.branch',{...params,newSessionId:'mismatch'}),/unknown outcome/);
  assert.equal(forkCalls,beforeMismatchRetry);
  corruptForkHistory=false;loseForkReply=true;
  await assert.rejects(host.dispatch('session.branch',{...params,newSessionId:'unknown'}),/lost fork/);
  const calls=forkCalls;
  await assert.rejects(host.dispatch('session.branch',{...params,newSessionId:'unknown'}),/unknown outcome/);
  await host.close();host=open();
  await assert.rejects(host.dispatch('session.branch',{...params,newSessionId:'unknown'}),/unknown outcome/);
  assert.equal(forkCalls,calls,'an uncertain fork is never repeated');
});

test('native Qt transcript Branch/Edit and Enter create exact children through the host', {timeout:30000},async t=>{
  const {CodexHost}=await import('../dist/codex-runtime/src/host.js');
  const {CodexIpcServer}=await import('../dist/codex-runtime/src/ipc.js');
  const {spawn}=await import('node:child_process');
  const {fileURLToPath}=await import('node:url');
  const root=mkdtempSync(join(process.platform==='darwin'?'/tmp':tmpdir(),'codex-ui-fork-')),requests=[];
  const server=createServer(async(req,res)=>{
    let raw='';for await(const chunk of req)raw+=chunk;requests.push(JSON.parse(raw));
    const item={id:'answer-'+requests.length,type:'message',role:'assistant',status:'completed',content:[{type:'output_text',text:'Native answer '+requests.length,annotations:[]}]};
    res.writeHead(200,{'content-type':'text/event-stream'});
    for(const frame of [{type:'response.created',response:{id:'r',status:'in_progress',output:[]}},{type:'response.output_item.added',output_index:0,item},{type:'response.output_item.done',output_index:0,item},{type:'response.completed',response:{id:'r',status:'completed',output:[item]}}])res.write('data: '+JSON.stringify(frame)+'\n\n');
    res.end();
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const host=new CodexHost({root:join(root,'host'),resolveProfile:async id=>({id,revision:1,connection:{kind:'local',model:'fixture',endpoint:`http://127.0.0.1:${server.address().port}/v1`}})});
  const ipc=new CodexIpcServer(host,join(root,'host.sock'));let child;
  t.after(async()=>{if(child&&child.exitCode===null&&child.signalCode===null)child.kill('SIGKILL');await ipc.close();await host.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));rmSync(root,{recursive:true,force:true});});
  await ipc.listen();await host.create({sessionId:'native-fork-source',profileId:'fixture',cwd:root});
  for(const text of ['NATIVE_SOURCE_FIRST','NATIVE_SOURCE_SECOND']){
    const done=Promise.withResolvers();const listener=(id,frame)=>{if(id==='native-fork-source'&&frame.payload?.event?.type==='turn/end'){host.off('event',listener);done.resolve();}};
    host.on('event',listener);
    await host.dispatch('session.prompt',{sessionId:'native-fork-source',requestId:text,content:[{type:'text',text}]});await done.promise;
  }
  const home=join(root,'ui-home');mkdirSync(home,{mode:0o700});
  child=spawn(process.env.AUGMENTOR_PYTHON??'python3',[fileURLToPath(new URL('./fixtures/codex/native-fork.py',import.meta.url))],{env:{...process.env,HOME:home,XDG_CONFIG_HOME:join(home,'config'),XDG_DATA_HOME:join(home,'data'),XDG_STATE_HOME:join(home,'state'),AUGMENTOR_WINDOW_ID:'main',AUGMENTOR_CODEX_STATE:join(root,'host'),AUGMENTOR_CODEX_SOCKET:ipc.socketPath,AUGMENTOR_CODEX_NO_AUTOSTART:'1',PYTHONPATH:fileURLToPath(new URL('../apps/native',import.meta.url)),QT_QPA_PLATFORM:'offscreen'},stdio:['ignore','pipe','pipe']});
  let output='',errors='';child.stdout.on('data',chunk=>output+=chunk);child.stderr.on('data',chunk=>errors+=chunk);
  const code=await new Promise((resolve,reject)=>{child.on('error',reject);child.on('exit',resolve);});
  assert.equal(code,0,errors);assert.match(output,/"nativeFork": "passed"/);
  assert.equal(requests.length,3,'only original turns and explicit edited input run inference');
  assert.match(JSON.stringify(requests[2].input),/NATIVE_EDITED_FIRST/);
  assert.doesNotMatch(JSON.stringify(requests[2].input),/NATIVE_SOURCE_FIRST|NATIVE_SOURCE_SECOND|RESTORED_DRAFT/);
});
