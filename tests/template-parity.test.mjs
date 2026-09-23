// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import{readFileSync}from'node:fs';
import {expandClipboard} from '../packages/templates/clipboard.mjs';
for(const row of JSON.parse(readFileSync(new URL('./parity/clipboard.json',import.meta.url))))test('JS clipboard parity '+JSON.stringify(row),()=>{
 if(row.error)assert.throws(()=>expandClipboard(row.template,row.snapshot));else assert.equal(expandClipboard(row.template,row.snapshot),row.expected);
});
