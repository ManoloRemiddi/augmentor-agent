// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

import {surfaceRequest} from './shared/surface.mjs'
import {homeConnection} from './shared/home.mjs'
import {PiConnection} from '../../dist/client/src/socket.js'
import {promptLibrary} from './shared/prompts.mjs'
import {dshSetup,dshConfiguration} from './shared/dsh-setup.mjs'
import {supportReport} from './shared/support.mjs'
import {startOnboarding} from './shared/onboarding.mjs'
import {memoryRequest} from './shared/memory.mjs'
import {homedir} from 'node:os'
import {join} from 'node:path'
import {AcceptedWork} from './shared/accepted-work.mjs'
import {BrowserVoice,voicePreferences} from './shared/voice-client.mjs'
if(process.env.AUGMENTOR_BROWSER_HARNESS && process.env.AUGMENTOR_BROWSER_HARNESS!=='pi')throw new Error('This bridge supports Pi only.')
const harness='pi'
const preset='augmentor-browser-'+harness
const workspace=join(homedir(),'Augmentor Browser Pi')
const send=value=>{if(process.stdout.destroyed||process.stdout.writableEnded)return;const b=Buffer.from(JSON.stringify(value));if(b.length>1024*1024)throw new Error('Browser response exceeds frame limit');const h=Buffer.alloc(4);h.writeUInt32LE(b.length);process.stdout.write(Buffer.concat([h,b]))}
let connection,opening,selection,currentSession;const interactions=new Map()
const work=new AcceptedWork();let closing
const voice=new BrowserVoice({
  ticket:async()=>{throw Error('Local voice is unavailable with Pi. Choose OpenAI GPT-Live.')},
  submit:async(sessionId,requestId,text)=>{
    if(sessionId!==currentSession)throw Error('The voice conversation changed.')
    const c=await client(),rows=await c.call('session.list')
    if(rows.items.find(row=>row.sessionId===sessionId)?.running)throw Error('Wait for the current Pi task before speaking again.')
    return c.call('session.prompt',{sessionId,requestId,content:[{type:'text',text}]})
  },notify:send,
})
function cleanup(code=0){
  if(code)process.exitCode=code
  else process.exitCode??=0
  if(closing)return closing
  work.close();process.stdin.destroy()
  voice.close()
  closing=(async()=>{await work.drained();await voice.settled();connection?.close();process.stdout.end()})()
  return closing
}
async function client(){if(connection&&!connection.closed)return connection;if(!opening)opening=PiConnection.open(frame=>{
  if(frame.method==='browser/execute'){send(frame.payload);return}
  if(['approval/requested','question/requested'].includes(frame.method)){interactions.set(frame.rpcId,frame.payload.sessionId);send({id:frame.rpcId,method:frame.method.replace('/','.'),params:frame.payload});return}
  if(frame.method==='interaction/resolved'){interactions.delete(frame.payload.rpcId);send({method:'interaction.resolved',params:frame.payload});return}
  if(frame.method==='session/event'){voice.observe(frame.payload.sessionId,frame.payload.event);send({method:'session.event',params:frame.payload});const type=frame.payload.event.type;if(type==='turn/start'||type==='turn/end')send({method:'session.status',params:{sessionId:frame.payload.sessionId,status:type==='turn/start'?'running':'idle'}})}
},()=>{if(!work.closing)void cleanup(1)},harness).then(c=>{connection=c;return c}).finally(()=>opening=null);return opening}
async function attach(sid){if(currentSession!==sid)await voice.close();const c=await client();await c.call('events.subscribe',{sessionId:sid});await c.call('browser.attach',{sessionId:sid});currentSession=sid}
async function request(method,p={},id){
  if(method==='augmentor/voice/preferences'){if(!['get','status',undefined].includes(p.action))await voice.close();return voicePreferences(p)}
  if(method==='augmentor/voice/start'){if(p.sessionId!==currentSession)throw Error('Open the current Pi conversation first.');return voice.start(p)}
  if(method==='augmentor/voice/control')return voice.control(p)
  if(method==='augmentor/dsh')return dshSetup(p)
  if(method==='augmentor/diagnostics')return supportReport()
  if(method==='augmentor/onboarding')return startOnboarding(p)
  if(method==='augmentor/surface'){if(!['appearance','dictation'].includes(p.action))throw Error('Prompt improvement requires DSH');return surfaceRequest(p)}
  if(method==='augmentor/home')return homeConnection(p)
  if(method==='augmentor/memory')return memoryRequest(p)
  if(method==='augmentor/prompts')return promptLibrary(p)
  if(method==='shutdown'){queueMicrotask(()=>void cleanup(0));return {ok:true}}
  const c=await client()
  if(['setup.test','setup.save','setup.cancel'].includes(method))return c.call(method,p,id)
  if(p.sessionId){
    const rows=await c.call('session.list')
    const row=rows.items.find(r=>r.sessionId===p.sessionId)
    if(row&&row.agentPreset!==preset)throw new Error('This browser connection cannot access a Linux chat.')
    if(!row&&method!=='session.create')throw new Error('Browser conversation not found.')
  }
  if(method==='augmentor/models')return c.call('models.list')
  if(method==='initialize'){
    selection={provider:p.provider,model:p.model};await c.call('models.validate',selection)
    const saved=await c.call('chats.saved');return {serverInfo:{home:homedir(),harness,capabilities:{branch:true,edit:true,voice:true},augmentor:{chatCwd:workspace,agentPreset:preset,saved:saved.saved}}}
  }
  if(method==='session.attach'){await attach(p.sessionId);const rows=await c.call('session.list');return {attached:true,running:rows.items.find(r=>r.sessionId===p.sessionId)?.running===true}}
  if(method==='session.create'){const row=await c.call(method,{...p,surface:'browser',selection,cwd:workspace},id);await attach(p.sessionId);return row}
  if(method==='session.prompt'){if(currentSession!==p.sessionId)await attach(p.sessionId);return c.call(method,p,id)}
  if(method==='session.selectModel'){const result=await c.call(method,p,id);selection={provider:p.provider,model:p.model};return result}
  if(method==='session.list'){const result=await c.call(method,p);const items=result.items.filter(r=>r.agentPreset===preset).map(r=>({...r,projections:{values:{title:r.title}}}));return {items,total:items.length}}
  if(method==='session.branch'){const result=await c.call(method,p,id);await attach(result.sessionId);selection=result.selection;return result}
  if(method==='session.history'){const result=await c.call(method,{...p,maxMessages:Math.min(p.maxMessages??50,100)});result.events=result.events.filter(r=>r.event.type!=='assistant/chunk');while(Buffer.byteLength(JSON.stringify(result))>850000&&result.events.length>1){result.events.shift();result.hasMore=true}return result}
  if(['augmentor/save','augmentor/unsave','augmentor/state'].includes(method)){const action=method.split('/')[1];const result=await c.call('chats.saved',{action,sessionId:p.sessionId});return {ok:true,...result}}
  if(['session.cancel','session.rename','session.models','settings.describe','settings.mutate','models.pin'].includes(method))return c.call(method,p,id)
  if(method.startsWith('updates/'))throw new Error('Update this unified installation with its installer.')
  throw new Error('Unsupported harness browser operation: '+method)
}
let buffer=Buffer.alloc(0)
process.stdin.on('data',chunk=>{if(work.closing)return;buffer=Buffer.concat([buffer,chunk]);if(buffer.length>2*1024*1024){void cleanup(1);return}while(buffer.length>=4){const size=buffer.readUInt32LE(0);if(size>1024*1024){void cleanup(1);return}if(buffer.length<size+4)break;let frame;try{frame=JSON.parse(buffer.subarray(4,size+4));}catch{void cleanup(1);return}buffer=buffer.subarray(size+4);
  if(!frame||typeof frame!=='object'||Array.isArray(frame)){void cleanup(1);return}
  if(!frame.method){void work.run(async()=>{const c=await client();if(interactions.has(frame.id)){const sid=interactions.get(frame.id);interactions.delete(frame.id);await c.call('interaction.respond',{rpcId:frame.id,sessionId:sid,value:frame.result??{allow:false}})}else await c.call('browser.respond',{rpcId:frame.id,result:frame.result,error:frame.error?.message})}).catch(()=>{});continue}
  void work.run(()=>request(frame.method,frame.params,frame.id).then(result=>send({id:frame.id,result}),error=>send({id:frame.id,error:{message:error.message}}))).catch(()=>void cleanup(1))
}})
process.stdin.on('end',()=>void cleanup(0));process.on('SIGTERM',()=>void cleanup(0));process.on('SIGINT',()=>void cleanup(130))
process.stdout.on('error',()=>void cleanup(1))
