// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

export async function updateSettings(container,send,{registerDirty=()=>{}}={}){
  const doc=container.ownerDocument,win=doc.defaultView
  const make=(tag,text)=>{const el=doc.createElement(tag);if(text)el.textContent=text;return el}
  const call=async(method,params={})=>{const r=await send('surface/updates',{method,params});if(!r?.ok)throw Error(r?.error||'Updates are unavailable');return r.result}
  const label=(text,input)=>{const row=make('label',text);row.append(input);container.append(row);return input}
  const info=make('p');info.style.whiteSpace='pre-line';container.append(info)
  const checks=label('Check for updates automatically',make('input'));checks.type='checkbox'
  const interval=label('Check frequency',make('select')),channel=label('Update channel',make('select'))
  for(const [value,text] of [[24,'Every day'],[48,'Every two days']]){const option=make('option',text);option.value=String(value);interval.append(option)}
  for(const [value,text] of [['stable','Stable releases'],['preview','Preview releases']]){const option=make('option',text);option.value=value;channel.append(option)}
  const downloads=label('Download new versions automatically',make('input'));downloads.type='checkbox'
  const installs=label('Install automatically when Augmentor is idle',make('input'));installs.type='checkbox'
  const explanation=make('p');container.append(explanation)
  const note=make('p');note.setAttribute('role','status');container.append(note)
  const release=make('a','Open release and installation instructions');release.target='_blank';release.rel='noopener noreferrer';release.hidden=true
  let state=null,busy=false,closed=false,dirty=false,revision=null
  const controls=[checks,interval,channel,downloads,installs]
  for(const control of controls)control.addEventListener('input',()=>{dirty=true;enable()})
  registerDirty(container,()=>dirty)
  const values=()=>({automaticChecks:checks.checked,intervalHours:Number(interval.value),channel:channel.value,
                     automaticDownload:downloads.checked,automaticInstall:installs.checked})
  const button=(text,fn)=>{const b=make('button',text);b.type='button';b.onclick=()=>void operate(fn);container.append(b);return b}
  const save=button('Save update preferences',async()=>{await call('configure',{revision,preferences:values()});dirty=false})
  const reload=button('Reload saved preferences',async()=>{dirty=false})
  const check=button('Check now',()=>call('check')),download=button('Download update',()=>call('download'))
  const cancel=button('Cancel download',()=>call('cancel'))
  container.append(release)
  const folder=button('Show downloaded files',()=>call('reveal'))
  const remind=button('Remind me tomorrow',()=>call('postpone',{hours:24})),skip=button('Skip this release',()=>call('skip'))
  const buttons=[save,reload,check,download,cancel,remind,skip,folder]
  async function refresh(){
    state=await call('status');if(closed)return
    const current=state.installed,candidate=state.candidate
    let text=`Installed: ${current.version} · build ${current.buildKnown===false?'unknown':current.build}\nLast successful check: ${state.lastSuccessfulCheck?new Date(state.lastSuccessfulCheck*1000).toLocaleString():'Never'}`
    if(candidate)text+=`\nAvailable: ${candidate.version} · build ${candidate.build}`
    else if(state.phase==='current')text+='\nNo newer compatible release was found.'
    if(state.phase==='ready')text+='\nDownload ready. Open the release instructions to install.'
    if(state.phase==='downloading')text+=`\nDownloading: ${((state.bytesDownloaded||0)/1024**2).toFixed(1)} MB`
    info.textContent=text;note.textContent=state.error||''
    explanation.textContent='Downloads use your internet connection and disk space. Settings are shared with Desktop. '+
      (state.automaticInstallAvailable?'Automatic installation waits for all Augmentor work to finish.':'Automatic installation is not available for this installed build. Use the release installation instructions. Reload the browser extension after updating its companion.')
    if(!dirty){const p=state.preferences;checks.checked=p.automaticChecks;interval.value=String(p.intervalHours);channel.value=p.channel;downloads.checked=p.automaticDownload;installs.checked=p.automaticInstall;revision=state.revision}
    release.hidden=!candidate
    if(candidate)release.href=candidate.releaseUrl;else release.removeAttribute('href')
  }
  function enable(){
    const working=state?.busy
    for(const control of controls)control.disabled=!state||busy||!!working
    installs.disabled=installs.disabled||!state?.automaticInstallAvailable
    save.disabled=!state||busy||working||!dirty;reload.disabled=busy
    check.disabled=!state||busy||working||dirty
    download.disabled=check.disabled||!state?.candidate
    cancel.disabled=busy||!working
    folder.disabled=busy||state?.phase!=='ready'
    remind.disabled=skip.disabled=busy||!state?.candidate
  }
  async function operate(fn){
    if(busy||closed)return;busy=true;for(const b of buttons)b.disabled=true;for(const control of controls)control.disabled=true
    try{await fn();await refresh()}catch(error){note.textContent=error.message}finally{busy=false;enable()}
  }
  enable();await operate(async()=>{})
  const timer=win.setInterval(()=>void operate(async()=>{}),2500)
  win.addEventListener('pagehide',()=>{closed=true;win.clearInterval(timer)},{once:true})
  return {refresh:()=>operate(async()=>{}),close:()=>{closed=true;win.clearInterval(timer)}}
}

export function attachUpdateNotice({document:doc,send,openSettings,paused=()=>false}){
  const win=doc.defaultView,button=doc.createElement('button')
  button.type='button';button.className='update-notice';button.hidden=true
  button.onclick=()=>{button.hidden=true;openSettings('updates')}
  doc.querySelector('header').after(button)
  let pending=false,closed=false
  const poll=async()=>{
    if(pending||closed||paused()||doc.hidden)return
    pending=true
    try{
      const r=await send('surface/updates',{method:'notification'})
      if(!closed&&r?.ok&&r.result){button.textContent=`Augmentor ${r.result.version} (build ${r.result.build}) is available · Open updates`;button.hidden=false}
    }catch{}finally{pending=false}
  }
  const timer=win.setInterval(()=>void poll(),60000)
  void poll()
  win.addEventListener('pagehide',()=>{closed=true;win.clearInterval(timer)},{once:true})
  return {poll,close:()=>{closed=true;win.clearInterval(timer)}}
}
