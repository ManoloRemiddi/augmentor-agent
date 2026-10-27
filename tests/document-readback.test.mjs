// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import {zipSync,strToU8} from 'fflate';
import {decodeDocument} from '../apps/browser/extension/document-readback.mjs';
test('saved Docs HTML readback accepts plain text and one compressed HTML entry, retaining styles',async()=>{
 const html='<html><h1 style="font-weight:700">café 日本語</h1></html>';
 assert.equal(await decodeDocument(strToU8('actual text'),'txt'),'actual text');
 assert.equal(await decodeDocument(zipSync({'document.html':strToU8(html),'images/image.png':new Uint8Array([1,2,3])}),'html'),html);
 await assert.rejects(decodeDocument(zipSync({'a.html':strToU8(html),'b.html':strToU8(html)}),'html'),/unambiguous/);
 await assert.rejects(decodeDocument(zipSync({'document.html':strToU8('x'.repeat(1024*1024+1))}),'html'),/oversized/);
 const broken=zipSync({'document.html':strToU8(html)});broken.fill(0,0,4);await assert.rejects(decodeDocument(broken,'html'));
});
