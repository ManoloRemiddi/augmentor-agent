// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mcpReceiptMessage} from '../apps/harness/mcp-management.js';
test('interrupted and partial MCP actions cannot be presented as successful or healthy',()=>{
 for(const row of [{state:'interrupted',result:'unknown'},{state:'failed',result:'unknown'},{state:'failed',result:'profile-saved-partial'}]){
  const message=mcpReceiptMessage({action:'configure',server:'profile',...row});assert.doesNotMatch(message,/completed|connected|healthy|success/i);assert.match(message,/unknown outcome|could not be applied everywhere/);assert.match(message,/before.*action/);
 }
});
test('a settled SDK command is not a successful connection check',()=>{
 const message=mcpReceiptMessage({action:'reconnect',server:'authored',state:'completed',result:'sdk-command-settled'});assert.doesNotMatch(message,/completed|healthy|successfully/);assert.match(message,/did not report whether it succeeded/);
});
test('cancelled and unsaved configuration receipts preserve their distinct effects',()=>{
 assert.match(mcpReceiptMessage({action:'login',server:'authored',state:'cancelled',result:'sdk-command-settled'}),/credentials are not rolled back/);
 assert.match(mcpReceiptMessage({action:'configure',server:'profile',state:'cancelled',result:'configuration-not-saved'}),/not saved/);
 assert.match(mcpReceiptMessage({action:'login',server:'authored',state:'cancel-requested',result:'pending'}),/Waiting.*settle/);
});
