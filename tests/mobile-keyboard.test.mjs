// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {bindKeyboard} from '../apps/mobile/web/keyboard.js';

function fixture() {
  const field = new EventTarget();field.value='';
  const sent=[];let connected=true;
  bindKeyboard(field,key=>sent.push(key),()=>connected);
  return {field,sent,offline:()=>connected=false,online:()=>connected=true,
    emit(type,values={}) {const event=new Event(type,{cancelable:true});Object.assign(event,values);field.dispatchEvent(event);return event;}};
}
test('composition commits Unicode once, including supplementary characters',()=>{
  const f=fixture();f.field.value='café 🐱';
  f.emit('input',{isComposing:true});assert.deepEqual(f.sent,[]);
  f.emit('compositionend');f.emit('input',{isComposing:false});
  assert.deepEqual(f.sent,[99,97,102,233,32,0x0101f431]);assert.equal(f.field.value,'');
});
test('phone IME deletion and Enter work without hardware keydown',()=>{
  const f=fixture();
  for(const inputType of ['deleteContentBackward','deleteContentForward','insertParagraph'])assert.equal(f.emit('beforeinput',{inputType}).defaultPrevented,true);
  assert.deepEqual(f.sent,[0xff08,0xffff,0xff0d]);
  f.emit('beforeinput',{inputType:'deleteContentBackward',isComposing:true});assert.equal(f.sent.length,3);
});
test('hardware edit keys suppress native edits; disconnected input is discarded',()=>{
  const f=fixture();assert.equal(f.emit('keydown',{key:'Backspace'}).defaultPrevented,true);
  assert.deepEqual(f.sent,[0xff08]);f.offline();f.field.value='never replay';f.emit('input');f.emit('keydown',{key:'Enter'});
  assert.equal(f.field.value,'');f.online();f.emit('input');assert.deepEqual(f.sent,[0xff08]);
});
