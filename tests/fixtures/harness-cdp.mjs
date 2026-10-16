// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {once} from "node:events";
export async function harnessCdp(url){
  const ws=new WebSocket(url);await once(ws,'open');let id=0;const pending=new Map(),errors=[],dialogs=[],requests=new Map(),failedResponses=[],urls=[],pausedRequests=[],finishedRequests=new Set();
  const listeners=new Set(),retiredSessions=new Set(),contexts=new Map(),lifecycle=[];let transportClosed=false;
  const contextKey=(route,id)=>route+'\0'+id;
  const forgetContexts=(route,match=()=>true)=>{for(const [key,value] of contexts)if(value.sessionId===route&&match(value))contexts.delete(key);};
  const trace=entry=>{lifecycle.push(entry);if(lifecycle.length>128)lifecycle.shift();};
  const retire=(matches,event)=>{for(const [key,row] of pending)if(row.observation&&matches(row)){
    pending.delete(key);clearTimeout(row.timer);trace({event:'observation-retired',id:key,method:row.method,sessionId:row.sessionId??null,reason:event});
    row.reject(Object.assign(Error('CDP observation retired: '+event+'; result unknown; command was not replayed'),{code:'CDP_OBSERVATION_RETIRED'}));
  }};
  const retireSession=session=>{retiredSessions.add(session);if(retiredSessions.size>128)retiredSessions.delete(retiredSessions.values().next().value);forgetContexts(session);retire(row=>(row.sessionId??'')===session,'session-detached');};
  const api={acceptDialog:true,errors,dialogs,requests,failedResponses,urls,pausedRequests,finishedRequests,lifecycle,get contextCount(){return contexts.size;},context(id,sessionId){const value=contexts.get(contextKey(sessionId??'',id));return value?{...value}:undefined;},onEvent(listener){listeners.add(listener);return()=>listeners.delete(listener);}};
  ws.addEventListener('message',event=>{
    const frame=JSON.parse(event.data),row=pending.get(frame.id);
    const route=frame.sessionId??'',p=frame.params??{};
    if(['Runtime.executionContextCreated','Runtime.executionContextDestroyed','Runtime.executionContextsCleared','Target.detachedFromTarget','Inspector.detached','Page.frameDetached'].includes(frame.method)){
      trace({event:frame.method,sessionId:frame.sessionId??null,contextId:p?.context?.id??p?.executionContextId??null,uniqueContextId:p?.context?.uniqueId??p?.executionContextUniqueId??null,frameId:p?.frameId??p?.context?.auxData?.frameId??null,detachedSessionId:frame.method==='Target.detachedFromTarget'?p?.sessionId??null:null});
      if(frame.method==='Runtime.executionContextCreated'&&Number.isSafeInteger(p.context?.id)&&typeof p.context?.uniqueId==='string'){
        const c=p.context,key=contextKey(route,c.id);contexts.delete(key);contexts.set(key,{sessionId:route,id:c.id,uniqueId:c.uniqueId,frameId:c.auxData?.frameId});if(contexts.size>256)contexts.delete(contexts.keys().next().value);
      }
      if(frame.method==='Runtime.executionContextDestroyed')forgetContexts(route,c=>p.executionContextUniqueId!==undefined?c.uniqueId===p.executionContextUniqueId:c.id===p.executionContextId);
      if(frame.method==='Runtime.executionContextsCleared')forgetContexts(route);
      if(frame.method==='Page.frameDetached'&&typeof p.frameId==='string')forgetContexts(route,c=>c.frameId===p.frameId);
      if(frame.method==='Runtime.executionContextDestroyed')retire(r=>(r.sessionId??'')===route&&((p.executionContextId!==undefined&&r.params.contextId===p.executionContextId)||(p.executionContextUniqueId!==undefined&&r.params.uniqueContextId===p.executionContextUniqueId)),frame.method);
      if(frame.method==='Runtime.executionContextsCleared')retire(r=>(r.sessionId??'')===route,frame.method);
      if(frame.method==='Target.detachedFromTarget'&&typeof p.sessionId==='string'&&p.sessionId)retireSession(p.sessionId);
      if(frame.method==='Inspector.detached')retireSession(route);
      if(frame.method==='Page.frameDetached'&&typeof p.frameId==='string'&&p.frameId)retire(r=>(r.sessionId??'')===route&&r.params.frameId===p.frameId,frame.method);
    }
    if(frame.method==='Network.requestWillBeSent')urls.push(frame.params.request.url);
    if(frame.method==='Network.loadingFinished')finishedRequests.add(frame.params.requestId);
    if(frame.method==='Runtime.exceptionThrown')errors.push(frame.params.exceptionDetails);
    if(frame.method==='Fetch.requestPaused'){
      let rpcMethod;try{rpcMethod=JSON.parse(frame.params.request.postData).method;}catch{}
      if(api.pauseRpcMethods&&!api.pauseRpcMethods.has(rpcMethod))void call('Fetch.continueRequest',{requestId:frame.params.requestId}).catch(error=>errors.push(error.message));
      else pausedRequests.push({id:frame.params.requestId,url:frame.params.request.url,rpcMethod,networkId:frame.params.networkId});
    }
    if(frame.method==='Log.entryAdded'&&['warning','error'].includes(frame.params.entry.level))errors.push(frame.params.entry);
    if(frame.method==='Network.requestWillBeSent'&&frame.params.request.postData){try{requests.set(frame.params.requestId,JSON.parse(frame.params.request.postData));}catch{}}
    if(frame.method==='Network.responseReceived'&&frame.params.response.status>=400)failedResponses.push({id:frame.params.requestId,...frame.params.response});
    if(frame.method==='Page.javascriptDialogOpening'){dialogs.push(frame.params.message);void call('Page.handleJavaScriptDialog',{accept:api.acceptDialog}).catch(error=>errors.push(error.message));}
    for(const listener of listeners){try{listener(frame);}catch(error){errors.push('CDP observer callback: '+String(error));}}
    if(row){pending.delete(frame.id);clearTimeout(row.timer);if(row.observation)trace({event:'observation-reply',id:frame.id,method:row.method,sessionId:frame.sessionId??null});
      if(row.observation&&(row.sessionId??'')!==route)row.reject(Error('CDP observation response scope mismatch; result unknown'));
      else frame.error?row.reject(Error(frame.error.message)):row.resolve(frame.result);}
  });
  // Opt-in observations can be abandoned on authoritative context/session loss.
  // Generic calls may act: their unknown results are never retried or promoted.
  const send=(method,params={},sessionId,observation=false)=>new Promise((resolve,reject)=>{
    if(observation&&(transportClosed||retiredSessions.has(sessionId??''))){reject(Object.assign(Error('CDP observation '+(transportClosed?'transport closed':'session already retired')+'; command not sent'),{code:'CDP_OBSERVATION_RETIRED'}));return;}
    const key=++id,timer=setTimeout(()=>{pending.delete(key);if(observation)trace({event:'observation-timeout',id:key,method,sessionId:sessionId??null});reject(Error('CDP timeout: '+method));},10000);
    pending.set(key,{resolve,reject,timer,method,params:{contextId:params.contextId,uniqueContextId:params.uniqueContextId,frameId:params.frameId},sessionId,observation});if(observation)trace({event:'observation-sent',id:key,method,sessionId:sessionId??null});
    try{ws.send(JSON.stringify({id:key,method,params,...(sessionId?{sessionId}:{})}));}catch(error){pending.delete(key);clearTimeout(timer);reject(error);}
  });
  const call=(method,params={},sessionId)=>send(method,params,sessionId);
  ws.addEventListener('close',()=>{transportClosed=true;contexts.clear();retire(()=>true,'transport-closed');});
  return Object.assign(api,{call,read(method,params={},sessionId){
    if(!['Runtime.evaluate','Page.getFrameTree','Page.createIsolatedWorld','Target.getTargets'].includes(method))return Promise.reject(Error('Not a supported CDP observation method'));
    return send(method,params,sessionId,true);
  },async navigate(url){
    const key='__augmentor_test_navigation_'+crypto.randomUUID().replaceAll('-','');await api.evaluate('globalThis['+JSON.stringify(key)+']=true');
    const result=await call('Page.navigate',{url});if(result.errorText)throw Error('CDP navigation failed: '+result.errorText);
    const end=Date.now()+10000;while(Date.now()<end){try{if(await api.evaluate('globalThis['+JSON.stringify(key)+']===undefined&&document.readyState==="complete"'))return;}catch{}await new Promise(resolve=>setTimeout(resolve,30));}
    throw Error('CDP navigation did not replace and finish the document');
  },async reload(){
    const key='__augmentor_test_reload_'+crypto.randomUUID().replaceAll('-','');await api.evaluate('globalThis['+JSON.stringify(key)+']=true');await call('Page.reload');
    const end=Date.now()+10000;while(Date.now()<end){try{if(await api.evaluate('globalThis['+JSON.stringify(key)+']===undefined&&document.readyState==="complete"'))return;}catch{}await new Promise(resolve=>setTimeout(resolve,30));}
    throw Error('CDP reload did not replace the document');
  },close(){transportClosed=true;contexts.clear();retire(()=>true,'observer-closed');for(const row of pending.values())clearTimeout(row.timer);listeners.clear();ws.close();},async evaluate(expression){const result=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));return result.result.value;}});
}
