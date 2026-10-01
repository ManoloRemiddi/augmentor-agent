// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import test from 'node:test';
import assert from 'node:assert/strict';
import {ApprovalPresenters} from '../extension/approval-presenters.mjs';
test('one live Browser document owns an approval and disconnect permits another to present',()=>{
 globalThis.chrome={runtime:{getURL:path=>'chrome-extension://fixture/'+path}};
 const registry=new ApprovalPresenters();
 const port=id=>{let closed;return {name:'augmentor-approval-presenter',sender:{documentId:id,url:'chrome-extension://fixture/sidepanel.html'},onDisconnect:{addListener:fn=>closed=fn},disconnect:()=>closed?.()}};
 const a=port('a'),b=port('b');registry.connect(a);registry.connect(b);
 assert.equal(registry.claim('request',a.sender),true);assert.equal(registry.claim('request',b.sender),false);
 assert.equal(registry.owns('request',b.sender),false);a.disconnect();
 assert.equal(registry.owns('request',a.sender),false);assert.equal(registry.claim('request',b.sender),true);
 assert.equal(registry.claim('request',a.sender),false);registry.resolve('request');assert.equal(registry.owns('request',b.sender),false);
 const foreign=port('foreign');foreign.sender.url='https://other.test/';registry.connect(foreign);assert.equal(registry.claim('request',foreign.sender),false);
 registry.clear();b.disconnect();delete globalThis.chrome;
});
