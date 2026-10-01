// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

/** Presentation only: the shared host owns admission, promotion and delivery. */
export function createQueue({container,input,send}) {
  let sessionId, enabled=false, online=false, running=false, activeTurnId=null, tail=Promise.resolve()
  const sessions=new Map()
  const current=()=>{
    if(!sessions.has(sessionId))sessions.set(sessionId,{revision:-1,items:[],pending:new Map(),changing:new Set(),errors:new Map(),delivered:new Set()})
    return sessions.get(sessionId)
  }
  function render(){
    container.replaceChildren()
    const state=current(),rows=[...state.items.map(item=>({id:item.id,text:item.message.content.filter(p=>p.type==='text').map(p=>p.text).join('\n'),label:item.stateLabel??(item.placement==='steering'?'Steering…':'Queued'),item})),...Array.from(state.pending,([id,p])=>({id,...p}))]
    container.hidden=!enabled||!rows.length
    for(const row of rows){
      const element=container.ownerDocument.createElement('div');element.className='queue-row';element.dataset.queueId=row.id
      const label=container.ownerDocument.createElement('span');label.className='queue-text'
      const status=state.errors.get(row.id)??row.label
      label.textContent=(status==='Queued'?'':status+' · ')+row.text;label.title=status+'\n'+row.text;element.append(label)
      function button(text,action,allowed){const b=container.ownerDocument.createElement('button');b.type='button';b.textContent=text;b.disabled=!allowed;b.setAttribute('aria-label',text==='×'?'Remove queued prompt':text+' queued prompt');b.addEventListener('click',action);element.append(b)}
      if(row.item){
        button('Steer',()=>act(row.id,'steer'),online&&running&&Boolean(activeTurnId)&&row.item.canSteer===true&&!state.changing.has(row.id))
        button('×',()=>act(row.id,'remove'),online&&row.item.canRemove===true&&!state.changing.has(row.id))
      }else if(row.failed){
        button('Copy',()=>{void input.ownerDocument.defaultView.navigator.clipboard.writeText(row.text).catch(()=>{})},true)
        button('×',()=>{state.pending.delete(row.id);render()},true)
      }
      container.append(element)
    }
  }
  function update(message,viewing=false){
    if(message.sessionId&&message.sessionId!==sessionId){sessionId=message.sessionId;activeTurnId=null}
    enabled=message.harness==='codex'&&message.capabilities?.queue===true&&!viewing
    online=message.phase==='ready';running=message.running===true
    const state=current()
    if(message.queue?.sessionId===sessionId&&Number.isSafeInteger(message.queue.revision)&&message.queue.revision>=state.revision){
      state.revision=message.queue.revision
      activeTurnId=message.queue.activeTurnId
      state.items=message.queue.items.filter(item=>!state.delivered.has(item.rpcId))
      for(const item of state.items)state.pending.delete(item.rpcId)
    }
    const entries=message.log??(message.entry?[message.entry]:[])
    for(const entry of entries){
      const event=entry.event,id=event?.data?.source?.rpcId
      if(entry.sessionId===sessionId&&event?.type==='user/message'&&event.data.source.kind==='user'&&id){state.delivered.add(id);state.pending.delete(id);state.items=state.items.filter(item=>item.rpcId!==id)}
    }
    if(state.delivered.size>2048)state.delivered=new Set([...state.delivered].slice(-1024))
    render()
  }
  async function act(itemId,action){
    const state=current(),target=sessionId,expectedTurnId=activeTurnId
    const item=state.items.find(item=>item.id===itemId)
    if(!enabled||!online||!item||state.changing.has(itemId)||!(action==='steer'?running&&expectedTurnId&&item.canSteer:item.canRemove))return
    state.changing.add(itemId);render()
    const task=tail.then(async()=>{
      try{
        if(target!==sessionId||!enabled||!online)throw Error('Conversation changed before queue action.')
        const result=await send('queue/action',{sessionId:target,itemId,action,expectedTurnId});if(!result?.accepted)throw Error(result?.error??'Queue action was not confirmed.');state.errors.delete(itemId)
      }catch(error){state.errors.set(itemId,error.message)}
      finally{state.changing.delete(itemId);render()}
    })
    tail=task.catch(()=>{});return task
  }
  function submit(){
    if(!enabled||!online||!running)return Promise.resolve(false)
    const text=input.value.trim();if(!text)return Promise.resolve(false)
    const id=globalThis.crypto.randomUUID(),target=sessionId,state=current()
    state.pending.set(id,{text,label:'Queuing…'});input.value='';input.dispatchEvent(new input.ownerDocument.defaultView.Event('input',{bubbles:true}));render()
    const task=tail.then(async()=>{
      try{
        if(target!==sessionId||!enabled||!online)throw Error('Conversation changed before submission.')
        const result=await send('queue/prompt',{sessionId:target,requestId:id,text})
        if(!result?.accepted)throw Error(result?.error??'Submission was not confirmed.')
        const pending=state.pending.get(id);if(pending)pending.label='Queued'
      }catch(error){const pending=state.pending.get(id);if(pending){pending.label='Not confirmed — '+error.message;pending.failed=true}}
      render();return true
    })
    tail=task.catch(()=>{});return task
  }
  return {update,submit,act,get enabled(){return enabled}}
}
