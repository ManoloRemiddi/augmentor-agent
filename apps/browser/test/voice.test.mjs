// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import test from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {attachVoice} from '../extension/voice.mjs'

test('voice owns capture only after a click, submits each final once and releases on navigation',async t=>{
  const dom=new JSDOM('<button id="send"></button><button id="stop"></button>');
  const originals=new Map();
  function global(name,value){originals.set(name,Object.getOwnPropertyDescriptor(globalThis,name));Object.defineProperty(globalThis,name,{value,configurable:true,writable:true});}
  t.after(()=>{for(const [name,value] of originals){if(value)Object.defineProperty(globalThis,name,value);else delete globalThis[name];}dom.window.close();});
  dom.window.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  dom.window.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new dom.window.Event('close'));};
  let captures=0,stopped=0;const sent=[],sockets=[];
  class Socket {static OPEN=1;constructor(){this.readyState=1;this.bufferedAmount=0;sockets.push(this);}send(){}close(){this.readyState=3;} }
  class Context {constructor(){this.audioWorklet={addModule:async()=>{}};}async resume(){}async close(){}createMediaStreamSource(){return {connect(){}};}createGain(){return {gain:{},connect(){}};}}
  class Node {constructor(){this.port={postMessage(){}};}connect(){return {connect(){}};}disconnect(){}}
  global('document',dom.window.document);global('window',dom.window);global('AudioContext',Context);global('AudioWorkletNode',Node);global('WebSocket',Socket);
  global('navigator',{mediaDevices:{getUserMedia:async()=>{captures++;return {getTracks:()=>[{stop(){stopped++;}}]};}}});
  global('chrome',{runtime:{getURL:s=>s}});
  const voice=attachVoice({isHistory:()=>false,onError:message=>assert.fail(message),send:async(type,payload)=>{sent.push([type,payload]);return type==='voice/connect'?{ok:true,ticket:{protocol:'resonant-voice/1',url:'ws://127.0.0.1:8877/voice',sessionId:'one',ticket:'ticket'}}:{ok:true};}});
  assert.equal(captures,0);
  voice.update({harness:'dsh',phase:'ready',sessionId:'one'},false);
  dom.window.document.querySelector('[aria-label="Resonant Voice"]').click();
  await new Promise(resolve=>setTimeout(resolve,10));assert.equal(captures,1);assert.equal(dom.window.document.querySelector('dialog'),null);assert.equal(dom.window.document.querySelector('[aria-controls]').getAttribute('aria-expanded'),'true');
  const ws=sockets[0];ws.onopen();await ws.onmessage({data:JSON.stringify({type:'ready'})});
  const event={data:JSON.stringify({type:'transcript',sessionId:'one',requestId:'id',text:'Find the report'})};
  await ws.onmessage(event);await ws.onmessage(event);
  assert.equal(sent.filter(([type])=>type==='voice/prompt').length,1);
  voice.update({harness:'dsh',phase:'ready',sessionId:'two'},false);
  assert.equal(ws.readyState,3);assert.equal(stopped,1);
});
