// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

export function attachVoice({send,onError,isHistory}){
  const button=document.createElement('button');const icon=document.createElement('img');icon.src=chrome.runtime.getURL('voice-orb.svg');icon.alt='';icon.width=24;icon.height=24;button.append(icon);button.title='Resonant Voice';button.setAttribute('aria-label','Resonant Voice');button.type='button';
  document.getElementById('send').before(button);
  const dialog=document.createElement('section'),status=document.createElement('p'),talk=document.createElement('button'),mute=document.createElement('button'),close=document.createElement('button');
  const title=document.createElement('h3');title.textContent='Resonant Voice';
  talk.textContent='Hold to talk';mute.textContent='Mute';close.textContent='Close';talk.type=mute.type=close.type='button';
  const help=document.createElement('p');help.textContent='English · Use headphones · Spoken messages use this conversation’s tools and approvals.';
  dialog.id='resonant-voice-controls';dialog.hidden=true;dialog.setAttribute('aria-label','Resonant Voice controls');
  button.setAttribute('aria-expanded','false');button.setAttribute('aria-controls',dialog.id);status.setAttribute('role','status');
  dialog.style.cssText='padding:10px 14px;border-top:1px solid var(--border);flex-shrink:0';
  dialog.append(title,status,help,talk,mute,close);
  const footer=document.getElementById('send').closest('footer');if(footer)footer.after(dialog);else document.body.append(dialog);
  function reveal(){dialog.hidden=false;button.setAttribute('aria-expanded','true');}
  function collapse(){shutdown();dialog.hidden=true;button.setAttribute('aria-expanded','false');button.focus();}
  let ws=null,context=null,stream=null,capture=null,session=null,generation=-1,nextPlay=0,muted=false,recording=false,closed=true,connecting=false;
  const playing=new Set(),submitted=new Set();
  function clear(){for(const source of playing){try{source.stop();}catch{}}playing.clear();nextPlay=0;generation=-1;}
  function control(value){if(ws?.readyState===WebSocket.OPEN)ws.send(JSON.stringify(value));}
  function shutdown(){closed=true;connecting=false;recording=false;clear();ws?.close();ws=null;stream?.getTracks().forEach(track=>track.stop());stream=null;capture?.disconnect();capture=null;void context?.close();context=null;session=null;talk.disabled=true;}
  function error(message){status.textContent=message;shutdown();onError(message);}
  async function open(){
    if(isHistory()){onError('Open the current conversation to use Voice.');return;}
    if(connecting)return;
    if(!closed){reveal();return;}
    connecting=true;closed=false;muted=false;mute.textContent='Mute';submitted.clear();status.textContent='Preparing microphone and speech models…';talk.disabled=true;reveal();
    try{
      // User click creates/resumes the context before waiting on network activity.
      context=new AudioContext({sampleRate:16000,latencyHint:'interactive'});await context.resume();
      stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
      if(closed){stream.getTracks().forEach(track=>track.stop());return;}
      await context.audioWorklet.addModule(chrome.runtime.getURL('voice-worklet.js'));
      capture=new AudioWorkletNode(context,'resonant-capture');context.createMediaStreamSource(stream).connect(capture);
      const silent=context.createGain();silent.gain.value=0;capture.connect(silent).connect(context.destination);
      capture.port.onmessage=({data})=>{
        if(data instanceof ArrayBuffer){if(ws?.readyState===1){if(ws.bufferedAmount>64000){error('Microphone connection fell behind.');return;}ws.send(data);}}
        else if(data.type==='ended'){control({type:'end'});status.textContent='Recognizing…';talk.disabled=true;}
        else if(data.type==='error')error(data.message);
      };
      const response=await send('voice/connect');if(closed)return;if(!response?.ok)throw Error(response?.error||'Voice connection failed');
      const ticket=response.ticket;if(ticket.protocol!=='resonant-voice/1'||!/^ws:\/\/127\.0\.0\.1:\d+\/voice$/.test(ticket.url))throw Error('Invalid voice endpoint');
      session=ticket.sessionId;ws=new WebSocket(ticket.url);ws.binaryType='arraybuffer';
      ws.onopen=()=>control({type:'auth',ticket:ticket.ticket});
      ws.onmessage=async({data})=>{
        if(closed)return;
        if(data instanceof ArrayBuffer){
          if(data.byteLength<8||data.byteLength%2){error('Invalid speech packet');return;}
          const view=new DataView(data);if(view.getUint32(0,true)!==generation)return;
          if(nextPlay-context.currentTime>8){error('Speech playback fell behind. Read the remaining answer in chat.');return;}
          const count=(data.byteLength-8)/2,buffer=context.createBuffer(1,count,24000),channel=buffer.getChannelData(0);
          for(let i=0;i<count;i++)channel[i]=view.getInt16(8+i*2,true)/32768;
          const source=context.createBufferSource();source.buffer=buffer;source.connect(context.destination);playing.add(source);source.onended=()=>playing.delete(source);
          nextPlay=Math.max(nextPlay,context.currentTime+.02);source.start(nextPlay);nextPlay+=buffer.duration;return;
        }
        let event;try{event=JSON.parse(data);}catch{error('Invalid voice control');return;}
        if(event.type==='clear'){clear();generation=event.generation;}
        else if(event.type==='ready'){connecting=false;status.textContent='Ready';talk.disabled=false;}
        else if(event.type==='transcript'){
          if(event.sessionId!==session||submitted.has(event.requestId))return;submitted.add(event.requestId);
          status.textContent='Thinking…';talk.disabled=false;
          const result=await send('voice/prompt',{text:event.text,sessionId:session,requestId:event.requestId});
          if(!result?.ok)error(result?.error||'Message was not accepted. Check chat before trying again.');
        }else if(event.type==='empty-transcript'){status.textContent='No speech recognized. Try again.';talk.disabled=false;}
        else if(event.type==='speaking')status.textContent='Speaking…';
        else if(event.type==='error'){if(event.recoverable){status.textContent=event.message;talk.disabled=false;}else error(event.message);}
      };
      ws.onerror=()=>error('Voice connection failed. Text chat remains available.');
      ws.onclose=()=>{if(!closed){status.textContent='Voice disconnected. Reopen to connect again.';shutdown();}};
    }catch(e){error(e.message);}
  }
  function begin(){if(talk.disabled||recording||closed)return;recording=true;clear();control({type:'begin'});capture.port.postMessage('start');status.textContent='Listening…';}
  function end(){if(!recording)return;recording=false;capture?.port.postMessage('stop');}
  button.onclick=()=>{if(!dialog.hidden)collapse();else void open();};
  talk.onpointerdown=e=>{talk.setPointerCapture(e.pointerId);begin();};talk.onpointerup=end;talk.onpointercancel=end;
  talk.onkeydown=e=>{if([' ','Enter'].includes(e.key)){e.preventDefault();if(!e.repeat)begin();}};
  talk.onkeyup=e=>{if([' ','Enter'].includes(e.key)){e.preventDefault();end();}};
  mute.onclick=()=>{muted=!muted;mute.textContent=muted?'Unmute':'Mute';control({type:'mute',value:muted});if(muted)clear();};
  close.onclick=()=>collapse();window.addEventListener('pagehide',shutdown);window.addEventListener('blur',end);
  document.getElementById('stop')?.addEventListener('click',()=>{collapse();shutdown();});
  return {update(state,history){button.disabled=state.harness!=='dsh'||state.phase!=='ready'||history;if(!closed&&(history||state.harness&&state.harness!=='dsh'||session&&state.sessionId&&session!==state.sessionId)){collapse();shutdown();}}};
}
