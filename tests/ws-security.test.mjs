// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Bounded loopback regression for CVE-2026-62389, including empty fragments.
import test from 'node:test';
import assert from 'node:assert/strict';
import {once} from 'node:events';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root = process.env.AUGMENTOR_WS_TEST_ROOT ?? fileURLToPath(new URL('..', import.meta.url));
const packages = new Map();
for (const owner of ['', 'apps/browser', 'apps/browser/plugin', 'apps/mobile',
  'node_modules/@earendil-works/pi-coding-agent']) {
  const require = createRequire(path.join(root, owner, 'package.json'));
  const entry = require.resolve('ws');
  const labels = packages.get(entry)?.labels ?? [];
  labels.push(owner || 'runtime');
  packages.set(entry, {ws: require('ws'), labels});
}

for (const {ws: {WebSocket, WebSocketServer}, labels} of packages.values()) {
  for (const receivingSide of ['server', 'client']) {
    for (const payload of ['', 'x']) {
      test(`${labels.join(', ')}: ${receivingSide} bounds ${payload ? 'nonempty' : 'empty'} fragments`,
        {timeout: 5000}, async t => {
          const server = new WebSocketServer({host: '127.0.0.1', port: 0});
          let client;
          t.after(async () => {
            client?.terminate();
            for (const socket of server.clients) socket.terminate();
            await new Promise(resolve => server.close(resolve));
          });
          await once(server, 'listening');
          const connected = once(server, 'connection');
          client = new WebSocket(`ws://127.0.0.1:${server.address().port}`);
          client.on('error', () => {});
          const [peer] = await connected;
          peer.on('error', () => {});
          if (client.readyState !== WebSocket.OPEN) await once(client, 'open');
          const [receiver, sender] = receivingSide === 'server' ? [peer, client] : [client, peer];

          // Normal fragmented traffic must continue working in both directions.
          const message = once(receiver, 'message');
          sender.send('hello ', {fin: false});
          sender.send('world', {fin: true});
          assert.equal((await message)[0].toString(), 'hello world');

          const failure = new Promise((resolve, reject) => {
            const timer = setTimeout(() => reject(new Error('Receiver accepted excessive incomplete fragments')), 2000);
            receiver.once('error', error => {clearTimeout(timer); resolve(error);});
            t.after(() => clearTimeout(timer));
          });
          // At most ~115 KiB on the wire; no heap exhaustion or large payloads.
          for (let i = 0; i <= 16 * 1024; i++) sender.send(payload, {fin: false});
          assert.equal((await failure).code, 'WS_ERR_TOO_MANY_BUFFERED_PARTS');
        });
    }
  }
}
