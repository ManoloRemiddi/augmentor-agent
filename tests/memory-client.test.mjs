// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import net from 'node:net';
import {mkdtempSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';import {once} from 'node:events';
import {recall} from '../dist/memory/src/index.js';
test('Stop closes an in-flight memory recall without replay or another connection',async t=>{
 const dir=mkdtempSync(join(tmpdir(),'augmentor-memory-cancel-'));process.env.AUGMENTOR_SHARED_STATE=dir;
 let calls=0,connections=0,peer,received;
 const ready=new Promise(r=>received=r);
 const server=net.createServer(socket=>{connections++;peer=socket;socket.on('data',()=>{calls++;received()})});server.listen(join(dir,'prompts.sock'));await once(server,'listening');
 t.after(()=>{peer?.destroy();server.close()});
 const abort=new AbortController(),request=recall('A private query',abort.signal);await ready;
 const closed=once(peer,'end');peer.resume();abort.abort();await assert.rejects(request,/Cancelled/);await closed;
 await new Promise(r=>setTimeout(r,100));assert.equal(calls,1);assert.equal(connections,1);
 await assert.rejects(recall('Never send this',AbortSignal.abort()));assert.equal(connections,1);
});
