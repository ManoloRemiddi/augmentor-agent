// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

import test from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {marked} from 'marked'
import {createChatUI} from '../extension/chat-render.js'

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
