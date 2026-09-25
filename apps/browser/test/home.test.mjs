// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import {JSDOM} from 'jsdom';
import {homeConnection} from '../shared/home.mjs';import {homeSettings} from '../extension/home.mjs';
test('Home settings bridge exposes only explicit connection operations',async()=>{
 const calls=[],call=async(method,params)=>{calls.push({method,params});return {connected:true};};
 assert.equal((await homeConnection({action:'state'},call)).connected,true);
 assert.deepEqual(calls,[{method:'home.connection.state',params:{}}]);
 assert.equal((await homeConnection({action:'host.shutdown'},call)).ok,false);assert.equal(calls.length,1);
});
test('Home settings pair once, clear the code and use the native connection boundary',async t=>{
 const dom=new JSDOM('<main></main>');t.after(()=>dom.window.close());const calls=[];
 homeSettings(dom.window.document,async(type,body)=>{calls.push({type,body});return {ok:true,connected:body.request.action==='pair',url:'https://home.example.com'};},dom.window.document.querySelector('main'));
 await new Promise(r=>setImmediate(r));const form=dom.window.document.querySelector('form');
 form.elements.url.value='https://home.example.com';form.elements.code.value='fixture-code';
 form.dispatchEvent(new dom.window.Event('submit',{cancelable:true,bubbles:true}));await new Promise(r=>setImmediate(r));
 assert.equal(calls.at(-1).type,'homeConnection');assert.equal(calls.at(-1).body.request.action,'pair');assert.equal(form.elements.code.value,'');
 assert.equal(form.querySelector('button[type=submit]').disabled,true);assert.match(form.textContent,/Connected/);
});
