// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {desktopCapabilities} from '../dist/desktop/src/capabilities.js';
import {desktopPackage} from '../dist/desktop/src/index.js';
import {applyWithCapabilities} from '../adapters/dsh-desktop/index.mjs';
const ready={schema:1,available:true,backend:'kde-wayland-portal',reason:null,permission:'not-requested',functionalTested:false};

test('macOS retains its native helper and user-consent contract without probing Linux',()=>{
 const forbidden=()=>{throw Error('Linux probe must not run');};
 assert.equal(desktopCapabilities('darwin',{},()=>false,forbidden).available,false);
 const c=desktopCapabilities('darwin',{AUGMENTOR_MACOS_HELPER:'/test/helper'},path=>path==='/test/helper',forbidden);
 assert.equal(c.available,true);assert.equal(c.backend,'macos-screencapturekit');
 assert.equal(c.text,'Unicode');assert.equal(c.requiresUserConsent,true);assert.equal(c.functionalTested,false);
 assert.equal(desktopCapabilities('darwin',{AUGMENTOR_PI_LINUX_TOOLS:'0'},()=>true,forbidden).available,false);
});
test('Windows and disabled Linux never query a desktop session',()=>{
 const forbidden=()=>{throw Error('Probe must not run');};
 assert.equal(desktopCapabilities('win32',{},()=>true,forbidden).available,false);
 assert.equal(desktopCapabilities('linux',{AUGMENTOR_PI_LINUX_TOOLS:'0'},()=>true,forbidden).available,false);
});
test('Linux reports observed backend availability separately from permission and acceptance',()=>{
 const c=desktopCapabilities('linux',{},()=>false,()=>ready);
 assert.equal(c.available,true);assert.equal(c.backend,'kde-wayland-portal');assert.equal(c.reason,null);
 assert.equal(c.text,'ASCII');assert.equal(c.monitors,1);assert.equal(c.permission,'not-requested');assert.equal(c.functionalTested,false);
});
for(const reason of ['unsupported-session','dependencies-missing','window-observer-unavailable','portal-capabilities-incomplete'])test('Linux refuses '+reason,()=>{
 const c=desktopCapabilities('linux',{},()=>true,()=>({...ready,available:false,backend:reason==='unsupported-session'?null:ready.backend,reason}));
 assert.equal(c.available,false);assert.equal(c.reason,reason);
});
test('unavailable Pi and DSH backends keep Stop without advertising input tools',()=>{
 const pi=[];desktopPackage('pi:fixture',false)({registerTool:tool=>pi.push(tool.name)});
 assert.deepEqual(pi,['linux_desktop_stop']);
 const dsh=[];const ctx={tools:{register:tool=>dsh.push(tool.name),guard:()=>{}},on:()=>{},effect:()=>{}};
 applyWithCapabilities(ctx,{available:false});
 assert.ok(dsh.includes('linux_desktop_stop'));assert.ok(!dsh.includes('linux_desktop_connect'));
 assert.ok(!dsh.includes('linux_desktop_snapshot'));assert.ok(!dsh.includes('linux_desktop_action'));
 if(process.platform==='linux')assert.ok(dsh.includes('linux_system_profile'));
});
