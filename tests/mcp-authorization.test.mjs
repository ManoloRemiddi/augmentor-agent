// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const {savedMcpAuthorization}=await import(pathToFileURL(join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),'dist/runtime/src/mcp-authorization.js')));
test('native authorization recovery admits bounded historical metadata and drops foreign sensitive fields',()=>{
 const row={server:'authored',status:403,boundary:'http-tool-response',state:'sign-in-required',observedAt:'2026-10-11T00:00:00.000Z',requestId:17};
 assert.deepEqual(savedMcpAuthorization({...row,headers:{authorization:'SYNTHETIC_SECRET'},body:'SYNTHETIC_PRIVATE_BODY',url:'https://synthetic.invalid/private'}),row);
 for(const patch of [{status:200},{boundary:'provider-request'},{state:'authorized'},{observedAt:'2026-02-30T00:00:00.000Z'},{server:'x'.repeat(129)},{requestId:'x'.repeat(257)},{requestId:Infinity}])assert.equal(savedMcpAuthorization({...row,...patch}),undefined);
 assert.equal(savedMcpAuthorization(null),undefined);
});
