// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

export async function voiceSettings(container,send,register=()=>{}){
  const document=container.ownerDocument
  const make=(tag,text)=>{const node=document.createElement(tag);if(text)node.textContent=text;return node}
  const call=async payload=>{const reply=await send('voice/preferences',payload);if(!reply?.ok)throw Error(reply?.error||'Voice settings are unavailable');return reply.result}
  let data=await call({action:'get'}),busy=false
  const add=(host,title,input)=>{const label=make('label',title);label.append(input);host.append(label);return input}
  const enabled=add(container,'Voice On',make('input'));enabled.type='checkbox';enabled.checked=data.enabled
  container.append(make('p','Voice delegates to the model selected in Augmentor. Configure where listening and speaking run.'))
  const controls=make('div');container.append(controls)
  const provider=add(controls,'Voice provider',make('select'))
  for(const [value,title] of [['local','Resonant Voice — local'],['openai-live','OpenAI GPT-Live — cloud']]){const option=make('option',title);option.value=value;provider.append(option)}
  provider.value=data.provider??'local'
  const status=make('p');status.setAttribute('role','status');controls.append(status)
  const localButton=make('button','Set up / configure local voice'),cloudButton=make('button','Set up / configure OpenAI GPT-Live')
  localButton.type=cloudButton.type='button';controls.append(localButton,cloudButton)
  const local=make('div'),cloud=make('div');local.hidden=cloud.hidden=true;controls.append(local,cloud)
  const guide=make('a','Local installation guide');guide.href='https://github.com/ManoloRemiddi/augmentor-agent/blob/main/docs/COMPLETE-INSTALL.md#local-speech';guide.target='_blank';guide.rel='noopener noreferrer';local.append(guide)
  local.append(make('p',data.localError||'Local speech uses your existing Resonant Voice configuration.'))
  const voice=add(local,'Speaking voice',make('select'))
  for(const row of data.voices){const option=make('option',row.name);option.value=row.id;voice.append(option)}
  voice.value=data.values.voiceId
  const speed=add(local,'Speaking speed',make('input'));speed.type='number';speed.min=.75;speed.max=1.5;speed.step=.05;speed.value=data.values.speed
  const volume=add(local,'Output volume',make('input'));volume.type='number';volume.min=0;volume.max=1;volume.step=.05;volume.value=data.values.volume
  cloud.append(make('p','OpenAI processes microphone audio and supplied context. Voice costs $0.05/minute ($3/hour), including silence, plus your selected model’s costs. Test and save opens a short billed session without recording.'))
  const key=add(cloud,'OpenAI project API key',make('input'));key.type='password';key.autocomplete='off'
  const cloudVoice=add(cloud,'OpenAI speaking voice',make('select'))
  for(const row of data.cloudVoices??[{id:'marin',name:'Marin'}]){const option=make('option',row.name);option.value=row.id;cloudVoice.append(option)}
  cloudVoice.value=data.cloudVoice??'marin'
  const consent=add(cloud,'I agree to cloud processing and API duration charges',make('input'));consent.type='checkbox'
  cloud.append(make('p','Your API key stays in the operating system’s credential vault.'))
  if(data.lastUsage){const receipt=data.lastUsage;cloud.append(make('p',`Last session: ${receipt.seconds==null?'duration unknown':receipt.seconds+' seconds'} (${receipt.confirmed?'API confirmed':'final API usage unconfirmed'}).`))}
  const test=make('button','Test and save'),remove=make('button','Remove saved API key');test.type=remove.type='button';cloud.append(test,remove)
  const mode=add(controls,'Conversation mode',make('select'))
  for(const [value,title] of [['manual','Hold or slide to lock'],['hands-free','Hands-free conversation']]){const option=make('option',title);option.value=value;mode.append(option)}mode.value=data.mode
  const pause=add(controls,'Pause before sending (milliseconds)',make('input'));pause.type='number';pause.min=400;pause.max=2000;pause.step=50;pause.value=data.pauseMs
  const save=make('button','Save');save.type='button';controls.append(save)
  const values=()=>({enabled:enabled.checked,provider:provider.value,mode:mode.value,pauseMs:Number(pause.value)})
  const draftValues=()=>({...values(),voiceId:voice.value,speed:Number(speed.value),volume:Number(volume.value),cloudVoice:cloudVoice.value,consent:consent.checked})
  let baseline=JSON.stringify(draftValues())
  register(container,()=>busy||key.value!==''||JSON.stringify(draftValues())!==baseline)
  const update=()=>{voice.replaceChildren();for(const row of data.voices??[]){const option=make('option',row.name);option.value=row.id;voice.append(option)}voice.value=data.values?.voiceId??'';speed.value=data.values?.speed??1;volume.value=data.values?.volume??1;cloudVoice.value=data.cloudVoice??'marin';controls.hidden=!enabled.checked;status.textContent=data.configured?'Voice is ready.':data.audioError||'Voice needs setup. Configure the selected provider.';provider.value=data.provider??provider.value}
  async function operation(work){
    if(busy)return
    busy=true;for(const node of [provider,enabled,save,test,remove,localButton,cloudButton])node.disabled=true
    try{data=await work();provider.value=data.provider;enabled.checked=data.enabled;update();baseline=JSON.stringify(draftValues())}
    catch(error){enabled.checked=data.enabled;provider.value=data.provider;controls.hidden=!enabled.checked;status.textContent=error.message}
    finally{busy=false;for(const node of [provider,enabled,save,test,remove,localButton,cloudButton])node.disabled=false}
  }
  enabled.onchange=()=>{controls.hidden=!enabled.checked;void operation(()=>call({action:'save',settings:values()}))}
  provider.onchange=()=>void operation(()=>call({action:'select',provider:provider.value}))
  localButton.onclick=()=>{local.hidden=false;cloud.hidden=true;key.value='';void operation(()=>call({action:'select',provider:'local'}))}
  cloudButton.onclick=()=>{cloud.hidden=false;local.hidden=true;void operation(()=>call({action:'select',provider:'openai-live'}))}
  test.onclick=()=>{const apiKey=key.value;key.value='';void operation(()=>call({action:'cloud-configure',apiKey,voice:cloudVoice.value,consent:consent.checked}))}
  remove.onclick=()=>{key.value='';void operation(()=>call({action:'cloud-remove'}))}
  save.onclick=()=>void operation(()=>call({action:'save',settings:{...values(),...(provider.value==='local'&&voice.value?{voiceId:voice.value,speed:Number(speed.value),volume:Number(volume.value)}:{})}}))
  document.defaultView.addEventListener('pagehide',()=>{key.value=''}, {once:true})
  const observer=new document.defaultView.MutationObserver(()=>{if(!container.isConnected){key.value='';observer.disconnect()}})
  observer.observe(document.documentElement,{childList:true,subtree:true})
  update()
  return {get busy(){return busy},clear(){key.value=''}}
}
