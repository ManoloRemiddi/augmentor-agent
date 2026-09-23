// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {desktopCapabilities} from '../dist/desktop/src/capabilities.js';

test('macOS advertises input only when its native helper is installed',()=>{
 assert.equal(desktopCapabilities('darwin',{},()=>false).available,false);
 const c=desktopCapabilities('darwin',{AUGMENTOR_MACOS_HELPER:'/test/helper'},path=>path==='/test/helper');
 assert.equal(c.available,true);assert.equal(c.backend,'macos-screencapturekit');
 assert.equal(c.text,'Unicode');assert.equal(c.requiresUserConsent,true);
 assert.equal(desktopCapabilities('darwin',{AUGMENTOR_PI_LINUX_TOOLS:'0'},()=>true).available,false);
});
test('deferred Windows backend is unavailable and Linux retains its restrictions',()=>{
 assert.equal(desktopCapabilities('win32',{},()=>true).available,false);
 const c=desktopCapabilities('linux',{});
 assert.equal(c.backend,'kde-wayland-portal');assert.equal(c.text,'ASCII');assert.equal(c.monitors,1);
});
