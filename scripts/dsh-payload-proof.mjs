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
let report;
const windows = process.platform === 'win32';
// Node creates redirected stdout/stderr lazily. Include the proof's own output
// pipes before comparing resources; a later console.log must not count as a
// terminal leak. The independent natural-exit and console-host checks remain.
void process.stdout;
void process.stderr;
const baselineResources = process.getActiveResourcesInfo();
const pwsh = process.env.AUGMENTOR_PWSH || 'pwsh.exe';
const deadline = setTimeout(() => { console.error('DSH payload proof timed out'); process.exit(1); }, 60000);
try {
  const koffi = require('koffi');
  const libc = koffi.load(windows ? 'kernel32.dll' : process.platform === 'darwin' ? '/usr/lib/libSystem.B.dylib' : 'libc.so.6');
  assert.equal(libc.func(windows ? 'uint32_t __stdcall GetCurrentProcessId()' : 'int getpid()')(), process.pid);
  const {rgPath} = await load('@vscode/ripgrep');
  await writeFile(join(work, 'search.txt'), 'augmentor-payload-needle\n');
  assert.match(execFileSync(rgPath, ['--fixed-strings', 'augmentor-payload-needle', work], {encoding:'utf8'}), /search.txt/);
  await ctx.plugin(LocalSubprocessRuntime).await();
  const spec = {cwd:work, graceMs:200, stdio:{stdin:'ignore', stdout:{maxBytes:8192}, stderr:{maxBytes:8192}}};
  const shell = ctx.subprocess.spawn({...spec, argv:windows
    ? [pwsh, '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', "Write-Output 'shell-ok' | ForEach-Object { $_ }"]
    : ['/bin/sh', '-c', 'printf shell-ok | cat']});
  handles.push(shell);
  assert.equal((await shell.done).exitCode, 0);
  assert.equal(shell.collected.stdout.readFrom(0).text.trim(), 'shell-ok');
  assert.equal(await shell.waitForExit(AbortSignal.timeout(5000)), true);
  const slow = ctx.subprocess.spawn({...spec, argv:windows
    ? [pwsh, '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', 'Start-Sleep -Seconds 30']
    : ['/bin/sh', '-c', 'sleep 30 & wait']});
  handles.push(slow);
  await new Promise(resolve => setTimeout(resolve, 150));
  slow.terminate();
  assert.equal(await slow.waitForExit(AbortSignal.timeout(5000)), true);
  await slow.done;
  for (let iteration=0; iteration<(windows?4:1); iteration++) {
    terminal = await ctx.subprocess.spawnTerminal({argv:windows
    ? [pwsh, '-NoLogo', '-NoProfile', '-Command', "Write-Output 'terminal-ok'; $answer=[Console]::ReadLine(); Write-Output ('reply:'+$answer)"]
    : ['/bin/sh', '-c', 'printf terminal-ok; read answer; printf "reply:%s" "$answer"'],
    cwd:work, env:{TERM:'xterm-256color'}, rows:24, cols:80, graceMs:200});
  let output = '';
  terminal.output.on('data', data => { output += data.toString(); });
  await terminal.write(windows ? 'payload-input\r' : 'payload-input\n');
  assert.equal((await terminal.done).exitCode, 0);
  await finished(terminal.output);
  await terminal.terminate();
  assert.match(output, /terminal-ok/);
  assert.match(output, /reply:payload-input/);
  }
  report = {platform:process.platform, arch:process.arch, nativeFFI:true,
    ripgrep:true, shellPipeline:true, ordinaryTermination:true, terminalRoundTrip:true,
    terminalRepetitions:windows?4:1,
    arbitraryDetachedDescendantContainment:'not established'};
  console.log(JSON.stringify({phase:'tool-checks-complete', ...report}));
} finally {
  for (const handle of handles) handle.terminate();
  if (terminal) await terminal.terminate();
  await ctx.fiber.dispose();
  clearTimeout(deadline);
  await rm(work, {recursive:true, force:true});
}
if (windows) {
  // node-pty's published drain interval is 1000 ms. Require both worker and
  // client pipe cleanup to settle while the host is still alive, not at exit.
  await new Promise(resolve=>setTimeout(resolve,2500));
  const remaining=process.getActiveResourcesInfo();
  for(const kind of ['PipeWrap','ProcessWrap','MessagePort']){
    assert.ok(remaining.filter(x=>x===kind).length<=baselineResources.filter(x=>x===kind).length,
      'Windows terminal resources remain after disposal: '+JSON.stringify({baseline:baselineResources,remaining}));
  }
  const filter=`ParentProcessId = ${process.pid} AND (Name = 'OpenConsole.exe' OR Name = 'conhost.exe')`;
  const children=execFileSync(pwsh,['-NoLogo','-NoProfile','-NonInteractive','-Command',
    `(Get-CimInstance Win32_Process -Filter "${filter}" | Measure-Object).Count`],{encoding:'utf8'}).trim();
  assert.equal(children,'0','A terminal console host survived natural shell exit');
  report.terminalResourcesReleased=true;
}
// A resolved terminal API is insufficient if its worker/pipe keeps the host
// alive. Require natural exit after disposal and keep only bounded, non-content
// diagnostics if an upstream native resource remains referenced.
setTimeout(() => {
  console.error(JSON.stringify({phase:'shutdown-failed', resources:process.getActiveResourcesInfo(),
    handles:process._getActiveHandles().map(handle=>({kind:handle.constructor.name,
      ...(Number.isInteger(handle.pid)?{pid:handle.pid,connected:handle.connected}: {})}))}));
  process.exit(1);
}, 10000).unref();
process.once('beforeExit', () => console.log(JSON.stringify({...report, naturalShutdown:true})));
