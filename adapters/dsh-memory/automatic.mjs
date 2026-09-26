// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {ownsProductSession,profileForSession,profiles} from '../../services/workspaces/profiles.mjs'
import {profileMemoryCall} from '../../services/workspaces/memory.mjs';
import {randomUUID} from 'node:crypto';
import {DualMemoryClient} from '../../dist/memory/src/dual.js';
const allowed=new Set(['augmentor-linux-product','augmentor-browser-product',...profiles().map(p=>p.preset)]);
const text=content=>typeof content==='string'?content:(content||[]).filter(p=>p.type==='text').map(p=>p.text).join('\n');
const owned=session=>ownsProductSession(session.header);
// Delegated agents and speech can use the GPU inside a tool call. Only known
// ordinary I/O tools open a spare-compute window; unknown tools stay foreground.
const spare=name=>['bash','read','write','edit','glob','grep','web_fetch','web_search'].includes(name)||String(name).startsWith('browser_');

export function applyAutomaticMemory(ctx,{createClient=(session,cwd,profile)=>new DualMemoryClient(session,cwd,profile?profileMemoryCall(profile):undefined,message=>console.warn('[augmentor-memory]',message))}={}){
  const states=new Map();
  function state(session){
    if(!owned(session))return;
    let value=states.get(session.id);
    if(!value){value={client:createClient('dsh:'+session.id,session.header.cwd||'',profileForSession(session.header)),mode:'text',cursor:session.inheritedEventCount||0,voiceCalls:new Set()};states.set(session.id,value);}
    return value;
  }
  function capture(session,liveSeq){
    const s=state(session);if(!s)return;
    const events=[];
    // Read committed events, not speculative streaming chunks. Backfill after a
    // crash/reconnect; inherited fork history is never counted as a new moment.
    for(const e of session.snapshotEvents(s.cursor)){
      s.cursor=e.seq+1;
      const d=e.data;
      const live=e.seq===liveSeq;
      if(e.type==='user/message'&&d.source?.kind==='user'){
        s.mode=String(d.source.rpcId||'').startsWith('resonant-voice:')?'voice':'text';
        const content=text(d.content);if(content.trim())events.push({id:String(e.seq),role:'user',mode:s.mode,content,live});
      }
      if(e.type==='assistant/message'){
        const content=text(d.message?.content);if(content.trim())events.push({id:String(e.seq),role:'assistant',mode:s.mode,content,status:d.interrupted?'interrupted':'complete',live});
      }
      if(e.type==='tool/call'&&d.name==='resonant_voice_reply')s.voiceCalls.add(d.callId);
      if(e.type==='tool/result'&&s.voiceCalls.has(d.message?.source?.callId)){
        s.voiceCalls.delete(d.message.source.callId);
        const result=d.message.content?.find(p=>p.type==='tool-result');
        const content=text(result?.content);
        if(result&&!result.isError&&content.trim())events.push({id:String(e.seq),role:'assistant',mode:'voice',content,live});
      }
    }
    if(events.length)void s.client.append(events);
    return s;
  }
  ctx.on('session/event',(session,event)=>{if(owned(session)){
    if(event.type==='user/message'&&event.data.source?.kind==='user')void state(session).client.activity('foreground');
    const s=capture(session,event.seq);
    if(event.type==='tool/call')void s.client.activity(spare(event.data.name)?'tools':'foreground');
  }});
  ctx.on('session/flush',async session=>{if(owned(session)){const s=capture(session);await s?.client.flush();}});
  ctx.on('agent/pre-step',async({agent,messages,signal},next)=>{
    const decision=await next();if(decision.kind==='reject'||!owned(agent.session))return decision;
    await state(agent.session).client.activity('foreground');
    const s=capture(agent.session);
    const human=messages.filter(m=>m.source?.kind==='user').at(-1);
    if(!human||agent.session.header.parentSession||agent.session.header.isSeeded)return decision;
    const mode=String(human.source.rpcId||'').startsWith('resonant-voice:')?'voice':'text';
    const context=await s.client.recall(mode,text(human.content));
    if(signal?.aborted)return decision;
    // Surface replacement is a supported DSH operation. Preserve the append-only
    // log while removing earlier memory payloads from effective model input.
    const session=agent.session;
    const previous=[...session.surface.nodes].map(seq=>session.eventAt(seq)).filter(e=>
      e?.type==='user/message'&&e.data.source?.kind==='plugin'&&e.data.source.plugin==='augmentor-memory');
    const message=content=>({id:randomUUID(),role:'user',content:[{type:'text',text:content}],source:{kind:'plugin',plugin:'augmentor-memory'}});
    const active=previous.filter(event=>text(event.data.content)!=='Earlier continuity superseded.');
    if(active.length===1&&text(active[0].data.content)===context)return decision;
    for(const event of active){
      session.append('user/message',message('Earlier continuity superseded.'),{surfaceOp:{op:'replace',startSeq:event.seq,endSeq:event.seq},sourceEventSeqs:[event.seq]});
    }
    // Put the new snapshot beside the new request. Rewriting a permanent early
    // slot would invalidate almost the entire model prefix cache on every turn.
    return context?{...decision,messages:[message(context),...decision.messages]}:decision;
  });
  ctx.on('agent/status',({agent,status})=>{if(owned(agent.session)){
    const s=capture(agent.session);void s.client.activity(status==='running'?'foreground':'stop');
  }});
  ctx.on('agent/disposed',({agent})=>{states.get(agent.id)?.client.close();states.delete(agent.id);});
  ctx.on('dispose',()=>{for(const s of states.values())s.client.close();states.clear();});
}
