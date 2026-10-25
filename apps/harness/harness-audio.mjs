// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
export function pcm16(samples,rate){
 const size=Math.floor(samples.length*16000/rate),out=new Int16Array(size);
 for(let i=0;i<size;i++){const at=i*rate/16000,left=Math.floor(at),v=samples[left]*(1-(at-left))+(samples[left+1]??samples[left])*(at-left);out[i]=Math.round(Math.max(-1,Math.min(1,v))*32767);}
 return new Uint8Array(out.buffer);
}
export function voiceControl({phase,recording}){
 return {busy:['preparing','starting','transcribing','thinking'].includes(phase),label:recording?'Finish & send':({preparing:'Connecting…',starting:'Starting mic…',transcribing:'Transcribing…',thinking:'Waiting for reply…',speaking:'Stop speech'}[phase]??'Talk')};
}
export class HarnessAudio {
 listeners=new Set();value={phase:'off',note:'Tap microphone to talk. Tap again to finish and send.',recording:false};sources=new Set();
 constructor(controller,view=globalThis){this.controller=controller;this.view=view;this.unsubscribe=controller.subscribe(()=>{if(this.seat&&this.seat.sessionId!==controller.state.sessionId)void this.close();});view.addEventListener?.('pagehide',()=>void this.close());view.document?.addEventListener('visibilitychange',()=>{if(view.document.hidden)void this.close();});}
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};getSnapshot=()=>this.value;
 set(value){this.value={...this.value,...value};for(const fn of this.listeners)fn();}
 async request(action,extra={},seat=this.seat){
  if(!seat)throw Error('Voice is not connected.');
  const c=this.controller,r=await c.fetcher('/api/voice/'+action,{method:'POST',headers:{Authorization:'Bearer '+c.token,'Content-Type':'application/json'},body:JSON.stringify({clientId:c.clientId,sessionId:seat.sessionId,openId:seat.openId,...extra}),...(action==='close'?{keepalive:true}:{})});
  const value=await r.json();if(!r.ok)throw Error(value.error?.message||'Voice did not confirm the operation. Nothing was replayed.');return value;
 }
 async toggle(){
  try{
   if(this.value.recording){await this.finish();return;}
   if(voiceControl(this.value).busy)return;
   if(this.value.phase==='speaking'){this.clearPlayback();await this.request('control',{type:'interrupt'});this.set({phase:'ready',note:'Speech stopped. Tap microphone to reply.'});return;}
   if(!this.seat)await this.open();
   if(this.seat?.ready)await this.record();
  }catch(error){await this.close();this.set({phase:'error',note:error.message});}
 }
 async open(){
  if(this.closing)await this.closing;
  const state=this.controller.state;if(!state.sessionId||state.phase!=='ready'||state.readOnly)throw Error('Open a chat before using voice.');
  if(state.capabilities?.browserAudio!==1)throw Error('This AH owner needs the tablet audio update.');
  this.set({phase:'preparing',note:'Preparing voice…'});
  const s={sessionId:state.sessionId,openId:crypto.randomUUID(),ready:false,seq:0,pending:0,chain:Promise.resolve(),cancelled:false};this.seat=s;
  // Request capture from the user's gesture; never open the desktop microphone.
  const mediaPromise=this.view.navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true,channelCount:1}});
  void mediaPromise.catch(()=>{});
  s.context=new this.view.AudioContext({latencyHint:'interactive'});await s.context.resume();
  try{const media=await mediaPromise;if(s.cancelled){media.getTracks().forEach(x=>x.stop());return;}s.media=media;s.opening=this.request('open',{},s);await s.opening;if(s.cancelled)return;await this.poll(s);}
  catch(error){await this.close();throw error;}
 }
 async poll(s){
  if(s!==this.seat||s.cancelled)return;
  try{const {events}=await this.request('events',{},s);if(s!==this.seat)return;
   for(const e of events){
    await this.event(s,e);
   }
   if(s===this.seat)s.timer=setTimeout(()=>void this.poll(s),120);
  }catch(error){await this.close();this.set({phase:'error',note:error.message});}
 }
 async event(s,e){
  if(s!==this.seat)return;
  if(e.type==='ready'){s.ready=true;s.maximum=Math.max(1,Math.min(600,Number(e.maxUtteranceSeconds)||60));if(!s.started){s.started=true;await this.record();}}
  else if(e.type==='pcm')this.play(e.data,s);
  else if(e.type==='clear')this.clearPlayback();
  else if(e.type==='transcript'){this.stopCapture(s);s.turnComplete=false;s.speechIdle=false;this.set({recording:false,phase:'thinking',note:'Message sent · waiting for Augmentor.'});}
  else if(e.type==='transcript-partial'&&this.value.recording)this.set({note:'Listening · '+(e.text||'transcribing…')});
  else if(e.type==='recording-ended'){s.ended=true;this.stopCapture(s);this.set({recording:false,phase:'transcribing',note:'Finishing transcription…'});}
  else if(e.type==='speaking'){s.speechIdle=false;this.set({phase:'speaking',note:'Speaking · tap microphone to stop speech.'});}
  else if(e.type==='speech-idle'){s.speechIdle=true;this.playbackReady(s);}
  else if(e.type==='turn-complete'){s.turnComplete=true;this.playbackReady(s);}
  else if(e.type==='empty-transcript')this.set({phase:'ready',note:'No speech detected. Tap microphone to try again.'});
  else if(e.type==='timing'&&e.stage==='asr-final'&&Number.isFinite(e.elapsedMs))this.set({transcriptionMs:Math.round(e.elapsedMs)});
  else if(e.type==='error')throw Error(e.message||'Voice unavailable.');
 }
 playbackReady(s){if(s===this.seat&&s.turnComplete&&s.speechIdle&&!this.sources.size&&!this.value.recording)this.set({phase:'ready',note:'Voice ready. Tap microphone to reply.'});}
 async record(){
  const s=this.seat;if(!s?.ready||this.value.recording||['starting','transcribing','thinking'].includes(this.value.phase))return;
  this.set({phase:'starting',note:'Starting microphone…'});this.clearPlayback();s.ended=false;s.turnComplete=false;s.speechIdle=false;
  if(!s.media){const media=await this.view.navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true,channelCount:1}});if(s!==this.seat){media.getTracks().forEach(x=>x.stop());return;}s.media=media;}
  await this.request('control',{type:'interrupt'});await this.request('control',{type:'begin'});
  if(s!==this.seat)return;
  s.source=s.context.createMediaStreamSource(s.media);s.processor=s.context.createScriptProcessor(4096,1,1);s.silent=s.context.createGain();s.silent.gain.value=0;
  s.source.connect(s.processor);s.processor.connect(s.silent);s.silent.connect(s.context.destination);
  s.processor.onaudioprocess=event=>{
   if(!this.value.recording||s!==this.seat)return;
   const bytes=pcm16(event.inputBuffer.getChannelData(0),s.context.sampleRate),data=btoa(String.fromCharCode(...bytes)),seq=s.seq++;
   if(++s.pending>24){void this.close().then(()=>this.set({phase:'error',note:'Audio connection fell behind. Nothing was retried.'}));return;}
   s.chain=s.chain.then(()=>{if(!s.cancelled)return this.request('audio',{seq,data},s);}).catch(error=>{void this.close().then(()=>this.set({phase:'error',note:error.message}));}).finally(()=>s.pending--);
  };
  this.set({recording:true,phase:'listening',note:'Recording · tap microphone to finish and send.'});s.limit=setTimeout(()=>void this.finish(),(s.maximum??60)*1000);
 }
 stopCapture(s){clearTimeout(s.limit);if(s.processor)s.processor.onaudioprocess=null;s.source?.disconnect();s.processor?.disconnect();s.silent?.disconnect();s.media?.getTracks().forEach(x=>x.stop());s.media=undefined;}
 async finish(){const s=this.seat;if(!s||!this.value.recording)return;this.stopCapture(s);this.set({recording:false,phase:'transcribing',note:'Finishing transcription…'});await s.chain;if(s===this.seat&&!s.cancelled&&!s.ended)await this.request('control',{type:'end'},s);}
 play(data,s){
  if(this.value.recording)return;
  const bytes=Uint8Array.from(atob(data),x=>x.charCodeAt(0));if(bytes.length%2)throw Error('Invalid speech audio.');
  const pcm=new Int16Array(bytes.buffer),buffer=s.context.createBuffer(1,pcm.length,24000),samples=buffer.getChannelData(0);for(let i=0;i<pcm.length;i++)samples[i]=pcm[i]/32768;
  this.set({phase:'speaking',note:'Speaking · tap microphone to stop speech.'});
  const source=s.context.createBufferSource();source.buffer=buffer;source.connect(s.context.destination);this.sources.add(source);source.onended=()=>{this.sources.delete(source);this.playbackReady(s);};const start=Math.max(s.context.currentTime+.025,this.playAt??0);source.start(start);this.playAt=start+buffer.duration;
 }
 clearPlayback(){for(const source of this.sources){try{source.stop();}catch{}}this.sources.clear();this.playAt=0;}
 async close(){
  if(this.closing)return this.closing;const s=this.seat;this.seat=null;
  if(!s){this.set({phase:'off',recording:false});return;}
  s.cancelled=true;clearTimeout(s.timer);this.stopCapture(s);s.media?.getTracks().forEach(x=>x.stop());this.clearPlayback();void s.context?.close();this.set({phase:'off',recording:false,note:'Voice off. Unfinished recording discarded.'});
  this.closing=(async()=>{await s.opening?.catch(()=>{});await this.request('close',{},s).catch(()=>{});})();try{await this.closing;}finally{this.closing=null;}
 }
}
