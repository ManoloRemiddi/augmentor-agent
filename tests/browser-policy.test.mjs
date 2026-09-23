// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {applyBrowserPolicy} from '../adapters/dsh-desktop/browser-policy.mjs'
function fixture(){
  const events={};let guard
  applyBrowserPolicy({tools:{guard:fn=>{guard=fn}},on:(name,fn)=>{events[name]=fn}})
  return {events,guard,exec:(name,id='a')=>({name,agent:{id}})}
}
const accept=async()=>({kind:'accept'})
test('legacy false-success browser failure blocks isolated fallback only for that agent and turn',async()=>{
  const {events,guard,exec}=fixture()
  const result=await events['tools/post-execute'](exec('browser_navigate'),{isError:false,content:[{type:'text',text:'navigate failed: no browser client connected'}]},accept)
  assert.equal(result.kind,'block')
  assert.match(guard(exec('mcp__playwright__browser_navigate')),/separate browser/)
  assert.equal(guard(exec('mcp__playwright__browser_navigate','b')),undefined)
  assert.equal(guard(exec('browser_tabs_list')),undefined)
  events['agent/status']({agent:{id:'a'},status:'idle'})
  assert.equal(guard(exec('mcp__playwright__browser_navigate')),undefined)
})
test('successful real navigation releases fallback restriction and research has provenance',async()=>{
  const {events,guard,exec}=fixture()
  await events['tools/post-execute'](exec('browser_navigate'),{isError:true,content:[]},accept)
  await events['tools/post-execute'](exec('browser_navigate'),{isError:false,value:{ok:true},content:[]},accept)
  assert.equal(guard(exec('mcp__playwright__browser_snapshot')),undefined)
  const result=await events['tools/post-execute'](exec('mcp__playwright__browser_snapshot'),{isError:false,content:[{type:'text',text:'Page snapshot'}]},accept)
  assert.match(result.content[0].text,/research evidence only/)
  assert.equal(result.content[1].text,'Page snapshot')
})
test('preserves upstream policy blocks',async()=>{
  const {events,exec}=fixture();const blocked={kind:'block',feedback:[]}
  assert.equal(await events['tools/post-execute'](exec('mcp__playwright__browser_navigate'),{content:[]},async()=>blocked),blocked)
})
test('recorded blank NAS result blocks speculative actions until actual observation',async()=>{
 const {events,guard,exec}=fixture()
 const empty={content:[{type:'text',text:'Page: R-NAS1\nURL: https://nas.test/\n\n\nObserved controls (use exact selector; refresh snapshot after page changes):\n'}]}
 const feedback=await events['tools/post-execute'](exec('browser_snapshot'),empty,accept)
 assert.match(feedback.content.at(-1).text,/browser_screenshot/)
 assert.match(guard(exec('browser_click')),/fresh readable/)
 assert.equal(guard(exec('browser_snapshot')),undefined)
 assert.equal(guard(exec('browser_click','other')),undefined)
 await events['tools/post-execute'](exec('browser_screenshot'),{isError:true,content:[{type:'text',text:'permission denied'}]},accept)
 assert.match(guard(exec('browser_click')),/fresh readable/)
 await events['tools/post-execute'](exec('browser_screenshot'),{content:[{type:'image',attachment:{}}]},accept)
 assert.equal(guard(exec('browser_click')),undefined)
})
test('readable recovery and idle clear stale observation guards',async()=>{
 const {events,guard,exec}=fixture()
 await events['tools/post-execute'](exec('browser_snapshot'),{content:[{type:'text',text:'Page: \nURL: \n\n(no visible text)'}]},accept)
 await events['tools/post-execute'](exec('browser_snapshot'),{content:[{type:'text',text:'Page: NAS\nURL: https://nas.test/\n\nControl Panel'}]},accept)
 assert.equal(guard(exec('browser_type')),undefined)
 await events['tools/post-execute'](exec('browser_snapshot'),{isError:true,content:[]},accept)
 events['agent/status']({agent:{id:'a'},status:'idle'})
 assert.equal(guard(exec('browser_type')),undefined)
})
