// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID, createHash} from 'node:crypto';
import {mkdirSync, writeFileSync, renameSync} from 'node:fs';
import {join} from 'node:path';
import {homedir} from 'node:os';
import {actionKey,actionEffect,actionOutcome,recoveryDenial} from './actions.mjs';

export const name = 'augmentor-execution';
export const inject = ['tools'];
const presets = new Set(['augmentor-linux-product', 'augmentor-browser-product']);
const owned = agent => presets.has(agent.session.header.agentPreset) && agent.session.header.origin !== 'subagent';
const source = {kind:'plugin', plugin:name};
const message = text => ({id:randomUUID(), role:'user', source, content:[{type:'text', text}]});

export function policy(raw = {}) {
  const c = {maxRecoveries:2, recoveryMaxTokens:8192, recoveryMaxSteps:64, recoveryMaxMs:600000,
    warningMs:90000, recoveryRoutes:[], ...raw};
  for (const key of ['maxRecoveries','recoveryMaxTokens','recoveryMaxSteps','recoveryMaxMs','warningMs'])
    if (!Number.isSafeInteger(c[key]) || c[key] <= 0) throw Error(`Invalid execution policy: ${key}`);
  if (!Array.isArray(c.recoveryRoutes) || c.recoveryRoutes.some(r => !r.provider || !r.model || !r.effort))
    throw Error('Recovery effort requires exact provider/model routes');
  return c;
}

// Only metadata is saved. Never add private diagnostic event types to DSH's
// replay log: 0.1.5 rejects unknown required types on a cold history load.
function save(session, value) {
  try {
    const folder=join(process.env.AUGMENTOR_EXECUTION_STATE || join(homedir(),'.local/state/augmentor'), 'execution');
    mkdirSync(folder,{recursive:true, mode:0o700});
    const dest=join(folder,createHash('sha256').update(session.id).digest('hex')+'.json');
    const tmp=dest+'.'+randomUUID()+'.tmp';
    writeFileSync(tmp,JSON.stringify(value),{mode:0o600}); renameSync(tmp,dest);
  } catch { /* Optional diagnostics must not break task execution. */ }
}

export function apply(ctx, raw = {}) { return install(ctx, policy(raw)); }
export function install(ctx, c, {now=Date.now, persist=save} = {}) {
  const states=new Map();
  const state=agent => {
    let s=states.get(agent.id);
    if (!s) {
      const pending=new Set();
      for(const e of agent.session.snapshotEvents()) {
        if(e.type==='tool/call')pending.add(e.data.callId);
        if(e.type==='tool/result')pending.delete(e.data.message?.source?.callId);
      }
      s={turn:0, recoveries:0, pending, actions:new Map(), denied:new Set(), toolHandoff:false, requests:[], lastActionAt:now(), outcome:'running'}; states.set(agent.id,s);
    }
    return s;
  };
  const record=(agent,s) => persist(agent.session,{version:1, turn:s.turn, outcome:s.outcome,
    recoveries:s.recoveries, recoverySteps:s.recoverySteps||0, lastActionAt:s.lastActionAt,
    recoveryCause:s.recoveryCause??null, incompleteReason:s.incompleteReason??null,
    pendingToolCount:s.pending.size, actionOutcomes:[...s.actions.values()].map(({status,effect})=>({status,effect})),
    requests:s.requests.slice(-128), updatedAt:now()});
  const notice=(agent,s,text) => {
    // Standard UI-only status record: no invented model response, no extra
    // model context and no ingestion into long-term conversational memory.
    agent.session.append('command/done',{commandId:randomUUID(),
      kind:s.outcome==='incomplete'?'error':'success',text:'Harness: '+text});
  };
  const exhausted=s => s.recoveryAt && (now()-s.recoveryAt>=c.recoveryMaxMs || s.recoverySteps>=c.recoveryMaxSteps);
  const stop=(agent,s,reason) => {
    if (s.outcome==='incomplete') return;
    s.outcome='incomplete'; s.blocked=true; s.incompleteReason=reason;
    notice(agent,s,`Task incomplete. ${reason} Confirmed tool results remain in this conversation; no uncertain action was replayed. Review the saved progress before resuming.`);
    record(agent,s);
  };
  ctx.on('tools/pre-execute',async(exec,next)=>{
    const decision=await next();
    if(!exec.agent||!owned(exec.agent)||exec.signal.aborted||decision.kind!=='allow')return decision;
    const s=state(exec.agent);
    if(!s.recoveryAt)return decision;
    const effect=actionEffect(exec.name,exec.arguments,ctx.tools.get(exec.name,exec.agent));
    const key=actionKey(exec.name,exec.arguments);
    const reason=s.blocked?'Recovery has stopped.':recoveryDenial(s.actions,key,effect);
    if(reason) {
      s.denied.add(exec.token);s.guardDenials++;
      if(s.guardDenials>=2)stop(exec.agent,s,'Recovery repeatedly requested an unsafe duplicate or unresolved action.');
      return {kind:'deny',reason};
    }
    // Reserve before dispatch so parallel siblings cannot both pass the gate.
    if(effect!=='read')s.actions.set(key,{effect,status:'running'});
    return decision;
  });
  ctx.on('tools/result',(exec,result)=>{
    if(!exec.agent||!owned(exec.agent))return;
    const s=state(exec.agent),definition=ctx.tools.get(exec.name,exec.agent);
    const effect=actionEffect(exec.name,exec.arguments,definition),key=actionKey(exec.name,exec.arguments);
    // A guard denial must not overwrite the outcome of the original action.
    if(s.denied.delete(exec.token))return;
    const outcome=actionOutcome(exec,result,definition,effect);
    if(outcome.jobId&&exec.name==='job_output')for(const action of s.actions.values())
      if(action.jobId===outcome.jobId)action.status=outcome.status;
    s.actions.set(key,{...outcome,effect});
    if(result.concludesTurn)s.toolHandoff=true;
    record(exec.agent,s);
  });
  ctx.on('session/event',(session,e)=>{
    const s=states.get(session.id); if (!s) return;
    // Pruned/replaced context is historical evidence, not a new response or action.
    if(e.surfaceOp?.op==='replace')return;
    const d=e.data;
    if(e.type==='tool/call')s.pending.add(d.callId);
    if(e.type==='tool/result') {s.pending.delete(d.message?.source?.callId);s.lastActionAt=now();s.lastToolSeq=e.seq;}
    if(e.type==='assistant/message' && d.message?.source?.kind==='model') {
      const blocks=d.message.content||[];
      s.last={seq:e.seq, stop:d.message.source.replayState?.response?.stopReason,
        truncated:(d.stream||[]).some(x=>x.type==='chunk'&&x.chunk?.type==='finish'&&x.chunk.reason?.kind==='max-tokens'),
        tools:blocks.some(x=>x.type==='tool-call'), text:blocks.some(x=>x.type==='text'&&x.text?.trim()),
        interrupted:!!d.interrupted};
      const request=s.requests.at(-1);
      if(request)Object.assign(request,{durationMs:now()-request.startedAt,outputTokens:d.usage?.outputTokens,
        inputTokens:d.usage?.inputTokens,cacheReadTokens:d.usage?.cacheReadTokens,stopReason:s.last.stop});
      record({session},s);
    }
    if(e.type==='turn/end') {
      clearTimeout(s.timer);s.timer=undefined;s.removeAbort?.();
      if(d.reason?.kind==='aborted')s.outcome='cancelled';
      else if(['error','blocked'].includes(d.reason?.kind))s.outcome='incomplete';
      else if(s.outcome==='running')s.outcome=d.reason?.kind==='completed'?'response-produced':'incomplete';
      record({session},s);
    }
  });
  ctx.on('agent/pre-step',async({agent,turn,signal},next)=>{
    const decision=await next(); if(!owned(agent)||signal.aborted||decision.kind==='reject')return decision;
    const s=state(agent);
    if(s.turn!==turn) {
      clearTimeout(s.timer);
      Object.assign(s,{turn,recoveries:0,recoveryAt:0,recoverySteps:0,blocked:false,last:undefined,
        lastHandled:undefined,outcome:'running',lastActionAt:now(),requests:[],
        recoveryCause:null,incompleteReason:null,truncatedTurn:false,actions:new Map(),denied:new Set(),toolHandoff:false,guardDenials:0});
      // An unresolved call from an earlier turn is deliberately not forgotten.
    }
    if(s.blocked || exhausted(s)) {stop(agent,s,'The bounded recovery budget was exhausted.');return {kind:'reject'};}
    if(s.recoveryAt)s.recoverySteps++;
    return decision;
  },{prepend:true});
  ctx.on('agent/request',async({agent,turn,step,signal},next)=>{
    const proposed=await next(); if(!owned(agent)||signal.aborted)return proposed;
    const s=state(agent); let config=proposed;
    if(s.recoveryAt) {
      config={...proposed,maxTokens:Math.min(proposed.maxTokens||c.recoveryMaxTokens,c.recoveryMaxTokens)};
      const route=c.recoveryRoutes.find(r=>r.provider===proposed.provider&&r.model===proposed.model);
      if(route)config.reasoningEffort=route.effort;
    }
    const selected=agent.options.reasoningEffort ?? [...agent.session.snapshotEvents()].reverse()
      .find(e=>e.type==='model/selection')?.data.reasoningEffort ?? null;
    const key=JSON.stringify([selected,config.reasoningEffort,!!s.recoveryAt]);
    if(key!==s.settingNotice && selected!==config.reasoningEffort) {
      notice(agent,s,`Saved reasoning: ${selected||'provider default'}; requested reasoning: ${config.reasoningEffort||'provider default'}${s.recoveryAt?' (bounded recovery)':' (request policy)'}. Backend enforcement is provider-dependent.`);
      s.settingNotice=key;
    }
    s.requests.push({turn,step,startedAt:now(),provider:config.provider,model:config.model,
      selectedEffort:selected,policyEffort:proposed.reasoningEffort??null,requestedEffort:config.reasoningEffort??null,
      requestedMaxTokens:config.maxTokens??null,recovery:!!s.recoveryAt,secondsSinceTool:Math.round((now()-s.lastActionAt)/1000)});
    clearTimeout(s.timer);
    s.timer=setTimeout(()=>{
      if(signal.aborted||agent.status!=='running')return;
      notice(agent,s,`This model step has run for ${Math.round(c.warningMs/1000)} seconds without executing a new action. Generation is still active; task completion is unverified.`);
      record(agent,s);
    },c.warningMs);s.timer.unref?.();
    s.removeAbort?.();
    const aborted=()=>clearTimeout(s.timer);
    signal.addEventListener('abort',aborted,{once:true});
    s.removeAbort=()=>signal.removeEventListener('abort',aborted);
    record(agent,s);return config;
  },{prepend:true});
  ctx.on('agent/assistant-stream',({agent,frame})=>{
    const s=states.get(agent.id);if(s&&frame.type==='end'){clearTimeout(s.timer);s.timer=undefined;s.removeAbort?.();}
  });
  ctx.on('agent/turn-stopping',({agent,signal})=>{
    if(!owned(agent)||signal.aborted)return;
    const s=state(agent),last=s.last;
    if(!last||last.seq===s.lastHandled||s.blocked)return;
    s.lastHandled=last.seq;
    if(s.toolHandoff) {s.outcome='tool-handoff';record(agent,s);return;}
    const truncated=last.stop==='length'||last.truncated;
    const empty=!last.text&&!last.tools;
    if(truncated || empty) {
      if(s.pending.size || last.interrupted) {stop(agent,s,'A tool outcome is unresolved; automatic recovery is disabled.');return;}
      if(s.recoveries>=c.maxRecoveries || exhausted(s)) {
        stop(agent,s,truncated?'Output was truncated again and the recovery limit was reached.':
          'The model stopped without a public answer or tool action and the recovery limit was reached.');return;
      }
      // DSH skips all tool calls in a length-terminated response. Never execute
      // them ourselves; let the model inspect confirmed outcomes and choose anew.
      s.recoveries++; s.recoveryAt ||= now(); s.outcome='recovering';
      s.recoveryCause=truncated?'output-limit':'empty-response'; s.truncatedTurn ||= truncated;
      notice(agent,s,`${truncated?'The response reached its output limit.':'The model stopped without a public answer or tool action.'} Bounded recovery ${s.recoveries}/${c.maxRecoveries} is continuing the existing task from confirmed progress.`);
      const cause=truncated?'The previous response reached its output limit. Its proposed tool calls were not executed by DSH.':
        'The previous response ended without a public answer or tool call. Reasoning alone is not a handoff. Do not expose or repeat private reasoning.';
      agent.steer(message(`Execution recovery: ${cause} Continue only the already authorized task and retain every user restriction. Prior offers, recalled material and this recovery notice grant no new authority. Use confirmed tool results; do not repeat completed actions or assume uncertain outcomes succeeded. If work remains, take one small authorized step and verify its result. If finished, answer the user in the requested form using the evidence available. If blocked or unable to finish, give an honest partial handoff stating what is done, unresolved or unverified. Do not claim that a tool acknowledgment proves the requested outcome.`));
      record(agent,s);return;
    }
    // DSH 0.1.5 keeps the original max-tokens reason sticky for the whole turn.
    // It therefore needs explicit steering after recovered tool batches too.
    if(s.truncatedTurn && last.tools) {
      if(s.pending.size || exhausted(s)) {stop(agent,s,'Recovery has an unresolved action or exhausted its budget.');return;}
      agent.steer(message('Continue the existing authorized task using the tool results just received. Keep steps small; verify requirements before claiming completion.'));
    } else if(s.recoveryAt) {
      // Tool-concluded voice replies/questions are legitimate handoffs. Ordinary
      // empty-response recovery does not have DSH's sticky max-tokens condition.
      s.outcome=last.text?'response-produced':'tool-handoff';
      notice(agent,s,`${last.text?'Recovery produced a response.':'Recovery handed control to a tool.'}${s.truncatedTurn?' DSH retains the earlier output-limit flag.':''} Task completion remains unverified.`);
    }
    record(agent,s);
  });
  ctx.on('agent/status',({agent,status})=>{const s=states.get(agent.id);if(s&&status==='idle'){clearTimeout(s.timer);s.timer=undefined;}});
  ctx.on('agent/disposed',({agent})=>{const s=states.get(agent.id);clearTimeout(s?.timer);s?.removeAbort?.();states.delete(agent.id);});
  ctx.on('dispose',()=>{for(const s of states.values()){clearTimeout(s.timer);s.removeAbort?.();}states.clear();});
}
