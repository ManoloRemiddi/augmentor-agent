// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {once} from "node:events";
export async function harnessCdp(url){
  const ws=new WebSocket(url);await once(ws,'open');let id=0;const pending=new Map(),errors=[],dialogs=[],requests=new Map(),failedResponses=[],urls=[],pausedRequests=[],finishedRequests=new Set();
  const api={acceptDialog:true,errors,dialogs,requests,failedResponses,urls,pausedRequests,finishedRequests};
  ws.addEventListener('message',event=>{
    const frame=JSON.parse(event.data),row=pending.get(frame.id);
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
    if(row){pending.delete(frame.id);clearTimeout(row.timer);frame.error?row.reject(Error(frame.error.message)):row.resolve(frame.result);}
  });
  const call=(method,params={},sessionId)=>new Promise((resolve,reject)=>{const key=++id,timer=setTimeout(()=>{pending.delete(key);reject(Error('CDP timeout: '+method));},10000);pending.set(key,{resolve,reject,timer});ws.send(JSON.stringify({id:key,method,params,...(sessionId?{sessionId}:{})}));});
  return Object.assign(api,{call,async navigate(url){
    const key='__augmentor_test_navigation_'+crypto.randomUUID().replaceAll('-','');await api.evaluate('globalThis['+JSON.stringify(key)+']=true');
    const result=await call('Page.navigate',{url});if(result.errorText)throw Error('CDP navigation failed: '+result.errorText);
    const end=Date.now()+10000;while(Date.now()<end){try{if(await api.evaluate('globalThis['+JSON.stringify(key)+']===undefined&&document.readyState==="complete"'))return;}catch{}await new Promise(resolve=>setTimeout(resolve,30));}
    throw Error('CDP navigation did not replace and finish the document');
  },async reload(){
    const key='__augmentor_test_reload_'+crypto.randomUUID().replaceAll('-','');await api.evaluate('globalThis['+JSON.stringify(key)+']=true');await call('Page.reload');
    const end=Date.now()+10000;while(Date.now()<end){try{if(await api.evaluate('globalThis['+JSON.stringify(key)+']===undefined&&document.readyState==="complete"'))return;}catch{}await new Promise(resolve=>setTimeout(resolve,30));}
    throw Error('CDP reload did not replace the document');
  },close(){for(const row of pending.values())clearTimeout(row.timer);ws.close();},async evaluate(expression){const result=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));return result.result.value;}});
}
