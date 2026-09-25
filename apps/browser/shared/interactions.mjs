// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto'
// Same product broker as Desktop: one presenter, explicit answers, no retries.
export class BrowserInteractions {
  constructor(operation,notify){Object.assign(this,{operation,notify});this.owner=randomUUID();this.session=null;this.pending=new Map();this.attempted=new Set();this.timer=null;this.closed=false}
  request(operation,values={},sessionId=this.session){return this.operation({action:'interaction',surface:'browser',sessionId,owner:this.owner,operation,...values})}
  async claim(sessionId){
    if(this.closed)throw Error('Interaction connection closed')
    if(this.session===sessionId)return
    if(this.session)await this.release()
    await this.request('claim',{},sessionId)
    if(this.closed){await this.request('release',{},sessionId);return}
    this.session=sessionId;await this.poll()
  }
  async poll(){
    const session=this.session
    try{
      const {pending}=await this.request('poll')
      if(this.closed||this.session!==session)return
      const rows=new Map(pending.map(row=>[row.id,row]))
      for(const id of this.pending.keys())if(!rows.has(id))this.notify({method:'interaction.resolved',params:{rpcId:id,sessionId:session}})
      for(const row of rows.values())if(!this.pending.has(row.id)&&!this.attempted.has(row.id))this.notify({id:row.id,method:row.kind+'.requested',params:{...row.payload,sessionId:session,approvalId:row.id}})
      this.pending=rows
      this.timer=setTimeout(()=>void this.poll(),500);this.timer.unref?.()
    }catch(error){
      if(!this.closed)this.notify({method:'session.error',params:{sessionId:session,message:'Approval connection lost. Check the conversation before retrying. '+error.message}})
      await this.release().catch(()=>{})
    }
  }
  async answer(id,value){
    const row=this.pending.get(id)
    if(!row||this.attempted.has(id)||this.closed)throw Error('This interaction is no longer pending')
    this.attempted.add(id);this.pending.delete(id)
    const answer=row.kind==='approval'?value.outcome:value.answer
    await this.request('answer',{id,value:answer})
    this.notify({method:'interaction.resolved',params:{rpcId:id,sessionId:this.session}})
  }
  async release(){
    clearTimeout(this.timer)
    const session=this.session;this.session=null
    for(const id of this.pending.keys())this.notify({method:'interaction.resolved',params:{rpcId:id,sessionId:session}})
    this.pending.clear()
    if(session)await this.request('release',{},session)
  }
  close(){this.closed=true;void this.release().catch(()=>{})}
}
