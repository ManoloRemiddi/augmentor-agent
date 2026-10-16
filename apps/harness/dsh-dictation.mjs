// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Adapter for the original DSH Recording/VoiceInput contracts. All service
 * credentials and protocol details remain in the trusted Pi Host. */
export class DshDictation {
  current=null;
  constructor(controller,{Recording,device=()=>({id:''})}){
    this.controller=controller;this.Recording=Recording;this.device=device;
    this.unsubscribe=controller.subscribe(()=>{if(this.current&&!this.valid(this.current))void this.current.dispose();});
  }
  valid(op){return op.epoch===this.controller.epoch&&op.sessionId===(this.controller.state.sessionId||undefined)&&this.controller.state.phase==='ready'&&!this.controller.state.readOnly;}
  async request(action,body,signal,binary){
    const c=this.controller,path='/api/dictation/'+action+(binary?'?'+new URLSearchParams({clientId:body.clientId,captureId:body.captureId}):'');
    const response=await c.fetcher(path,{method:'POST',headers:{Authorization:'Bearer '+c.token,'Content-Type':binary?'audio/wav':'application/json'},body:binary??JSON.stringify(body),...(signal?{signal}:{}),...(action==='close'?{keepalive:true}:{})});
    const result=await response.json();if(!response.ok)throw Error(result.error?.message||'Recognition is unavailable.');return result;
  }
  async catalog(signal,refresh=false){return this.request('catalog',refresh?{refresh:true}:{},signal);}
  createRecording=()=>{
    const previous=this.current;
    const c=this.controller,abort=new AbortController(),raw=new this.Recording(()=>{},this.device().id);
    const op={clientId:c.clientId,captureId:crypto.randomUUID(),sessionId:c.state.sessionId||undefined,epoch:c.epoch,abort,raw,started:false,stopped:false};
    const body=()=>({clientId:op.clientId,captureId:op.captureId});
    let opening,closing,timer;
    const reserve=async()=>{
      if(previous)await previous.dispose();
      if(this.current!==op||!this.valid(op)||abort.signal.aborted)throw Error('This draft is no longer active.');
      timer=setInterval(()=>{if(!this.valid(op)){void dispose();return;}void this.request('heartbeat',body(),abort.signal).catch(()=>{void dispose();});},2000);
      opening=this.request('open',{...body(),...(op.sessionId?{sessionId:op.sessionId}:{})},abort.signal);
      const result=await opening;if(!this.valid(op)||abort.signal.aborted)throw Error('This draft is no longer active.');op.started=true;return result;
    };
    const dispose=()=>{
      if(!closing)closing=(async()=>{abort.abort();clearInterval(timer);await Promise.allSettled([raw.dispose(),opening]);await this.request('close',body()).catch(()=>{});if(this.current===op)this.current=null;})();
      return closing;
    };
    Object.assign(op,{dispose,body});this.current=op;
    return {
      start:async onError=>{await reserve();await raw.start(error=>{void dispose();onError?.(error);});},
      preview:async onError=>{await reserve();await raw.preview(error=>{void dispose();onError?.(error);});},
      stop:async seconds=>{const wave=await raw.stop(seconds);op.stopped=true;return wave;},
      dispose,amplitude:()=>raw.amplitude(),deviceInfo:()=>raw.deviceInfo(),
    };
  };
  transcribe=async(request,signal)=>{
    const op=this.current;
    if(!op||!op.started||!op.stopped||!this.valid(op))throw Error('This recording is no longer owned by the draft.');
    try{
      signal.throwIfAborted();if(request.providerId!=='resonant-cpu'||request.language!=='en'||typeof request.audioBase64!=='string'||request.audioBase64.length>25600060)throw Error('Use the configured CPU recognizer and a bounded recording.');
      const bytes=Uint8Array.from(atob(request.audioBase64),char=>char.charCodeAt(0));
      const value=await this.request('transcribe',op.body(),AbortSignal.any([signal,op.abort.signal]),bytes);
      if(!this.valid(op)||op.abort.signal.aborted)throw Error('This draft is no longer active.');
      return {ok:true,value};
    }finally{await op.dispose();}
  };
  async dispose(){this.unsubscribe();await this.current?.dispose();}
}

/** A span is admitted once, only into the same editor revision and draft scope. */
export function dictationInsertion({scope,revision,span,replace}){
  const owners=new WeakMap();
  return {
    captureInsertion(){const value={...span(),draftRev:revision()};owners.set(value,scope());return value;},
    insertText(text,value){const owner=owners.get(value);if(typeof text!=='string'||text.length>262144||!owner||value.draftRev!==revision()||owner!==scope())return false;owners.delete(value);return replace(value,text);},
  };
}
