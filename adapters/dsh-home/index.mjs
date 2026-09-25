// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {actionOutcome} from '../dsh-execution/actions.mjs';

export const READ_TOOL='mcp__homeassistant__homeassistant__GetLiveContext';
export const WRITE_TOOLS=new Set(['mcp__homeassistant__intent__HassTurnOn','mcp__homeassistant__intent__HassTurnOff','mcp__homeassistant__intent__HassLightSet']);
export const DOMAINS=new Set(['light','switch','input_boolean']);
export function authority(name,args) {
  if(name===READ_TOOL)return 'read';
  if(!WRITE_TOOLS.has(name))throw new Error('This Home capability is not enabled.');
  const domains=Array.isArray(args.domain)?args.domain:[args.domain];
  if(!domains.length||domains.some(d=>!DOMAINS.has(d)))throw new Error('Choose an explicit light, switch or input_boolean domain.');
  if(typeof args.name!=='string'||!args.name.trim())throw new Error('Choose a named exposed device; whole-home actions are not enabled.');
  return 'change';
}

// HA can report partial intent failures inside a successful MCP envelope.
// Accept only the observed HA intent acknowledgement contract, not arbitrary
// model-visible prose or MCP transport success. Unknown schemas fail closed.
const intentOutcome={augmentorExecution:{outcome(_args,value){
  let response=value?.structuredContent;
  if(!response){
    const blocks=value?.content;
    if(!Array.isArray(blocks)||blocks.length!==1||blocks[0].type!=='text')return {status:'unknown'};
    response=JSON.parse(blocks[0].text);
  }
  return {status:response?.response_type==='action_done'&&
    Array.isArray(response.data?.success)&&response.data.success.length>0&&
    Array.isArray(response.data?.failed)&&response.data.failed.length===0?'completed':'unknown'};
}}};

// This is policy around the existing DSH and upstream MCP bridge, not an agent
// loop or a device driver. HA Assist owns entity exposure and intent execution.
export function installHomePolicy(ctx,ledger,current,{maxTools=12,maxSteps=10,devices=null}={}) {
  const reservations=new Map(),denied=new Set();
  ctx.on('agent/pre-step',async(exec,next)=>{
    const result=await next(),turn=current();
    if(!turn||turn.cancelled)return {kind:'reject'};
    if(++turn.steps>maxSteps){turn.incomplete='Step budget exhausted';return {kind:'reject'};}
    return result;
  },{prepend:true});
  ctx.on('tools/pre-execute',async(exec,next)=>{
    const decision=await next(),turn=current();
    if(decision.kind!=='allow')return decision;
    try {
      if(!turn||turn.cancelled||exec.signal.aborted)throw new Error('No active Home request.');
      if(++turn.tools>maxTools)throw new Error('Home tool budget exhausted.');
      let effect;
      if(devices){
        if(!['home_devices','home_set'].includes(exec.name))throw new Error('This Home capability is not enabled.');
        effect=exec.name==='home_devices'?'read':'change';
        if(effect==='change'){
          if(turn.readOnly)throw new Error('This client has read-only Home access.');
          await devices.validate(exec.arguments,exec.signal);
        }
      }else effect=authority(exec.name,exec.arguments);
      if(effect!=='read') {
        if(turn.readOnly)throw new Error('This client has read-only Home access.');
        const id=ledger.reserve(turn.id,exec.name,exec.arguments);
        reservations.set(exec.token,{id,turn});
      }
      return decision;
    } catch(error) {
      denied.add(exec.token);
      if(turn)turn.trace.push({tool:exec.name,status:'denied',reason:error.message});
      return {kind:'deny',reason:error.message};
    }
  },{prepend:true});
  ctx.on('tools/result',(exec,result)=>{
    if(denied.delete(exec.token))return;
    const reservation=reservations.get(exec.token),turn=reservation?.turn??current();
    if(!turn)return;
    const effect=[READ_TOOL,'home_devices'].includes(exec.name)?'read':'change';
    const outcome=actionOutcome(exec,result,effect==='change'?(devices?{augmentorExecution:{outcome:(_a,value)=>({status:value?.status==='completed'?'completed':'unknown'})}}:intentOutcome):undefined,effect);
    if(reservation){ledger.outcome(reservation.id,outcome.status);reservations.delete(exec.token);}
    turn.trace.push({tool:exec.name,status:outcome.status,...reservation?{action_id:reservation.id}:{}});
  });
  return {settle(){for(const {id} of reservations.values())ledger.outcome(id,'unknown');reservations.clear();}};
}
