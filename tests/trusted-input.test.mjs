// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
const calls=[],listeners={};let revision=0,loader='one',active=true,granted=true;
globalThis.chrome={permissions:{contains:async()=>granted},runtime:{getPlatformInfo:async()=>({os:'linux'})},windows:{update:async()=>{}},tabs:{update:async()=>{active=true},get:async id=>({id,active,url:'https://fixture.test/',windowId:1})},scripting:{executeScript:async()=>[{result:{epoch:1,revision,focus:[{tag:'IFRAME'}]}}]},debugger:{attach:async()=>{},detach:async()=>{},onDetach:{addListener:fn=>listeners.detach=fn},onEvent:{addListener:fn=>listeners.event=fn},sendCommand:async(target,method,params)=>{calls.push({method,params});if(method==='Page.getFrameTree')return {frameTree:{frame:{loaderId:loader}}};if(method==='Page.getLayoutMetrics')return {cssVisualViewport:{clientWidth:800,clientHeight:600,pageX:0,pageY:0}};return {}}}};
const {parseChord,observeTrusted,trustedAction,stopTrusted,trustedCapabilities}=await import('../apps/browser/extension/trusted-input.mjs');
const tab={id:5,url:'https://fixture.test/',windowId:1};
test('keyboard mapping preserves native modifiers and macOS editing commands',()=>{
 assert.equal(parseChord('Enter').text,'\r');assert.equal(parseChord('Space').text,' ');assert.equal(parseChord('Control+A').text,undefined);assert.deepEqual(parseChord('Control+Alt+1').modifiers,3);assert.equal(parseChord('Meta+A',true).commands[0],'selectAll');assert.equal(parseChord('Control+Shift+Z').modifiers,10);assert.throws(()=>parseChord('Unknown+A'));assert.throws(()=>parseChord('Control+NotAKey'));
});
test('trusted input consumes a fresh observation and never repeats it',async t=>{
 t.after(()=>stopTrusted());calls.length=0;revision=0;loader='one';granted=true;
 const observed=await observeTrusted(tab,'pi:one',async()=>({ok:true,text:'fixture'}));
 await trustedAction(tab,'pi:one',{action:'insert_text',text:'authored fixture',token:observed.target.token});
 assert.equal(calls.filter(c=>c.method==='Input.insertText').length,1);
 await assert.rejects(trustedAction(tab,'pi:one',{action:'insert_text',text:'again',token:observed.target.token}),/stale or already used/);
 assert.equal(calls.filter(c=>c.method==='Input.insertText').length,1);
});
test('human focus/input or document changes refuse input before dispatch',async t=>{
 t.after(()=>stopTrusted());revision=0;loader='one';granted=true;
 const first=await observeTrusted(tab,'pi:one',async()=>({ok:true}));revision++;
 const count=calls.filter(c=>c.method.startsWith('Input.')).length;
 await assert.rejects(trustedAction(tab,'pi:one',{action:'press_key',key:'Control+A',token:first.target.token}),/changed/);
 const second=await observeTrusted(tab,'pi:one',async()=>({ok:true}));loader='two';
 await assert.rejects(trustedAction(tab,'pi:one',{action:'press_key',key:'Control+A',token:second.target.token}),/changed/);
 assert.equal(calls.filter(c=>c.method.startsWith('Input.')).length,count);
});
test('tab lease prevents simultaneous writers and Stop releases keys and ownership',async t=>{
 t.after(()=>stopTrusted());revision=0;loader='one';granted=true;
 await observeTrusted(tab,'pi:first',async()=>({ok:true}));
 await assert.rejects(observeTrusted(tab,'pi:second',async()=>({ok:true})),/Another Augmentor conversation/);
 await stopTrusted('pi:first');const next=await observeTrusted(tab,'pi:second',async()=>({ok:true}));
 await trustedAction(tab,'pi:second',{action:'press_key',key:'Control+A',token:next.target.token});
 assert(calls.some(c=>c.method==='Input.dispatchKeyEvent'&&c.params.type==='keyUp'&&c.params.modifiers===0));
});
test('capabilities report actual grant instead of inventing input permission',async()=>{
 granted=false;assert.equal((await trustedCapabilities()).trustedKeyboard,false);granted=true;
});
