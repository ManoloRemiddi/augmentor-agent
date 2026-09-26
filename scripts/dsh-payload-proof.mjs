// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Real native dependency and subprocess checks against a staged or sealed bundle.
import assert from 'node:assert/strict';
import {mkdtemp, writeFile, rm} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {finished} from 'node:stream/promises';

const target = resolve(process.argv[2]);
const require = createRequire(join(target, 'package.json'));
const load = name => import(pathToFileURL(require.resolve(name)).href);
const work = await mkdtemp(join(tmpdir(), 'augmentor-dsh-payload-'));
const {Context} = await load('@deepseek-ai/cordis');
const {default: LocalSubprocessRuntime} = await load('@deepseek-ai/dsh-subprocess-local');
const ctx = new Context();
const handles = [];
let terminal;
const deadline = setTimeout(() => { console.error('DSH payload proof timed out'); process.exit(1); }, 60000);
try {
  const koffi = require('koffi');
  const libc = koffi.load(process.platform === 'darwin' ? '/usr/lib/libSystem.B.dylib' : 'libc.so.6');
  assert.equal(libc.func('int getpid()')(), process.pid);
  const {rgPath} = await load('@vscode/ripgrep');
  await writeFile(join(work, 'search.txt'), 'augmentor-payload-needle\n');
  assert.match(execFileSync(rgPath, ['--fixed-strings', 'augmentor-payload-needle', work], {encoding:'utf8'}), /search.txt/);
  await ctx.plugin(LocalSubprocessRuntime).await();
  const spec = {cwd:work, graceMs:200, stdio:{stdin:'ignore', stdout:{maxBytes:8192}, stderr:{maxBytes:8192}}};
  const shell = ctx.subprocess.spawn({...spec, argv:['/bin/sh', '-c', 'printf shell-ok | cat']});
  handles.push(shell);
  assert.equal((await shell.done).exitCode, 0);
  assert.equal(shell.collected.stdout.readFrom(0).text, 'shell-ok');
  assert.equal(await shell.waitForExit(AbortSignal.timeout(5000)), true);
  const slow = ctx.subprocess.spawn({...spec, argv:['/bin/sh', '-c', 'sleep 30 & wait']});
  handles.push(slow);
  await new Promise(resolve => setTimeout(resolve, 150));
  slow.terminate();
  assert.equal(await slow.waitForExit(AbortSignal.timeout(5000)), true);
  await slow.done;
  terminal = await ctx.subprocess.spawnTerminal({argv:['/bin/sh', '-c', 'printf terminal-ok; read answer; printf "reply:%s" "$answer"'],
    cwd:work, env:{TERM:'xterm-256color'}, rows:24, cols:80, graceMs:200});
  let output = '';
  terminal.output.on('data', data => { output += data.toString(); });
  await terminal.write('payload-input\n');
  assert.equal((await terminal.done).exitCode, 0);
  await finished(terminal.output);
  await terminal.terminate();
  assert.match(output, /terminal-ok/);
  assert.match(output, /reply:payload-input/);
  console.log(JSON.stringify({platform:process.platform, arch:process.arch, nativeFFI:true,
    ripgrep:true, shellPipeline:true, ordinaryTermination:true, terminalRoundTrip:true,
    arbitraryDetachedDescendantContainment:'not established'}));
} finally {
  for (const handle of handles) handle.terminate();
  if (terminal) await terminal.terminate();
  await ctx.fiber.dispose();
  clearTimeout(deadline);
  await rm(work, {recursive:true, force:true});
}
