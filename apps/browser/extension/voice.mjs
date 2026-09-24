import {attachVoiceIcon} from './voice-icon.mjs'
// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// The sidebar presents the native VoiceSession; it has no separate ASR/audio loop.
export function attachVoice({send,onError,isHistory}){
  const button=document.createElement('button'),icon=document.createElement('span'),status=document.createElement('span')
  icon.className='voice-shape';icon.setAttribute('aria-hidden','true')
  button.type='button';button.className='voice-orb';button.append(icon)
  button.setAttribute('aria-label','Voice: hold to talk, slide left to lock, slide right for hands-free')
  status.className='voice-status sr-only';status.setAttribute('role','status');status.setAttribute('aria-live','polite')
  const seat=document.getElementById('voice-seat');if(seat)seat.append(button,status);else document.getElementById('send').before(button,status)
  const drawing=typeof MutationObserver==='function'?attachVoiceIcon(button):null
  let lease=null,opening=null,epoch=0,held=false,locked=false,handsFree=false,timer=null,startX=0,heartbeat=null,voiceState='closed'
  let maxSeconds=600,elapsed=0,defaultHandsFree=false,voiceEnabled=true,nextPreferences=0
  const label=text=>{status.textContent=text;button.title=text;button.setAttribute('aria-description',text)}
  label('Hold to talk · Slide left to lock · Slide right for hands-free')
  async function control(action,current=lease){
    if(!current)return
    const result=await send('voice/control',{...current,action})
    if(!result?.ok&&action!=='close'){onError(result?.error??'Voice disconnected');close()}
  }
  function close(){
    ++epoch;clearTimeout(timer);clearInterval(heartbeat);heartbeat=null
    held=false;locked=false;handsFree=false;voiceState='closed';opening=null
    const old=lease;lease=null;const closing=control('close',old)
    button.dataset.state='closed';button.dataset.mode='';button.style.removeProperty('--voice-level')
    label('Voice off · Hold to talk · Slide right for hands-free')
    return closing
  }
  async function open(free=false){
    if(isHistory())throw Error('Open the current conversation to use Voice.')
    if(lease)return lease
    if(opening)return opening
    const ownEpoch=epoch,id=crypto.randomUUID();handsFree=free;label('Preparing speech models…')
    opening=(async()=>{
      const result=await send('voice/start',{id,handsFree:free})
      if(!result?.ok)throw Error(result?.error??'Voice could not start')
      const current=result.voice
      if(epoch!==ownEpoch){await control('close',current);return null}
      lease=current;heartbeat=setInterval(()=>void control('heartbeat'),2000)
      return current
    })()
    try{return await opening}
    catch(error){if(epoch===ownEpoch){onError(error.message);close();label(error.message)}return null}
    finally{if(epoch===ownEpoch)opening=null}
  }
  async function begin(){const current=await open();if(current&&(held||locked))await control('begin',current)}
  function down(event){
    if(button.disabled||event.button>0)return
    event.preventDefault()
    if(handsFree){close();return}
    if(defaultHandsFree&&!lease){void open(true);return}
    if(locked){locked=false;void control('end');return}
    held=true;startX=event.clientX??0
    if(event.pointerId!==undefined)button.setPointerCapture(event.pointerId)
    timer=setTimeout(()=>{timer=null;if(held)void begin()},230)
  }
  function release(){
    if(!held)return
    held=false
    if(timer){clearTimeout(timer);timer=null;void open().then(current=>{if(current)void control('interrupt',current)})}
    else if(!locked&&!handsFree)void control('end')
    button.style.transform=''
  }
  button.onpointerdown=down
  button.onpointermove=event=>{
    if(!held||locked||handsFree)return
    const delta=event.clientX-startX
    button.style.transform=`translateX(${Math.max(-12,Math.min(12,delta))}px)`
    if(delta<=-24){clearTimeout(timer);timer=null;locked=true;button.dataset.mode='locked';label('Recording locked · Tap to send');void begin()}
    else if(delta>=24){const closing=close(),ownEpoch=epoch;handsFree=true;button.dataset.mode='hands-free';void closing.then(()=>{if(epoch===ownEpoch)return open(true)})}
  }
  button.oncontextmenu=event=>{event.preventDefault();void send('settings/open',{section:'voice'})}
  button.onclick=event=>{if(event.detail===0&&!button.disabled){if(handsFree)close();else if(locked){locked=false;void control('end')}else if(lease)void control('interrupt');else void open(defaultHandsFree)}}
  button.onpointerup=release
  button.onpointercancel=()=>{if(!locked&&!handsFree)close()}
  button.onkeydown=event=>{
    if(event.key==='Escape'){event.preventDefault();close()}
    else if(event.key===' '&&!event.repeat)down(event)
    else if(event.key==='Enter'&&!event.repeat){event.preventDefault();if(handsFree)close();else if(locked){locked=false;void control('end')}else if(defaultHandsFree)void open(true);else void open().then(current=>control('interrupt',current))}
    else if(event.key.toLowerCase()==='l'&&held){clearTimeout(timer);timer=null;locked=true;button.dataset.mode='locked';void begin()}
  }
  button.onkeyup=event=>{if(event.key===' '){event.preventDefault();release()}}
  chrome.runtime.onMessage.addListener(message=>{
    if(message.type!=='voice/event')return
    const event=message.event
    if(!lease||event.id!==lease.id||event.sessionId!==lease.sessionId)return
    if(event.type==='error'){onError(event.message);close();label(event.message);return}
    if(event.type==='state'){
      voiceState=event.state;button.dataset.state=voiceState
      if(event.closed){close();return}
      button.dataset.recording=String(event.recordingAvailable)
      label(locked&&event.recording?'Recording locked · Tap to send':event.status)
    }else if(event.type==='progress'){
      elapsed=event.elapsed;maxSeconds=event.maximum
      drawing?.levels(event.levels)
      button.style.setProperty('--voice-level',String(Math.max(0,...event.levels)))
      button.dataset.limit=elapsed>=maxSeconds*.9?'red':elapsed>=maxSeconds*.8?'orange':''
      if(event.elapsed>0)status.textContent=`${locked?'Recording locked':handsFree?'Listening':'Release to send'} · ${Math.floor(elapsed/60)}:${String(Math.floor(elapsed%60)).padStart(2,'0')}`
    }
  })
  window.addEventListener('pagehide',close)
  window.addEventListener('blur',()=>{if(held&&!locked&&!handsFree)close()})
  document.addEventListener('visibilitychange',()=>{if(document.hidden)close()})
  document.getElementById('stop')?.addEventListener('click',close)
  return {update(state,history){
    if(state.harness==='dsh'&&state.phase==='ready'&&!lease&&!opening&&Date.now()>nextPreferences){
      nextPreferences=Date.now()+15000
      void send('voice/preferences').then(result=>{if(result?.ok&&result.result){defaultHandsFree=result.result.mode==='hands-free';voiceEnabled=result.result.enabled;button.hidden=!voiceEnabled;status.hidden=!voiceEnabled}}).catch(()=>{})
    }
    button.disabled=state.harness!=='dsh'||state.phase!=='ready'||history||!voiceEnabled
    if((lease||opening)&&(button.disabled||lease&&state.sessionId&&lease.sessionId!==state.sessionId))close()
    if(button.disabled&&state.harness==='pi')button.title='Voice uses the shared DSH harness. Select DSH in Settings → Harnesses.'
  }}
}
