// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useEffect,useState,useSyncExternalStore} from 'react';
import {VoiceInput} from './vendor/dsh/packages/experimental/client-ui-voice-input/src/client/VoiceInput.tsx';
import {Recording} from './vendor/dsh/packages/experimental/client-ui-voice-input/src/client/audio.ts';
import {MicrophonePicker} from './vendor/dsh/packages/experimental/client-ui-voice-input/src/client/MicrophonePicker.tsx';
import {createMicrophoneDeviceStore} from './vendor/dsh/packages/experimental/client-ui-voice-input/src/client/microphone-device.ts';
import {en} from './vendor/dsh/packages/experimental/client-ui-voice-input/src/client/locales.ts';
import {Button} from '@deepseek-ai/dsh-client-ui-primitives';
import {DshDictation} from './dsh-dictation.mjs';

const device=createMicrophoneDeviceStore();
const useMicrophoneDevice=select=>select(useSyncExternalStore(device.subscribe,device.getSnapshot,device.getSnapshot));
const t=(key,args={})=>String(en[key]??key).replace(/\{(\w+)\}/g,(_,name)=>String(args[name]??''));
let transport;
export function bindDictation(controller){
  if(transport)throw Error('Dictation is already bound.');
  transport=new DshDictation(controller,{Recording,device:device.getSnapshot});
  window.addEventListener('pagehide',()=>{void transport.current?.dispose();});
}
function useReadiness(select=x=>x){
  const [readiness,setReadiness]=useState({connected:false,catalog:null,error:null});
  useEffect(()=>{
    const abort=new AbortController();let timer;
    const poll=async()=>{
      try{const value=await transport.catalog(abort.signal);if(abort.signal.aborted)return;
        setReadiness({connected:true,error:null,catalog:{providers:[{id:'resonant-cpu',name:'Configured Whisper · CPU',location:'host-local',preparation:{phase:value.available?'standby':'failed'}}],selection:{providerId:'resonant-cpu',language:'en'},maxAudioBytes:value.maxAudioBytes,maxDurationSeconds:value.maxDurationSeconds}});
      }catch(error){if(!abort.signal.aborted)setReadiness({connected:false,catalog:null,error:error.message});}
      finally{if(!abort.signal.aborted)timer=setTimeout(poll,5000);}
    };void poll();return()=>{abort.abort();clearTimeout(timer);};
  },[]);return select(readiness);
}
const actions={createRecording:(...args)=>transport.createRecording(...args),transcribe:(...args)=>transport.transcribe(...args)};
export function OriginalDictation(props){return <VoiceInput {...props} {...actions} useSpeechReadiness={useReadiness} t={t}/>;}
export function DictationSettings(){
  const readiness=useReadiness(),[preview,setPreview]=useState(false);
  return <fieldset><legend>Voice input</legend><p>{readiness.error||(!readiness.catalog?'Checking recognition…':readiness.catalog.providers[0].preparation.phase==='standby'?'Existing Whisper model is cached. Recognition runs locally on CPU.':'The configured recognition model is not cached. No download was started.')}</p><p>Dictation inserts editable text. Press Send when ready. Recognition language: English.</p><Button onClick={()=>setPreview(value=>!value)}>{preview?'Close microphone settings':'Choose microphone'}</Button>{preview&&<MicrophonePicker createRecording={actions.createRecording} useMicrophoneDevice={useMicrophoneDevice} selectMicrophone={value=>device.set(value)} t={t}/>}</fieldset>;
}
