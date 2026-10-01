// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {checkProvider} from '../dist/codex-runtime/src/provider-check.js';

async function provider(t, handler) {
  const server = createServer(handler); await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(async () => {server.closeAllConnections(); await new Promise(resolve => server.close(resolve));});
  return {kind: 'api', model: 'test-model', endpoint: `http://127.0.0.1:${server.address().port}/v1`, credential: 'fixture-secret'};
}
test('explicit provider check sends no history or tools and requires a completed text response', async t => {
  let body, authorization;
  const connection = await provider(t, async (req, res) => {
    let raw = ''; for await (const chunk of req) raw += chunk;
    body = JSON.parse(raw); authorization = req.headers.authorization;
    res.writeHead(200, {'content-type': 'text/event-stream'});
    res.write('data: {"type":"response.output_text.del');
    res.write('ta","delta":"OK"}\n\n');
    res.end('data: {"type":"response.completed","response":{"status":"completed","output":[]}}\n\n');
  });
  assert.equal((await checkProvider(connection)).validation, 'responses-text');
  assert.equal(authorization, 'Bearer fixture-secret'); assert.equal(body.stream, true); assert.equal(body.store, false);
  assert.equal(body.tools, undefined); assert.equal(body.input.length, 1); assert.equal(body.instructions, undefined);
});
test('provider error bodies and redirects do not expose or forward credentials', async t => {
  const rejected = await provider(t, (_req, res) => {res.writeHead(401); res.end('fixture-secret');});
  await assert.rejects(checkProvider(rejected), error => error.message.includes('HTTP 401') && !error.message.includes('fixture-secret'));
  let redirected = false;
  const redirect = await provider(t, (req, res) => {
    if (req.url === '/target') {redirected = true; res.end(); return;}
    res.writeHead(302, {location: '/target'}); res.end();
  });
  await assert.rejects(checkProvider(redirect), /did not accept/); assert.equal(redirected, false);
});
test('partial and failed streams never count as successful connection checks', async t => {
  const partial = await provider(t, (_req, res) => {res.writeHead(200); res.end('data: {"type":"response.output_text.delta","delta":"Partial"}\n\n');});
  await assert.rejects(checkProvider(partial), /without a completed/);
  const failed = await provider(t, (_req, res) => {res.writeHead(200); res.end('data: {"type":"response.failed","error":{"message":"fixture-secret"}}\n\n');});
  await assert.rejects(checkProvider(failed), error => error.message.includes('could not complete') && !error.message.includes('fixture-secret'));
});

test('provider check accepts mixed SSE line endings in their original order', async t => {
  const connection = await provider(t, (_req, res) => {
    res.writeHead(200, {'content-type': 'text/event-stream'});
    res.end('data: {"type":"response.output_text.delta","delta":"OK"}\r\n\r\ndata: {"type":"response.completed","response":{"status":"completed"}}\n\n');
  });
  assert.equal((await checkProvider(connection)).valid, true);
});

test('image check requires the answer read from synthetic pixels, not generic text completion', async t => {
  const {inflateSync} = await import('node:zlib');
  const palette = new Map([['220,0,0','red'], ['0,160,0','green'], ['0,0,255','blue'], ['255,220,0','yellow'], ['0,0,0','black'], ['255,255,255','white']]);
  let wrong = false;
  const connection = await provider(t, async (req, res) => {
    let raw = ''; for await (const chunk of req) raw += chunk;
    const body = JSON.parse(raw); const content = body.input[0].content;
    assert.equal(body.tools, undefined); assert.equal(body.instructions, undefined);
    assert.equal(body.input.length, 1); assert.equal(content.length, 2);
    assert.equal(content[1].type, 'input_image');
    const png = Buffer.from(content[1].image_url.split(',')[1], 'base64');
    assert.equal(png.subarray(1, 4).toString(), 'PNG');
    const compressed = []; let width;
    for (let offset = 8; offset < png.length;) {
      const size = png.readUInt32BE(offset), kind = png.subarray(offset + 4, offset + 8).toString();
      const data = png.subarray(offset + 8, offset + 8 + size);
      if (kind === 'IHDR') width = data.readUInt32BE(0);
      if (kind === 'IDAT') compressed.push(data);
      offset += size + 12;
    }
    const pixels = inflateSync(Buffer.concat(compressed));
    const answer = Array.from({length: 4}, (_, i) => {
      const offset = 18 * (width * 3 + 1) + 1 + (i * 36 + 18) * 3;
      return palette.get([...pixels.subarray(offset, offset + 3)].join(','));
    }).join(',');
    res.writeHead(200, {'content-type': 'text/event-stream'});
    res.end('data: ' + JSON.stringify({type: 'response.completed', response: {status: 'completed', output: [{type: 'message', content: [{type: 'output_text', text: wrong ? 'OK' : answer}]}]}}) + '\n\n');
  });
  assert.equal((await checkProvider(connection, 45000, 'image')).validation, 'responses-image');
  wrong = true; await assert.rejects(checkProvider(connection, 45000, 'image'), /did not identify the test image/);
});
