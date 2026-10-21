// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

const modes=[
  {value:'read-only',name:'Read only',description:'Read pages and take snapshots. Navigation, typing and clicks are blocked.'},
  {value:'workspace-write',name:'Ask before actions',description:'Ask you before navigating, typing or clicking.'},
  {value:'danger-full-access',name:'Full access',description:'No per-action approval. Browser target scopes and limits still apply.'},
]
const label=value=>modes.find(row=>row.value===value)?.name??'unavailable'

/** One authoritative, revision-guarded permission snapshot per live chat. */
export function createApprovalMode({send,document,window,anchor,entry,isHistory,onError}){
  let state={},identity='',epoch=0,snapshot=null,defaults=null,menu=null,scope='session',busy=false,error='',readTicket=0
  const standalone=()=>['ah','pi'].includes(state.harness)
  const available=()=>standalone()&&state.phase==='ready'&&state.capabilities?.sessionPermissions===true&&!isHistory()
  const valid=token=>token===epoch&&!isHistory()
  const heading=()=>scope==='session'?'This chat':'Default for future chats'
  function badge(){
    const text=standalone()?`Approval mode: ${available()?label(snapshot?.currentValue):'unavailable'}`:'Approval mode — new chat default'
    entry.textContent=text
    anchor.title=text+' — More → Approval mode to change'
  }
  function close(){menu?.remove();menu=null}
  function render(){
    badge();if(!menu)return
    menu.replaceChildren()
    const element=(tag,text,cls)=>{const e=document.createElement(tag);e.textContent=text;if(cls)e.className=cls;return e}
    if(standalone()){
      const scopes=element('div','','access-scopes')
      for(const [value,text] of [['session','This chat'],['default','Future chats']]){
        const b=element('button',text,'access-scope');b.type='button';b.dataset.scope=value;b.setAttribute('aria-pressed',String(scope===value));b.disabled=busy
        b.onclick=e=>{e.stopPropagation();scope=value;error='';render();void load()};scopes.append(b)
      }menu.append(scopes)
    }
    menu.append(element('div',heading(),'access-head'))
    const status=element('div',error||(busy?'Loading…':scope==='session'?(available()?(snapshot?'Changes apply to this chat only.':'Open an idle chat to load its permission mode.'):'Open a ready standalone Harness or Pi chat.'):'Used when creating future chats. Existing chats keep their own mode.'),'access-status')
    status.setAttribute('role','status');menu.append(status)
    const value=scope==='session'?snapshot?.currentValue:defaults?.value?.defaultPreset
    for(const mode of modes){
      const b=element('button','','access-opt'+(value===mode.value?' current':''));b.type='button';b.dataset.preset=mode.value;b.setAttribute('aria-pressed',String(value===mode.value))
      b.disabled=busy||state.phase!=='ready'||isHistory()||(scope==='session'?(!available()||!snapshot||!snapshot.canSelect||state.running):!defaults)
      b.append(element('span',(value===mode.value?'✓ ':'')+mode.name,'a-name'),element('span',standalone()?mode.description:'Changes the DSH default for newly created chats.','a-desc'))
      b.onclick=e=>{e.stopPropagation();void choose(mode.value)};menu.append(b)
    }
    const r=anchor.getBoundingClientRect();menu.style.top=`${Math.max(8,Math.min(r.bottom+6,window.innerHeight-menu.offsetHeight-8))}px`
    menu.style.left=`${Math.max(8,Math.min(r.left,window.innerWidth-menu.offsetWidth-8))}px`
  }
  async function load(){
    const token=epoch,ticket=++readTicket,target=scope;busy=true;render()
    try{
      if(target==='session'){
        if(!available())return
        const reply=await send('permission',{action:'session',sourceSession:state.sessionId})
        if(!valid(token)||ticket!==readTicket)return
        if(!reply?.ok)throw Error(reply?.error??'Cannot read current chat permissions.')
        snapshot=reply.result
      }else{
        const reply=await send('settings/describe',{ns:'permission'})
        if(!valid(token)||ticket!==readTicket)return
        if(!reply?.ok)throw Error(reply?.error??'Cannot read permission defaults.')
        defaults=reply.value?.namespaces?.find(row=>row.ns==='permission')??null
        // Preserve DSH's established first-run Manual default. Never write a
        // Harness default while merely reading an existing chat's permissions.
        if(state.harness==='dsh'&&defaults&&defaults.value?.defaultPreset==null){
          const saved=await send('settings/mutate',{ns:'permission',ops:[{op:'set',path:['defaultPreset'],value:'workspace-write'}],expectedRevision:defaults.revision})
          if(!valid(token)||ticket!==readTicket)return
          if(!saved?.ok)throw Error(saved?.error??'Cannot initialize the DSH default.')
          defaults={...defaults,value:{...defaults.value,defaultPreset:'workspace-write'},revision:saved.value?.revision??defaults.revision}
        }
      }
    }catch(e){if(valid(token)&&ticket===readTicket){error=e.message;if(target==='session')snapshot=null;else defaults=null}}
    finally{if(valid(token)&&ticket===readTicket){busy=false;render()}}
  }
  async function choose(value){
    const token=epoch,target=scope,sid=state.sessionId,current=target==='session'?snapshot?.currentValue:defaults?.value?.defaultPreset
    if(busy||value===current||!valid(token))return
    if(value==='danger-full-access'&&!window.confirm(`Enable Full access for ${target==='session'?'this chat':'future chats'}?\n\nNew actions will not ask for approval. Browser target scopes and limits still apply.`))return
    if(!valid(token))return
    busy=true;error='';render()
    try{
      const reply=target==='session'?await send('permission',{action:'select',sourceSession:sid,preset:value,expectedRevision:snapshot.revision}):await send('settings/mutate',{ns:'permission',ops:[{op:'set',path:['defaultPreset'],value}],expectedRevision:defaults.revision})
      if(!valid(token))return
      if(!reply?.ok)throw Error(reply?.error??'Permission change failed.')
    }catch(e){if(valid(token)){error=e.message;onError('Approval mode: '+e.message)}}
    finally{if(valid(token))await load()}
  }
  function update(next){
    const wasRunning=state.running;state={...state,...next};const key=JSON.stringify([state.harness,state.sessionId,state.phase,state.capabilities?.sessionPermissions,!!isHistory()])
    if(key!==identity){identity=key;epoch++;readTicket++;snapshot=null;defaults=null;busy=false;error='';close();badge();if(available())void load()}
    else {render();if(wasRunning&&!state.running&&available())void load()}
  }
  document.addEventListener('click',e=>{if(!menu?.contains(e.target)&&!entry.contains(e.target)&&!anchor.contains(e.target))close()})
  document.addEventListener('keydown',e=>{if(e.key==='Escape')close()})
  return {update,close,open(){close();scope=standalone()?'session':'default';error='';menu=document.createElement('div');menu.id='access-menu';menu.setAttribute('aria-label','Approval mode');menu.onclick=e=>e.stopPropagation();document.body.append(menu);render();void load()}}
}
