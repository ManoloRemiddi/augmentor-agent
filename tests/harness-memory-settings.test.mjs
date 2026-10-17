// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {DshMemorySettings} from '../apps/harness/dsh-memory-settings.mjs';
const view=()=>({protocol:'augmentor-memory-settings/1',connected:true,enabled:true,configured:true,available:true,requestMode:'off',events:0,pending:0,stopped:0,actions:{capture:true,processing:true},processing:{known:true,paused:false,active:false}});
function fixture(handler){const listeners=new Set(),calls=[],controller={epoch:1,state:{phase:'ready',readOnly:false,capabilities:{memorySettings:true}},subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);},rpc:async(method,p)=>{calls.push({method,p});return handler(method,p);}};const profile=new DshMemorySettings(controller);return {profile,controller,calls,changed:()=>{for(const fn of listeners)fn();}};}
const settled=()=>new Promise(resolve=>setImmediate(resolve));
test('memory controls retain explicit expected state and never replay an unconfirmed write',async t=>{
 let raw=view(),fail=false;const f=fixture(async(method,p)=>{if(method==='memory.status')return structuredClone(raw);raw.enabled=p.enabled;if(fail)throw Error('synthetic-private-message');return structuredClone(raw);});t.after(()=>f.profile.close());await settled();
 await f.profile.change('capture');assert.deepEqual(f.calls.at(-1),{method:'memory.configure',p:{enabled:false,expectedEnabled:true}});assert.equal(f.profile.state.value.enabled,false);
 fail=true;await f.profile.change('capture');assert.equal(raw.enabled,true);assert.equal(f.profile.state.value,null);assert.match(f.profile.state.error,/Nothing was retried/);assert(!f.profile.state.error.includes('synthetic-private'));
 const calls=f.calls.length;await assert.rejects(f.profile.change('capture'),/Refresh/);assert.equal(f.calls.length,calls);await f.profile.load();assert.equal(f.profile.state.value.enabled,true);
});
test('late status from a retired connection cannot restore settings or reach an inspector',async t=>{
 let release;const held=new Promise(resolve=>release=resolve),f=fixture(()=>held);t.after(()=>f.profile.close());f.controller.epoch++;f.controller.state.readOnly=true;f.changed();release(view());await settled();assert.equal(f.profile.state.value,null);assert.equal(f.profile.current(),false);const calls=f.calls.length;await f.profile.load();assert.equal(f.calls.length,calls);
});
test('malformed statuses and unsupported actions remain non-writable',async t=>{
 const raw=view();raw.requestMode='synthetic-private-invalid-mode';const f=fixture(async()=>raw);t.after(()=>f.profile.close());await settled();assert.equal(f.profile.state.value,null);assert.match(f.profile.state.error,/confirmed/);const n=f.calls.length;await assert.rejects(f.profile.change('__proto__'),/capture or processing/);assert.equal(f.calls.length,n);
});
