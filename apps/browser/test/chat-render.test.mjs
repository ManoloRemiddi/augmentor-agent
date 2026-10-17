// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

import test from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {marked} from 'marked'
import {createChatUI} from '../extension/chat-render.js'

test('streamed rendering preserves negotiated queue Send and still blocks unsupported or disconnected sending',t=>{
 const dom=new JSDOM('<div id="log"></div><button id="send"></button>',{pretendToBeVisual:true});globalThis.window=dom.window;globalThis.document=dom.window.document
 globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window);globalThis.cancelAnimationFrame=window.cancelAnimationFrame.bind(window);window.marked=marked
 const log=document.querySelector('#log'),send=document.querySelector('#send'),ui=createChatUI({log,send});t.after(()=>{ui.clear();dom.window.close()})
 let seq=0;const stream=()=>ui.applyLog([{kind:'event',event:{seq:++seq,type:'assistant/chunk',data:{chunk:{type:'text-delta',text:'Partial '}}}}])
 ui.setState({phase:'ready',running:true,canQueue:true});stream();assert.equal(send.disabled,false)
 ui.setState({submitting:true});stream();assert.equal(send.disabled,true)
 ui.setState({submitting:false,canQueue:false});stream();assert.equal(send.disabled,true)
 ui.setState({canQueue:true,phase:'error'});stream();assert.equal(send.disabled,true)
})

test('persisted Branch/Edit buttons reflect ready idle state and suppress guarded clicks',t=>{
 const dom=new JSDOM('<div id="log"></div>',{pretendToBeVisual:true});globalThis.window=dom.window;globalThis.document=dom.window.document
 globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window);globalThis.cancelAnimationFrame=window.cancelAnimationFrame.bind(window);window.marked=marked
 let allowed=true;const calls=[],log=document.querySelector('#log'),ui=createChatUI({log,actionEnabled:()=>allowed,onMessageAction:(...args)=>calls.push(args)});t.after(()=>{ui.clear();dom.window.close()})
 ui.setState({phase:'ready',running:true,canQueue:true});ui.applyLog([{kind:'event',event:{seq:1,type:'user/message',data:{source:{kind:'user'},content:[{type:'text',text:'Input'}]}}},{kind:'event',event:{seq:2,type:'assistant/message',data:{message:{content:[{type:'text',text:'Reply'}]}}}}])
 const edit=log.querySelector('.msg-edit'),branch=log.querySelector('.msg-branch');assert(edit&&branch)
 const blocked=()=>{for(const button of [edit,branch]){assert.equal(button.disabled,true);button.click();button.dispatchEvent(new window.Event('click'))}}
 blocked();assert.equal(calls.length,0);ui.setState({running:false});assert.equal(edit.disabled,false);assert.equal(branch.disabled,false);branch.click();assert.deepEqual(calls,[['branch',2,'Reply']])
 ui.setState({submitting:true});blocked();ui.setState({submitting:false,phase:'error'});blocked();allowed=false;ui.setState({phase:'ready'});blocked();assert.equal(calls.length,1)
})

test('prepared Pi input displays the original submitted text without replacing effective native content',t=>{
 const dom=new JSDOM('<div id="log"></div>',{pretendToBeVisual:true});globalThis.window=dom.window;globalThis.document=dom.window.document
 globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window);globalThis.cancelAnimationFrame=window.cancelAnimationFrame.bind(window);window.marked=marked
 const log=document.querySelector('#log'),ui=createChatUI({log});t.after(()=>{ui.clear();dom.window.close()})
 const event={seq:1,type:'user/message',data:{source:{kind:'user'},submittedContent:[{type:'text',text:'/template original'}],content:[{type:'text',text:'Prepared instructions'}]}}
 ui.applyLog([{kind:'event',event}]);assert(log.textContent.includes('/template original'));assert(!log.textContent.includes('Prepared instructions'));assert.equal(event.data.content[0].text,'Prepared instructions')
})

test('inherited Pi input renders without confirming an optimistic child submission with the same text',t=>{
 const dom=new JSDOM('<div id="log"></div>',{pretendToBeVisual:true});globalThis.window=dom.window;globalThis.document=dom.window.document
 globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window);globalThis.cancelAnimationFrame=window.cancelAnimationFrame.bind(window);window.marked=marked
 const log=document.querySelector('#log'),ui=createChatUI({log});t.after(()=>{ui.clear();dom.window.close()})
 const pending=ui.pendingPrompt('Same submission'),event=(seq,origin)=>({kind:'event',sessionId:'child',event:{seq,type:'user/message',data:{source:{kind:'user',sessionId:origin},content:[{type:'text',text:'Same submission'}]}}})
 ui.applyLog([event(1,'parent')]);assert.equal(pending.confirmed,false);assert(log.contains(pending.node));assert.equal(log.querySelectorAll('.msg.user:not(.pending)').length,1)
 ui.applyLog([event(2,'child')]);assert.equal(pending.confirmed,true);assert(!log.contains(pending.node));assert.equal(log.querySelectorAll('.msg.user').length,2)
})

test('handled-input status clears only the originating optimistic prompt without inventing human/model messages',t=>{
 const dom=new JSDOM('<div id="log"></div>',{pretendToBeVisual:true});globalThis.window=dom.window;globalThis.document=dom.window.document
 globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window);globalThis.cancelAnimationFrame=window.cancelAnimationFrame.bind(window);window.marked=marked
 const log=document.querySelector('#log'),ui=createChatUI({log});t.after(()=>{ui.clear();dom.window.close()})
 const pending=ui.pendingPrompt('Handled'),event=(seq,origin)=>({kind:'event',sessionId:'child',event:{seq,type:'runtime/notice',data:{message:'Handled by extension',disposition:'input-handled',source:{kind:'user',sessionId:origin},submittedContent:[{type:'text',text:'Handled'}]}}})
 ui.applyLog([event(1,'parent')]);assert.equal(pending.confirmed,false);ui.applyLog([event(2,'child')]);assert.equal(pending.confirmed,true);assert.equal(log.querySelectorAll('.msg.user,.msg.assistant').length,0);assert.equal(log.querySelectorAll('.msg.status').length,2)
})

test('workspace thinking preference applies to live reasoning, preserves manual choices and leaves history collapsed',t=>{
 const dom=new JSDOM('<div id="log"></div>',{pretendToBeVisual:true})
 globalThis.window=dom.window;globalThis.document=dom.window.document
 globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
 globalThis.cancelAnimationFrame=window.cancelAnimationFrame.bind(window);window.marked=marked
 const log=document.querySelector('#log'),ui=createChatUI({log});t.after(()=>{ui.clear();dom.window.close()})
 let seq=0
 const event=(type,data={})=>ui.applyLog([{kind:'event',event:{seq:seq++,type,data}}])
 const think=()=>event('assistant/chunk',{chunk:{type:'reasoning-delta',text:'Thought'}})
 ui.setThinkingPreference(false);think()
 const first=log.querySelector('.think');assert.equal(first.open,false)
 first.open=true;ui.setThinkingPreference(false);think();assert.equal(first.open,true,'unchanged preference preserves manual expansion')
 ui.setThinkingPreference(true);ui.setThinkingPreference(false);assert.equal(first.open,false)
 first.open=true;event('assistant/chunk',{chunk:{type:'text-delta',text:'Answer'}});assert.equal(first.open,false)
 event('assistant/message',{message:{content:[{type:'reasoning',text:'ThoughtThought'},{type:'text',text:'Answer'}]}})
 first.open=true;ui.setThinkingPreference(true);assert.equal(first.open,true,'finished history remains manually controlled')
 think();const second=log.querySelectorAll('.think')[1];assert.equal(second.open,true)
 second.open=false;think();assert.equal(second.open,false,'new chunks preserve manual collapse')
 second.open=true;ui.setState({running:false});assert.equal(second.open,false)
 ui.clear();event('assistant/message',{message:{content:[{type:'reasoning',text:'Saved thought'},{type:'text',text:'Saved answer'}]}})
 assert.equal(log.querySelector('.think').open,false)
 assert.equal(log.querySelector('.md').textContent.trim(),'Saved answer')
})

for (const delivery of ['live', 'reopen']) {
  test(`${delivery}: unsequenced DSH chunks paint before completion and replay once`, async t => {
    const dom = new JSDOM('<div id="log"></div>', {pretendToBeVisual:true})
    globalThis.window = dom.window; globalThis.document = dom.window.document
    globalThis.requestAnimationFrame = dom.window.requestAnimationFrame.bind(dom.window)
    globalThis.cancelAnimationFrame = dom.window.cancelAnimationFrame.bind(dom.window)
    window.marked = marked
    const {log: record, state} = await import('../extension/state.mjs')
    state.log = []
    const log = document.querySelector('#log'), ui = createChatUI({log})
    t.after(() => {ui.clear(); dom.window.close(); state.log = []})
    const start = record('event', {event:{seq:10,type:'turn/start',data:{}}})
    const chunk = text => record('event', {event:{type:'assistant/chunk',data:{chunk:{type:'text-delta',text}}}})
    const first = chunk('Once upon '), second = chunk('a moon.')
    if (delivery === 'live') {
      ui.applyLog([start, first])
      await new Promise(resolve => setTimeout(resolve, 40))
      assert.equal(log.querySelector('.assistant .md').textContent.trim(), 'Once upon')
      ui.applyLog([second])
    } else ui.applyLog(state.log)
    await new Promise(resolve => setTimeout(resolve, 40))
    assert.equal(log.querySelector('.assistant .md').textContent.trim(), 'Once upon a moon.')
    assert.ok(log.querySelector('.md.streaming'))
    assert.equal(ui.lastSeq, 10)
    ui.applyLog(state.log)
    await new Promise(resolve => setTimeout(resolve, 40))
    assert.equal(log.querySelector('.assistant .md').textContent.trim(), 'Once upon a moon.')
    ui.applyLog([record('event', {event:{seq:11,type:'assistant/message',data:{message:{content:[{type:'text',text:'Once upon a moon.'}]}}}})])
    assert.equal(log.querySelectorAll('.assistant').length, 1)
    assert.equal(log.querySelector('.assistant .md').textContent.trim(), 'Once upon a moon.')
    assert.equal(log.querySelector('.md.streaming'), null)
    assert.equal(ui.lastSeq, 11)
  })
}

for (const delivery of ['live','history']) {
  test(`${delivery}: internal context is hidden; real user text and the answer remain intact`,t=>{
    const dom=new JSDOM('<div id="log"></div>',{pretendToBeVisual:true})
    globalThis.window=dom.window;globalThis.document=dom.window.document
    globalThis.requestAnimationFrame=dom.window.requestAnimationFrame.bind(dom.window)
    globalThis.cancelAnimationFrame=dom.window.cancelAnimationFrame.bind(dom.window)
    window.marked=marked
    const log=document.querySelector('#log'),ui=createChatUI({log})
    t.after(()=>{ui.clear();dom.window.close()})
    const userText='Rewrite this sentence.\n<system-reminder>This is text I supplied.</system-reminder>'
    const message=(seq,source,text)=>({kind:'event',event:{seq,type:'user/message',data:{source,content:[{type:'text',text}]}}})
    const events=[
      message(0,{kind:'user'},userText),
      message(1,{kind:'agent-instructions',form:'instructions'},'INTERNAL workspace instructions'),
      message(2,{kind:'plugin',form:'snapshot'},'INTERNAL runtime context'),
      message(3,{kind:'future-context-source',form:'catalog'},'INTERNAL catalog'),
      {kind:'event',event:{seq:4,type:'assistant/chunk',data:{chunk:{type:'text-delta',text:'A clearer sentence.'}}}},
      {kind:'event',event:{seq:5,type:'assistant/message',data:{message:{content:[{type:'text',text:'A clearer sentence.'}]}}}},
      {kind:'event',event:{seq:6,type:'step/end',data:{turn:1,step:1}}},
    ]
    if(delivery==='live')for(const event of events)ui.applyLog([event])
    else ui.applyLog(events.filter(entry=>entry.event.type!=='assistant/chunk'))
    assert.equal(log.querySelectorAll('.msg.user').length,1)
    assert.match(log.querySelector('.msg.user .md').textContent,/This is text I supplied/)
    assert.doesNotMatch(log.textContent,/INTERNAL/)
    assert.equal(log.querySelector('.msg.assistant .md').textContent.trim(),'A clearer sentence.')
    assert.equal(ui.lastSeq,6)
    ui.applyLog(events);assert.equal(log.querySelectorAll('.msg.user').length,1)
    ui.applyLog([message(7,undefined,'A legacy human message')])
    assert.equal(log.querySelectorAll('.msg.user').length,2)
  })
}

for (const parserVersion of ['shipped','test']) {
  test(`${parserVersion}: rich Markdown and highlighted code preserve literal text`, async t => {
    const dom=new JSDOM('<div id="log"></div>',{pretendToBeVisual:true,runScripts:'outside-only'})
    globalThis.window=dom.window;globalThis.document=dom.window.document
    globalThis.requestAnimationFrame=dom.window.requestAnimationFrame.bind(dom.window)
    globalThis.cancelAnimationFrame=dom.window.cancelAnimationFrame.bind(dom.window)
    if(parserVersion==='shipped') {
      const {readFileSync}=await import('node:fs')
      window.eval(readFileSync(new URL('../extension/vendor/marked.min.js',import.meta.url),'utf8'))
    } else window.marked=marked
    const log=document.querySelector('#log'),ui=createChatUI({log})
    t.after(()=>{ui.clear();dom.window.close()})
    const text='# Report\n\n**World News**\n\n1. **A story** with *source notes*\n\n> A quotation\n\n```python\n# comment\nname = "🌞 <b>& hello"\nif True:\n    print(name, 42)\n```\n\n<script>alert(1)</script>\n\n[bad](javascript:alert) [bad title](javascript:alert "title") ![image](file:///etc/passwd)'
    ui.applyLog([{kind:'event',event:{seq:0,type:'assistant/chunk',data:{chunk:{type:'text-delta',text}}}}])
    await new Promise(resolve=>setTimeout(resolve,40))
    for(const delivery of ['stream','final']) {
      if(delivery==='final')ui.applyLog([{kind:'event',event:{seq:1,type:'assistant/message',data:{message:{content:[{type:'text',text}]}}}}])
      assert.equal(log.querySelector('h1').textContent,'Report')
      assert.equal(log.querySelector('strong').textContent,'World News')
      assert.equal(log.querySelector('blockquote').textContent.trim(),'A quotation')
      assert.ok(log.querySelector('ol li strong'))
      const code=log.querySelector('pre code')
      assert.ok(code.querySelector('.hljs-keyword'));assert.ok(code.querySelector('.hljs-string'))
      assert.equal(code.textContent,'# comment\nname = "🌞 <b>& hello"\nif True:\n    print(name, 42)\n')
      assert.equal(log.querySelector('script, img'),null)
      assert.equal(log.querySelector('a[href^="javascript:"]'),null)
    }
  })
}

for(const parserVersion of ['shipped','test']) test(`${parserVersion}: report spans preserve bold, local colour and source line breaks`,async t=>{
  const dom=new JSDOM('<div id="log"></div>',{pretendToBeVisual:true,runScripts:'outside-only'});globalThis.window=dom.window;globalThis.document=dom.window.document
  globalThis.requestAnimationFrame=dom.window.requestAnimationFrame.bind(dom.window);globalThis.cancelAnimationFrame=dom.window.cancelAnimationFrame.bind(dom.window);window.marked=marked
  if(parserVersion==='shipped'){const {readFileSync}=await import('node:fs');window.eval(readFileSync(new URL('../extension/vendor/marked.min.js',import.meta.url),'utf8'))}
  const log=document.querySelector('#log'),ui=createChatUI({log});t.after(()=>{ui.clear();dom.window.close()})
  const text='## World News\n\n**1.** <span style="color:#8BC34A">**Headline**</span> — Summary.\n*Source: BBC*\n\n**2.** Another item.\n\n<span style="color:red" onclick="evil()">Bad</span>\n\n```html\n<span style="color:#8BC34A">Literal</span>\n```'
  ui.applyLog([{kind:'event',event:{seq:1,type:'assistant/message',data:{message:{content:[{type:'text',text}]}}}}])
  assert.equal(log.querySelector('span[style] strong').textContent,'Headline')
  assert.equal(log.querySelector('span[style]').style.color,'rgb(139, 195, 74)')
  assert.ok(log.querySelector('p br'));assert.ok(log.querySelector('p em'))
  assert.equal(log.querySelector('[onclick]'),null)
  assert.ok(log.querySelector('code').textContent.includes('<span style="color:#8BC34A">Literal</span>'))
})

test('thinking remains expandable and each code copy excludes prose',async t=>{
  const dom=new JSDOM('<div id="log"></div>',{pretendToBeVisual:true});globalThis.window=dom.window;globalThis.document=dom.window.document
  globalThis.requestAnimationFrame=dom.window.requestAnimationFrame.bind(dom.window);globalThis.cancelAnimationFrame=dom.window.cancelAnimationFrame.bind(dom.window);window.marked=marked
  let copied;const descriptor=Object.getOwnPropertyDescriptor(globalThis,'navigator')
  Object.defineProperty(globalThis,'navigator',{configurable:true,value:{clipboard:{writeText:async text=>{copied=text}}}})
  const log=document.querySelector('#log'),ui=createChatUI({log});t.after(()=>{ui.clear();dom.window.close();if(descriptor)Object.defineProperty(globalThis,'navigator',descriptor);else delete globalThis.navigator})
  ui.applyLog([{kind:'event',event:{seq:1,type:'assistant/chunk',data:{chunk:{type:'reasoning-delta',text:'Checking details.'}}}}])
  await new Promise(resolve=>setTimeout(resolve,40))
  const thinking=log.querySelector('details.think');assert.ok(thinking);thinking.open=true
  assert.match(thinking.textContent,/Checking details/)
  ui.applyLog([{kind:'event',event:{seq:2,type:'assistant/message',data:{message:{content:[{type:'reasoning',text:'Checking details.'},{type:'text',text:'Explanation\n\n```python\nprint("🌞")\n```\n\nNext\n\n```sh\necho done\n```'}]}}}}])
  assert.ok(thinking.open);assert.equal(log.querySelectorAll('details.think').length,1)
  thinking.querySelector('.think-collapse').click();assert.equal(thinking.open,false)
  assert.equal(document.activeElement,thinking.querySelector('summary'))
  const buttons=log.querySelectorAll('.code-actions button');assert.equal(buttons.length,2)
  buttons[0].click();await new Promise(resolve=>setTimeout(resolve,0));assert.equal(copied,'print("🌞")\n')
  buttons[1].click();await new Promise(resolve=>setTimeout(resolve,0));assert.equal(copied,'echo done\n')
})


test('command history renders separately and does not duplicate on replay',t=>{
  const dom=new JSDOM('<div id="log"></div>',{pretendToBeVisual:true})
  globalThis.window=dom.window;globalThis.document=dom.window.document
  globalThis.requestAnimationFrame=dom.window.requestAnimationFrame.bind(dom.window)
  globalThis.cancelAnimationFrame=dom.window.cancelAnimationFrame.bind(dom.window)
  window.marked=marked
  const log=document.querySelector('#log'),ui=createChatUI({log})
  t.after(()=>{ui.clear();dom.window.close()})
  const rows=[{kind:'event',event:{seq:200,type:'command/run',data:{name:'goal',args:' pause'}}},
    {kind:'event',event:{seq:201,type:'command/done',data:{kind:'success',text:'Goal paused'}}}]
  ui.applyLog(rows);ui.applyLog(rows)
  assert.equal(log.querySelectorAll('.msg').length,2)
  assert.match(log.textContent,/goal pause/);assert.match(log.textContent,/Goal paused/)
})

test('structured voice result renders its text as an assistant reply',async t=>{
  const dom=new JSDOM('<div id="log"></div>',{pretendToBeVisual:true})
  globalThis.window=dom.window;globalThis.document=dom.window.document
  globalThis.requestAnimationFrame=dom.window.requestAnimationFrame.bind(dom.window)
  globalThis.cancelAnimationFrame=dom.window.cancelAnimationFrame.bind(dom.window)
  window.marked=marked
  const {log:record,state}=await import('../extension/state.mjs');state.log=[]
  const log=document.querySelector('#log'),ui=createChatUI({log})
  t.after(()=>{ui.clear();dom.window.close();state.log=[]})
  ui.applyLog([record('event',{event:{seq:1,type:'tool/result',data:{meta:{resonantVoice:{version:1,text:'Hello, Manolo.',speech:{emotion:'warm'}}},message:{content:[{type:'tool-result',isError:false}]}}}})])
  assert.equal(log.querySelector('.assistant .md').textContent.trim(),'Hello, Manolo.')
  assert.ok(!log.textContent.includes('emotion'))
})

test('mixed prose and voice call uses the structured result only',async t=>{
  const dom=new JSDOM('<div id="log"></div>',{pretendToBeVisual:true})
  globalThis.window=dom.window;globalThis.document=dom.window.document
  globalThis.requestAnimationFrame=dom.window.requestAnimationFrame.bind(dom.window)
  globalThis.cancelAnimationFrame=dom.window.cancelAnimationFrame.bind(dom.window);window.marked=marked
  const {log:record,state}=await import('../extension/state.mjs');state.log=[]
  const log=document.querySelector('#log'),ui=createChatUI({log});t.after(()=>{ui.clear();dom.window.close();state.log=[]})
  ui.applyLog([record('event',{event:{seq:18,type:'assistant/message',data:{message:{content:[{type:'text',text:'Good news — it works.'},{type:'tool-call',name:'resonant_voice_demo'}]}}}}),record('event',{event:{seq:20,type:'tool/result',data:{meta:{resonantVoice:{version:1,text:'Here are the five samples.'}},message:{content:[{type:'tool-result',isError:false}]}}}})])
  assert.equal(log.querySelectorAll('.assistant .md').length,1)
  assert.equal(log.querySelector('.assistant .md').textContent.trim(),'Here are the five samples.')
})


test('v4 failed voice output never becomes an assistant reply',async t=>{
  const dom=new JSDOM('<div id="log"></div>',{pretendToBeVisual:true})
  globalThis.window=dom.window;globalThis.document=dom.window.document
  globalThis.requestAnimationFrame=dom.window.requestAnimationFrame.bind(dom.window)
  globalThis.cancelAnimationFrame=dom.window.cancelAnimationFrame.bind(dom.window);window.marked=marked
  const {log:record,state}=await import('../extension/state.mjs');state.log=[]
  const log=document.querySelector('#log'),ui=createChatUI({log})
  t.after(()=>{ui.clear();dom.window.close();state.log=[]})
  ui.applyLog([record('event',{event:{seq:25,type:'tool/result',data:{meta:{resonantVoice:{version:1,text:'Must not appear.'}},message:{role:'tool',isError:true,content:[{type:'text',text:'failed'}]}}}})])
  assert.equal(log.querySelectorAll('.assistant .md').length,0)
})

test('Pi recovery notices remain status records across live delivery and replay',t=>{
 const dom=new JSDOM('<div id="log"></div>',{pretendToBeVisual:true})
 globalThis.window=dom.window;globalThis.document=dom.window.document
 globalThis.requestAnimationFrame=dom.window.requestAnimationFrame.bind(dom.window)
 globalThis.cancelAnimationFrame=dom.window.cancelAnimationFrame.bind(dom.window);window.marked=marked
 const log=document.querySelector('#log'),ui=createChatUI({log});t.after(()=>{ui.clear();dom.window.close()})
 const rows=[{kind:'event',event:{seq:401,type:'runtime/notice',data:{message:'Bounded recovery 1/2 is continuing.'}}},
  {kind:'event',event:{seq:402,type:'runtime/notice',data:{message:'Task incomplete. Review confirmed progress.',incomplete:true}}}]
 ui.applyLog(rows);ui.applyLog(rows)
 assert.equal(log.querySelectorAll('.status').length,2)
 assert.equal(log.querySelectorAll('.assistant').length,0)
 assert.equal(log.querySelectorAll('.status .who')[0].textContent,'Status')
 assert.match(log.textContent,/Task incomplete/)
 ui.clear();ui.applyLog(rows);assert.equal(log.querySelectorAll('.status').length,2)
})
