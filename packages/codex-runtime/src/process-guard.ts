// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn} from 'node:child_process';

// This process is the detached POSIX group leader created by CodexRpc. Keeping
// ownership alive avoids guessing at saved PIDs after the host dies. The private
// IPC channel is a liveness lease; it carries no prompts or credentials.
if (process.platform === 'win32' || !process.connected || !process.argv[2]) process.exit(1);
let stopping = false;
const killGroup = (): void => {process.kill(-process.pid, 'SIGKILL');};
const stop = (signalGroup: boolean): void => {
  if (stopping) return;
  stopping = true;
  setTimeout(killGroup, 2000);
  if (signalGroup) process.kill(-process.pid, 'SIGTERM');
};
process.on('disconnect', () => stop(true));
// Rpc.close already signals the whole group. Repeating TERM could make a
// native graceful shutdown interpret the second signal as a force request.
process.on('SIGTERM', () => stop(false));
process.on('SIGINT', () => stop(false));
const child = spawn(process.argv[2], process.argv.slice(3), {
  env: process.env, stdio: ['inherit', 'inherit', 'inherit'], detached: false,
});
// The native process may exit before helpers that ignore TERM. Retire the group
// while its leader still owns the PID, including on spawn failure.
child.on('error', killGroup);
child.on('exit', killGroup);
if (!process.connected) stop(true);
