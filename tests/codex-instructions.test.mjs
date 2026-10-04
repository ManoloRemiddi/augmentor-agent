// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {instructionSnapshot,validateInstructions} from '../dist/codex-runtime/src/instructions.js';
test('Augmentor persona snapshots are bounded and immutable across future source changes',t=>{
 const root=mkdtempSync(join(tmpdir(),'codex-instructions-'));t.after(()=>rmSync(root,{recursive:true,force:true}));const path=join(root,'persona.md');
 writeFileSync(path,'You are a personal assistant.');const first=instructionSnapshot(path);validateInstructions(first);
 assert.match(first.text,/not registered/);writeFileSync(path,'A newer persona.');const second=instructionSnapshot(path);
 assert.notEqual(first.personaSha256,second.personaSha256);assert.notEqual(first.sha256,second.sha256);validateInstructions(first);
 assert.throws(()=>validateInstructions({...first,text:'changed'}),/corrupt/);
 writeFileSync(path,'x'.repeat(32769));assert.throws(()=>instructionSnapshot(path),/size limit/);
});

test('screenshot guidance follows the immutable conversation capability',()=>{
 const text = instructionSnapshot(undefined,true); const image = instructionSnapshot(undefined,true,true);
 assert.match(text.text,/screenshots are not enabled/); assert.match(image.text,/screenshots are available/);
 assert.match(image.text,/do not replace a fresh DOM snapshot/); assert.notEqual(text.sha256,image.sha256);
});
