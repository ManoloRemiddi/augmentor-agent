// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Audio stays in the common native engine. This transport owns one expiring UI lease.
import {spawn} from 'node:child_process'
import {readFileSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
import path from 'node:path'
import os from 'node:os'

export function voicePython(root, env=process.env){
  if(env.AUGMENTOR_PYTHON)return env.AUGMENTOR_PYTHON
  try{
    const descriptor=JSON.parse(readFileSync(path.join(env.XDG_DATA_HOME??path.join(os.homedir(),'.local/share'),'augmentor/desktop.json'),'utf8'))
    if(path.resolve(descriptor.root)===path.resolve(root)&&typeof descriptor.python==='string')return descriptor.python
  }catch{}
  return 'python3'
}
export class BrowserVoice {
  constructor({ticket,submit,notify,spawnWorker=spawn,root=fileURLToPath(new URL('../../../',import.meta.url))}){
    Object.assign(this,{ticket,submit,notify,spawnWorker,root});this.active=null
  }
  async start({sessionId,id,handsFree=false}){
    if(!/^[a-f0-9-]{36}$/.test(id??'')||typeof sessionId!=='string')throw Error('Invalid voice identity')
    if(this.active)throw Error('Voice is already open. Close it before opening another voice session.')
    const worker=this.spawnWorker(voicePython(this.root),['-u',path.join(this.root,'services/voice/browser-client.py')],{
      stdio:['pipe','pipe','ignore'],env:{...process.env,AUGMENTOR_WINDOW_ID:'main'},
    })
    const active={id,sessionId,worker,submitted:new Set(),buffer:''};this.active=active
    const emit=event=>{if(this.active===active)this.notify({method:'voice.event',params:{id,sessionId,...event}})}
    worker.on('error',()=>{emit({type:'error',message:'The shared Voice engine could not start. Check the companion installation.'});this.close(active)})
    worker.on('exit',()=>{emit({type:'state',state:'closed',closed:true,status:'Voice disconnected'});this.close(active)})
    worker.stdin.on('error',()=>this.close(active))
    worker.stdout.on('data',data=>{
      active.buffer+=data.toString()
      if(active.buffer.length>65536){emit({type:'error',message:'Invalid voice response'});this.close(active);return}
      for(let end;(end=active.buffer.indexOf('\n'))>=0;){
        const line=active.buffer.slice(0,end);active.buffer=active.buffer.slice(end+1)
        try{
          const event=JSON.parse(line)
          if(event.type==='transcript')void this.transcript(active,event).catch(()=>{})
          else emit(event)
        }catch{emit({type:'error',message:'Invalid voice response'});this.close(active)}
      }
    })
    this.write(active,{action:'prepare',handsFree})
    // Return the lease immediately, so release/cancel/heartbeats work during preparation.
    void this.ticket(sessionId).then(ticket=>{
      if(this.active!==active)return
      if(ticket.protocol!=='resonant-voice/1'||ticket.sessionId!==sessionId||!/^ws:\/\/127\.0\.0\.1:\d+\/voice$/.test(ticket.url))throw Error('Invalid voice endpoint')
      this.write(active,{action:'start',ticket})
    }).catch(error=>{emit({type:'error',message:error.message});this.close(active)})
    return {id,sessionId}
  }
  write(active,value){if(this.active===active&&!active.worker.stdin.destroyed)active.worker.stdin.write(JSON.stringify(value)+'\n')}
  control({id,sessionId,action}){
    const active=this.active
    if(!active||id!==active.id||sessionId!==active.sessionId)throw Error('Voice belongs to another or closed conversation')
    if(!['heartbeat','begin','end','interrupt','close'].includes(action))throw Error('Unsupported voice control')
    if(action==='close')this.close(active)
    else this.write(active,{action})
    return {ok:true}
  }
  observe(sessionId,event){if(this.active?.sessionId===sessionId)this.write(this.active,{action:'observe',event})}
  async transcript(active,event){
    if(this.active!==active||event.sessionId!==active.sessionId||!/^[-a-f0-9]{36}$/.test(event.requestId??'')||active.submitted.has(event.requestId))return
    if(typeof event.text!=='string'||!event.text.trim()||event.text.length>8192){this.close(active);return}
    active.submitted.add(event.requestId)
    const id='resonant-voice:'+event.requestId
    let result
    try{result=await this.submit(active.sessionId,id,event.text)}
    catch(error){result={accepted:false,error:'Submission outcome is unknown. Check the conversation before retrying. '+error.message}}
    this.write(active,{action:'submission',result:{...result,id}})
  }
  close(active=this.active){
    if(!active||this.active!==active)return
    this.write(active,{action:'close'});this.active=null
    active.worker.stdin.end()
    const timer=setTimeout(()=>active.worker.kill(),2000);timer.unref?.()
    active.worker.once('exit',()=>clearTimeout(timer))
    this.notify({method:'voice.event',params:{id:active.id,sessionId:active.sessionId,type:'state',state:'closed',closed:true,status:'Voice off'}})
  }
}

export function voicePreferences(value,root=fileURLToPath(new URL('../../../',import.meta.url))){
  return new Promise((resolve,reject)=>{
    const child=spawn(voicePython(root),[path.join(root,'services/voice/preferences.py')],{stdio:['pipe','pipe','ignore'],env:{...process.env,AUGMENTOR_WINDOW_ID:'main'}})
    let output='';const timer=setTimeout(()=>{child.kill();reject(Error('Voice settings did not respond.'))},25000)
    child.on('error',error=>{clearTimeout(timer);reject(error)})
    child.stdin.on('error',()=>{})
    child.stdout.on('data',data=>{output+=data;if(output.length>1024*1024)child.kill()})
    child.on('close',code=>{clearTimeout(timer);try{const result=JSON.parse(output);if(code||result.error)throw Error(result.error??'Voice settings failed');resolve(result)}catch(error){reject(error)}})
    child.stdin.end(JSON.stringify(value))
  })
}
