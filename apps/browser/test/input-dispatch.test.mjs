// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFileSync} from 'node:fs'
import assert from 'node:assert/strict'
import {test} from 'node:test'
import {JSDOM} from 'jsdom'
const source=readFileSync(new URL('../extension/actions.mjs',import.meta.url),'utf8')
const start=source.indexOf('(selector, text, pulse, target) => {')
const end=source.indexOf('\n          },',start)+12
const handler=source.slice(start,end)
function fixture(html){
 const dom=new JSDOM(html,{runScripts:'outside-only'})
 return {window:dom.window,run:dom.window.eval('('+handler+')')}
}
for(const tag of ['input','textarea'])test(`framework-managed ${tag} receives a changed input value`,()=>{
 const {window,run}=fixture(`<${tag} id="field"></${tag}><div id="saved"></div>`)
 const el=window.document.querySelector('#field');let tracked='';let saves=0
 const native=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el),'value')
 Object.defineProperty(el,'value',{get(){return native.get.call(this)},set(value){tracked=value;native.set.call(this,value)}})
 el.addEventListener('input',()=>{if(el.value!==tracked){tracked=el.value;saves++;window.document.querySelector('#saved').textContent=el.value}})
 assert.equal(run('#field','Option yes','').ok,true)
 assert.equal(saves,1);assert.equal(window.document.querySelector('#saved').textContent,'Option yes')
 window.close()
})
test('refuses noneditable, disabled and read-only targets',()=>{
 const {window,run}=fixture('<div id="plain">Keep</div><input id="disabled" disabled><input id="readonly" readonly>')
 for(const id of ['plain','disabled','readonly'])assert.equal(run('#'+id,'Overwrite','').ok,false)
 assert.equal(window.document.querySelector('#plain').textContent,'Keep');window.close()
})
test('contenteditable receives text and input event',()=>{
 const {window,run}=fixture('<div id="field" contenteditable="true"></div>')
 const el=window.document.querySelector('#field');Object.defineProperty(el,'isContentEditable',{value:true})
 let data;el.addEventListener('input',e=>data=e.data)
 assert.equal(run('#field','Question','').ok,true);assert.equal(el.textContent,'Question');assert.equal(data,'Question');window.close()
})

test('stale document refuses typing without changing the target',()=>{
 const {window,run}=fixture('<input id="field" value="Keep">')
 const result=run('#field','Overwrite','',{url:'https://old.example/',documentEpoch:window.performance.timeOrigin})
 assert.equal(result.ok,false);assert.match(result.error,/document changed/)
 assert.equal(window.document.querySelector('#field').value,'Keep');window.close()
})
