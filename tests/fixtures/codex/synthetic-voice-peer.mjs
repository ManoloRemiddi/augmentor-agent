// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Scripted test peer written from Augmentor's wire adapter and test expectations.
// No Resonant Voice implementation, ASR, TTS, configuration reader or device code.
import {createServer} from 'node:http';
import {randomBytes, randomUUID} from 'node:crypto';
import {WebSocketServer, WebSocket} from 'ws';

const opaque = () => randomBytes(32).toString('hex');
export function createSyntheticVoicePeer({render} = {}) {
  const token = opaque(), tickets = new Map(), bridges = new Map(), connections = [], spoken = [];
  let port;
  const send = (peer, event) => {if (peer?.socket.readyState === WebSocket.OPEN) peer.socket.send(JSON.stringify(event));};
  const clear = peer => {
    peer.rendering?.abort(); peer.rendering = undefined; peer.generation++;
    peer.streams.clear(); send(peer, {type: 'clear', generation: peer.generation});
  };
  const closePeer = peer => {if (!peer) return; clear(peer); peer.closed = true; peer.socket.close();};
  const synthesize = async (peer, text) => {
    spoken.push(text);
    const controller = new AbortController(); peer.rendering = controller;
    const generation = peer.generation;
    send(peer, {type: 'speaking', generation});
    const frames = render ? render(text, controller.signal) : [Buffer.from([1, 0, 2, 0])];
    for await (const frame of frames) {
      if (controller.signal.aborted || peer.closed || generation !== peer.generation) return;
      const header = Buffer.alloc(8); header.writeUInt32LE(generation);
      peer.socket.send(Buffer.concat([header, frame]));
    }
    if (!controller.signal.aborted && !peer.closed && generation === peer.generation) send(peer, {type: 'speech-idle', generation});
  };
  const server = createServer(async (request, response) => {
    const reply = (status, body) => {response.writeHead(status, {'content-type': 'application/json'}); response.end(JSON.stringify(body));};
    if (request.method === 'GET' && request.url === '/health') {
      reply(200, {status: 'ok', sample_rate: 24000, protocol: 'resonant-voice/1', capabilities: {scopedHarnessBridge: 1}}); return;
    }
    if (request.method !== 'POST' || request.headers['x-resonant-token'] !== token) {reply(403, {error: 'Synthetic peer requires its test token.'}); return;}
    let body;
    try {
      const chunks = []; let size = 0;
      for await (const chunk of request) {size += chunk.length; if (size > 65536) throw Error(); chunks.push(chunk);}
      body = JSON.parse(Buffer.concat(chunks));
    } catch {reply(400, {error: 'Invalid test request.'}); return;}
    if (request.url === '/internal/ticket') {
      const ticket = opaque(), bridgeId = opaque();
      const bridge = {sessionId: body.sessionId, harness: body.harness, bridgeId, seq: 0};
      tickets.set(ticket, bridge); bridges.set(bridgeId, bridge);
      reply(200, {protocol: 'resonant-voice/1', sessionId: body.sessionId, ticket, bridgeId,
        bridgeLeaseMs: 8000, url: `ws://127.0.0.1:${port}/voice`}); return;
    }
    const bridge = bridges.get(body.bridgeId);
    if (request.url !== '/internal/event' || !bridge || body.sessionId !== bridge.sessionId || body.harness !== bridge.harness) {
      reply(403, {error: 'Unknown test lease.'}); return;
    }
    if (!Number.isInteger(body.seq) || body.seq <= bridge.seq) {reply(200, {ok: true, ignored: true}); return;}
    bridge.seq = body.seq;
    const peer = bridge.peer;
    if (body.type === 'disconnect') {
      closePeer(peer); bridges.delete(bridge.bridgeId); reply(200, {ok: true, active: false}); return;
    }
    if (!peer) {reply(200, {ok: true, active: false, pending: true}); return;}
    if (body.type === 'cancel') {clear(peer); peer.requestId = undefined;}
    else if (body.type === 'user-turn') {peer.requestId = body.requestId; peer.streams.clear();}
    else if (body.requestId === peer.requestId) {
      if (body.type === 'start') peer.streams.set(body.stream, '');
      else if (body.type === 'text' && peer.streams.has(body.stream)) peer.streams.set(body.stream, peer.streams.get(body.stream) + body.text);
      else if (body.type === 'end' && peer.streams.has(body.stream)) {
        const text = peer.streams.get(body.stream); peer.streams.delete(body.stream);
        if (text) void synthesize(peer, text).catch(() => closePeer(peer));
      } else if (body.type === 'turn-complete') send(peer, {type: 'turn-complete', requestId: body.requestId, generation: peer.generation});
    }
    reply(200, {ok: true, active: !peer.closed});
  });
  const sockets = new WebSocketServer({server, path: '/voice', maxPayload: 65536});
  sockets.on('connection', socket => {
    let peer;
    socket.on('message', (data, binary) => {
      if (binary) return; // Synthetic input has no recognizer or audio processing.
      let event; try {event = JSON.parse(data);} catch {socket.close(); return;}
      if (!peer) {
        const bridge = event.type === 'auth' ? tickets.get(event.ticket) : undefined;
        if (!bridge) {socket.close(); return;}
        tickets.delete(event.ticket);
        peer = {socket, closed: false, generation: 0, streams: new Map(), sessionId: bridge.sessionId};
        bridge.peer = peer; connections.push(peer);
        send(peer, {type: 'ready', protocol: 'resonant-voice/1', sessionId: peer.sessionId, maxUtteranceSeconds: 600}); return;
      }
      if (event.type === 'begin') {
        clear(peer); peer.utteranceId = randomUUID();
        send(peer, {type: 'utterance-start', sessionId: peer.sessionId, requestId: peer.utteranceId});
      } else if (event.type === 'end' && peer.utteranceId) {
        send(peer, {type: 'transcript', sessionId: peer.sessionId, requestId: peer.utteranceId, text: 'Synthetic spoken request'});
        peer.utteranceId = undefined;
      } else if (event.type === 'cancel') clear(peer);
    });
    socket.on('close', () => {if (peer) {peer.closed = true; peer.rendering?.abort();}});
    socket.on('error', () => {if (peer) closePeer(peer);});
  });
  return {server, connections, spoken,
    get connection() {return {base: `http://127.0.0.1:${port}`, token};},
    async listen() {await new Promise(resolve => server.listen(0, '127.0.0.1', resolve)); port = server.address().port;},
    async close() {
      for (const peer of connections) {peer.rendering?.abort(); peer.closed = true; peer.socket.terminate();}
      sockets.close(); server.closeAllConnections(); await new Promise(resolve => server.close(resolve));
    },
  };
}
