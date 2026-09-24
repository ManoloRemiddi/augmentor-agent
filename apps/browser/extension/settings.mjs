// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {homeSettings} from './home.mjs'

import {formattingFields, formattingDefaults, appearanceFields, readAppearance, saveAppearance, resetAppearance, watchAppearance} from './appearance.mjs'
import {modelSetupDialog} from './setup.mjs'
import {dshSetupDialog} from './dsh-setup.mjs'
import {memoryDialog} from './memory.mjs'
import {promptEditor} from './prompt-editor.mjs'
import {supportDialog} from './support.mjs'

const send=(type,payload={})=>chrome.runtime.sendMessage({type,...payload})
const make=(tag,text)=>{const e=document.createElement(tag);if(text)e.textContent=text;return e}
const error=document.querySelector('#page-error')
const fail=e=>{error.hidden=false;error.textContent=e.message||String(e)}
const button=(parent,label,fn)=>{const b=make('button',label);b.type='button';b.onclick=()=>Promise.resolve().then(fn).catch(fail);parent.append(b);return b}
let state={},checking=false,closed=false
const sections=new Map()
const definitions=[
  ['voice','Voice','Shared with the floating Augmentor window.','M9 3h6v10H9zM5 10v3a7 7 0 0 0 14 0v-3M12 20v3'],
  ['appearance','Colours','Changes apply immediately.','M12 3a9 9 0 1 0 0 18h1a2 2 0 0 0 1-4 2 2 0 0 1 1-4h2a4 4 0 0 0 4-4c0-3-4-6-9-6ZM7 10h.01M10 6h.01M15 6h.01'],
  ['models','Models','Choose the model Augmentor uses.','M9 3v6m6-6v6M6 9h12v2a6 6 0 0 1-12 0ZM12 17v4'],
  ['harnesses','Harnesses','Choose what powers your browser agent.','M4 7h16M4 17h16M8 4v6m8 4v6'],
  ['prompts','Prompt library','Reusable prompts, shared with Augmentor Agent and both harnesses. Type / in chat to use one.','M5 3h14v18H5zM8 8h8M8 12h8M8 16h4'],
  ['home','Home','Connect your NAS and use Home in your Augmentor conversations.','M3 10l9-7 9 7v11H3z'],
  ['memory','Memories','Shared across your browser and Linux agents.','M4 5c0-4 16-4 16 0s-16 4-16 0v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0'],
  ['support','Support','Version information and a report you can review before sharing.','M12 11v6m0-10v1M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0'],
]
for(const [id,label,description,path] of definitions){
  const link=make('a');link.href='#'+id;link.id='nav-'+id
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');svg.setAttribute('stroke-width','1.6');svg.setAttribute('stroke-linecap','round');svg.setAttribute('stroke-linejoin','round');svg.setAttribute('aria-hidden','true')
  const shape=document.createElementNS(svg.namespaceURI,'path');shape.setAttribute('d',path);svg.append(shape);link.append(svg,document.createTextNode(label));document.querySelector('nav').append(link)
  const section=make('section');section.id='section-'+id;section.hidden=true;section.setAttribute('aria-labelledby','heading-'+id)
  const heading=make('h1',label);heading.id='heading-'+id
  const intro=make('p',description);intro.className='description';const body=make('div');body.className='section-body';section.append(heading,intro,body);document.querySelector('#sections').append(section)
  sections.set(id,{section,body,link,mounted:false})
}
document.querySelector('#version').textContent='Version '+chrome.runtime.getManifest().version
function appearance(container){
  const theme=make('div');theme.className='card';theme.append(make('h2','Theme'));const choices=make('div');choices.className='theme-choices';theme.append(choices)
  const themeButtons={};for(const id of ['dark','light'])themeButtons[id]=button(choices,id==='dark'?'Dark':'Light',async()=>{await saveAppearance({...readAppearance(),theme:id});sync()})
  const colours=make('div');colours.className='card';colours.append(make('h2','Colours'));const grid=make('div');grid.className='colour-grid';colours.append(grid)
  const controls=new Map()
  for(const [key,,label,min,max] of appearanceFields){
    const row=make('label',label),out=make('output'),input=make('input');input.type='range';input.min=min;input.max=max;input.step=1;input.id=key;input.setAttribute('aria-label',label);out.htmlFor=key
    input.oninput=()=>{saveAppearance({...readAppearance(),[key]:Number(input.value)}).catch(fail);sync()}
    row.append(out,input);grid.append(row);controls.set(key,{input,out})
  }
  const format=make('div');format.className='card formatting-colours';format.append(make('h2','Formatting colours'))
  const formatControls=new Map()
  for(const [key,label] of formattingFields){
    const row=make('label',label),input=make('input');input.type='color';input.setAttribute('aria-label',label)
    input.oninput=()=>{const value=readAppearance();saveAppearance({...value,formatColours:{...value.formatColours,[key]:input.value}}).catch(fail)}
    row.append(input);format.append(row);formatControls.set(key,input)
  }
  const preview=make('div');preview.className='card';preview.append(make('h2','Preview'));const sample=make('div');sample.className='preview'
  const user=make('p','Help me make this clearer.');user.className='sample-user';const reply=make('div');reply.className='sample-agent';reply.append(make('strong','Augmentor'),make('p','A little less clutter. More room for your ideas.'));sample.append(user,reply);preview.append(sample)
  const note=make('p','The accent also colours the overlay while Augmentor uses the browser.');note.className='help';colours.append(note)
  container.append(theme,colours,format,preview);button(container,'Reset colours',async()=>{await saveAppearance(resetAppearance());sync()})
  function sync(){const values=readAppearance();for(const [key,input] of formatControls)input.value=values.formatColours[key]||formattingDefaults(values.theme)[key];for(const [key,{input,out}] of controls){input.value=values[key];out.value=String(values[key])}for(const [id,b] of Object.entries(themeButtons))b.setAttribute('aria-pressed',String(values.theme===id))}
  watchAppearance(sync)
}
function advanced(parent,label){const detail=make('details');detail.className='advanced';detail.append(make('summary',label));const body=make('div');body.className='advanced-body';detail.append(body);parent.append(detail);return body}
function showModels(container){
  const active=make('p');active.id='active-model';container.append(active)
  const pi=make('div');pi.id='pi-model-settings';const dsh=make('div');dsh.id='dsh-model-settings';dsh.className='card';dsh.append(make('h2','DeepSeek Harness models'),make('p','DSH manages its model providers. Add or edit them in DSH, then refresh the model picker in Augmentor.'))
  button(dsh,'Open DSH model settings',async()=>{const r=await send('promptSettings');if(!r.ok)throw Error(r.error)})
  container.append(pi,dsh)
  const mountPi=()=>{const body=advanced(pi,'Connect another model');if(!state.model?.model)body.parentElement.open=true;const dialog=modelSetupDialog(document,send,body);dialog?.addEventListener('close',()=>{if(closed)return;const note=make('p','Model saved. Use the chat model picker to choose an existing model, or connect another below.');note.className='saved-note';pi.replaceChildren(note);mountPi()},{once:true})}
  container.update=()=>{
    pi.hidden=state.harness!=='pi';dsh.hidden=state.harness!=='dsh'
    active.textContent='Current model: '+(state.model?.model||'Not connected')
    if(state.harness==='pi'&&!pi.querySelector('.model-setup'))mountPi()
  };container.update()
}
function showHarnesses(container){
  const card=make('div');card.className='card';card.append(make('h2','Browser harness'))
  const select=make('select');select.setAttribute('aria-label','Browser harness');for(const [value,label] of [['','Choose DSH or Pi'],['pi','Pi'],['dsh','DeepSeek Harness']]){const opt=make('option',label);opt.value=value;opt.disabled=!value;select.append(opt)}
  select.onchange=async()=>{select.disabled=true;try{const r=await send('harness/select',{harness:select.value});if(!r.ok)throw Error(r.error);await refresh()}catch(e){fail(e)}finally{select.disabled=!!state.running}}
  card.append(select);container.append(card)
  const connection=advanced(container,'DSH connection settings')
  const mount=()=>{const dialog=dshSetupDialog(document,send,connection);dialog?.addEventListener('close',()=>{if(!closed){connection.replaceChildren(make('p','DSH connection saved.'));mount()}},{once:true})};mount()
  container.update=()=>{select.value=state.harness||'';select.disabled=!!state.running};container.update()
}
function showMemory(container){
  const card=make('div');card.className='card onboarding-card';card.append(make('h2','Let Augmentor set up memory'),make('p','Start a guided conversation. Augmentor checks your computer and handles the setup, asking only for missing choices or credentials.'))
  const status=make('p');status.className='help';status.setAttribute('role','status')
  const start=button(card,'Set up with Augmentor',async()=>{
    start.disabled=true;status.textContent='Opening Augmentor Agent…'
    const requestId=sessionStorage.getItem('memory-onboarding-id')||crypto.randomUUID();sessionStorage.setItem('memory-onboarding-id',requestId)
    try{const r=await send('onboarding/start',{topic:'memory',requestId});if(!r?.ok)throw Error(r?.error||'Could not open setup');status.textContent='Continue in Augmentor Agent.';start.textContent='Continue setup'}
    catch(e){status.textContent=e.message}
    finally{start.disabled=false}
  });card.append(status);container.append(card)
  const manual=advanced(container,'Advanced · manual setup and stored memories')
  // Mount on demand: opening Memories should not ask for technical inputs.
  manual.parentElement.addEventListener('toggle',()=>{if(manual.parentElement.open&&!manual.querySelector('dialog'))memoryDialog(document,send,()=>({surface:'browser',harness:state.harness,...(state.sessionId?{sessionId:state.sessionId}:{})}),manual)})
}
async function showVoice(container){
  const response=await send('voice/preferences');if(!response?.ok)throw Error(response?.error||'Voice is unavailable')
  const data=response.result,fields={}
  const add=(key,label,input)=>{const row=make('label',label);row.append(input);container.append(row);fields[key]=input;return input}
  const enabled=add('enabled','Enable Voice',make('input'));enabled.type='checkbox';enabled.checked=data.enabled
  const voices=add('voiceId','Speaking voice',make('select'))
  for(const row of data.voices){const option=make('option',row.name);option.value=row.id;voices.append(option)}voices.value=data.values.voiceId
  for(const [key,label,min,max,step,value] of [['speed','Speaking speed',.75,1.5,.05,data.values.speed],['volume','Output volume',0,1,.05,data.values.volume],['pauseMs','Pause before sending (milliseconds)',400,2000,50,data.pauseMs]]){
    const input=add(key,label,make('input'));input.type='number';input.min=min;input.max=max;input.step=step;input.value=value
  }
  const mode=add('mode','Conversation mode',make('select'))
  for(const [value,label] of [['manual','Hold or slide to lock'],['hands-free','Hands-free conversation']]){const option=make('option',label);option.value=value;mode.append(option)}mode.value=data.mode
  const note=make('p','Hold to record · Slide left to lock · Slide right for hands-free · Escape cancels. Changes apply when Voice next opens.');container.append(note)
  button(container,'Save',async()=>{
    const settings={voiceId:voices.value,enabled:enabled.checked,mode:mode.value,speed:Number(fields.speed.value),volume:Number(fields.volume.value),pauseMs:Number(fields.pauseMs.value)}
    const reply=await send('voice/preferences',{action:'save',settings});if(!reply?.ok)throw Error(reply?.error||'Could not save voice settings')
    note.textContent='Saved for both interfaces. Changes apply when Voice next opens.'
  })
}
function mount(id){
  const row=sections.get(id);if(row.mounted)return
  if(id!=='appearance'&&!['ready','needs-setup'].includes(state.phase)){
    row.body.textContent=state.error||'Connecting to the Augmentor companion… Settings will appear here when it is available.'
    return
  }
  row.body.replaceChildren();row.mounted=true
  if(id==='appearance')appearance(row.body)
  if(id==='models')showModels(row.body)
  if(id==='harnesses')showHarnesses(row.body)
  if(id==='prompts')promptEditor(document,async request=>{const r=await send('prompts',{request});if(!r?.ok)throw Error(r?.error||'Prompt library unavailable');return r.library},()=>{},row.body)
  if(id==='home')homeSettings(document,send,row.body)
  if(id==='memory')showMemory(row.body)
  if(id==='voice')void showVoice(row.body).catch(fail)
  if(id==='support'){
    const version=make('div');version.className='card';version.append(make('h2','Augmentor '+chrome.runtime.getManifest().version),make('p','This preview is updated with the Augmentor installer. The companion and extension must use matching versions.'));row.body.append(version)
    void supportDialog(document,send,row.body).catch(fail)
  }
}
function navigate(){
  const id=sections.has(location.hash.slice(1))?location.hash.slice(1):'appearance'
  for(const [key,row] of sections){row.section.hidden=key!==id;if(key===id)row.link.setAttribute('aria-current','page');else row.link.removeAttribute('aria-current')}
  mount(id)
}
async function refresh(){
  if(checking||closed)return;checking=true
  try{
    state=await send('connect')
    document.querySelector('#connection').textContent=({dsh:'DSH',pi:'Pi'}[state.harness]||'Harness')+' · '+({ready:'Connected','needs-setup':'Setup needed',connecting:'Connecting…'}[state.phase]||state.phase||'Connecting…')
    for(const row of sections.values())row.body.update?.()
    navigate()
  }catch(e){document.querySelector('#connection').textContent='Companion unavailable';fail(e)}finally{checking=false}
}
watchAppearance();window.addEventListener('hashchange',navigate);navigate();void refresh()
const timer=setInterval(refresh,1500)
window.addEventListener('pagehide',()=>{closed=true;clearInterval(timer);for(const dialog of document.querySelectorAll('dialog[open]'))dialog.close()},{once:true})
