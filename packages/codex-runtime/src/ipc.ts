// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import net from 'node:net';
import {chmodSync, existsSync, lstatSync, unlinkSync} from 'node:fs';
import {dirname} from 'node:path';
import {MAX_FRAME, request} from '../../protocol/src/index.js';
import {CodexHost, CODEX_PROTOCOL} from './host.js';
import {privateDirectory} from './storage.js';

/** User-owned local IPC, independent of the native window or browser connection. */
export class CodexIpcServer {
  private clients = new Map<net.Socket, {ready: boolean; sessionId?: string; pending: Set<string>}>();
  private server?: net.Server;
  private inode?: number;
  private closing = false;
  constructor(readonly host: CodexHost, readonly socketPath: string) {}
  async listen(): Promise<void> {
    if (this.server || this.closing) throw new Error('Codex IPC cannot be started twice.');
    privateDirectory(dirname(this.socketPath));
    if (existsSync(this.socketPath)) {
      const previous = lstatSync(this.socketPath);
      if (!previous.isSocket() || previous.isSymbolicLink() || (process.getuid && previous.uid !== process.getuid()) || (previous.mode & 0o077)) throw new Error('Codex socket is not a private, user-owned socket.');
      const live = await new Promise<boolean>((resolve, reject) => {
        const probe = net.createConnection(this.socketPath);
        const timer = setTimeout(() => {probe.destroy(); reject(new Error('Existing Codex host did not respond; it was not replaced.'));}, 2000);
        probe.once('connect', () => {clearTimeout(timer); probe.destroy(); resolve(true);});
        probe.once('error', (error: NodeJS.ErrnoException) => {
          clearTimeout(timer);
          if (error.code === 'ECONNREFUSED' || error.code === 'ENOENT') resolve(false);
          else reject(new Error('Existing Codex socket could not be checked safely.'));
        });
      });
      if (live) throw new Error('Codex host is already running.');
      if (existsSync(this.socketPath)) {
        if (lstatSync(this.socketPath).ino !== previous.ino) throw new Error('Codex socket changed during recovery.');
        unlinkSync(this.socketPath);
      }
    }
    const server = net.createServer(socket => this.connect(socket)); this.server = server;
    await new Promise<void>((resolve, reject) => {
      server.once('error', reject);
      server.listen(this.socketPath, () => {server.off('error', reject); resolve();});
    });
    chmodSync(this.socketPath, 0o600); this.inode = lstatSync(this.socketPath).ino;
    this.host.on('event', this.event);
    this.host.on('attention', this.attention);
  }
  private write(socket: net.Socket, value: unknown): void {
    if (socket.destroyed) return;
    const line = JSON.stringify(value) + '\n';
    if (Buffer.byteLength(line) > MAX_FRAME || socket.writableLength > 4 * MAX_FRAME) {socket.destroy(); return;}
    socket.write(line);
  }
  private event = (id: string, frame: unknown): void => {
    for (const [socket, client] of this.clients) if (client.ready && client.sessionId === id) this.write(socket, {event: frame});
  };
  private attention = (id: string, info: unknown): void => this.event(id, {method: 'session/attention', payload: {sessionId: id, ...info as object}});
  private connect(socket: net.Socket): void {
    if (this.closing || this.clients.size >= 32) {socket.destroy(); return;}
    const client = {ready: false, sessionId: undefined as string | undefined, pending: new Set<string>()};
    this.clients.set(socket, client);
    let buffer = Buffer.alloc(0);
    const handshakeTimer = setTimeout(() => {if (!client.ready) socket.destroy();}, 10000);
    socket.on('error', () => {});
    socket.on('close', () => {clearTimeout(handshakeTimer); this.clients.delete(socket);});
    socket.on('data', chunk => {
      buffer = Buffer.concat([buffer, chunk]);
      let end;
      while ((end = buffer.indexOf(10)) >= 0) {
        if (end > MAX_FRAME) {socket.destroy(); return;}
        const line = buffer.subarray(0, end); buffer = buffer.subarray(end + 1);
        if (client.pending.size >= 32) {socket.destroy(); return;}
        let parsed: unknown;
        try {parsed = JSON.parse(line.toString('utf8')); request(parsed);}
        catch {this.write(socket, {error: {message: 'Invalid Codex host request.'}}); socket.end(); return;}
        const req = parsed;
        if (client.pending.has(req.id)) {socket.destroy(); return;}
        client.pending.add(req.id);
        void (async () => {
          try {
            if (this.closing) throw new Error('Codex host is closing.');
            const params = req.params ?? {};
            let result;
            if (req.method === 'host.hello') {
              if (params.protocol !== CODEX_PROTOCOL) throw new Error('Incompatible Codex host protocol.');
              client.ready = true; clearTimeout(handshakeTimer); result = {protocol: CODEX_PROTOCOL};
            } else {
              if (!client.ready) throw new Error('Codex host protocol handshake is required.');
              if (req.method === 'events.subscribe') {
                if (params.sessionId !== null && params.sessionId !== undefined) await this.host.dispatch('session.describe', params);
                client.sessionId = params.sessionId ?? undefined; result = {subscribed: true};
              } else result = await this.host.dispatch(req.method, params);
            }
            this.write(socket, {id: req.id, result});
          } catch (error) {
            this.write(socket, {id: req.id, error: {message: error instanceof Error ? error.message : 'Codex host request failed.'}});
          } finally {client.pending.delete(req.id);}
        })();
      }
      if (buffer.length > MAX_FRAME) socket.destroy();
    });
  }
  async close(): Promise<void> {
    if (this.closing) return; this.closing = true;
    this.host.off('event', this.event); this.host.off('attention', this.attention);
    for (const socket of this.clients.keys()) socket.destroy(); this.clients.clear();
    if (this.server?.listening) await new Promise<void>(resolve => this.server!.close(() => resolve()));
    if (this.inode && existsSync(this.socketPath) && lstatSync(this.socketPath).ino === this.inode) unlinkSync(this.socketPath);
    await this.host.close();
  }
}
