// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Loaded Chromium extension + native messaging + pinned Codex; synthetic model and page only.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createServer} from 'node:http';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp, mkdir, readFile, writeFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
import {CodexHost} from '../dist/codex-runtime/src/host.js';
import {CodexIpcServer} from '../dist/codex-runtime/src/ipc.js';
import {ProfileStore} from '../dist/codex-runtime/src/profiles.js';
import {memoryServices} from './fixtures/codex/memory-services.mjs';

const repo = fileURLToPath(new URL('../', import.meta.url));
async function cdp(url) {
  const ws = new WebSocket(url); await once(ws, 'open');
  let id = 0; const pending = new Map();
  ws.addEventListener('message', event => {const frame = JSON.parse(event.data); const request = pending.get(frame.id); if (request) {pending.delete(frame.id); clearTimeout(request.timer); frame.error ? request.reject(new Error(frame.error.message)) : request.resolve(frame.result);}});
  const call = (method, params = {}) => new Promise((resolve, reject) => {const key = ++id; const timer = setTimeout(() => {pending.delete(key); reject(new Error('CDP timeout: ' + method));}, 10000); pending.set(key, {resolve, reject, timer}); ws.send(JSON.stringify({id: key, method, params}));});
  return {call, close: () => {for (const row of pending.values()) clearTimeout(row.timer); ws.close();}, evaluate: async expression => {
    const response = await call('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true});
    if (response.exceptionDetails) throw new Error(JSON.stringify(response.exceptionDetails));
    return response.result.value;
  }};
}

test('loaded Chromium extension executes Codex-observed typing, clicking and screenshots on an isolated page', {skip: process.platform !== 'linux', timeout: 45000}, async t => {
  const root = await mkdtemp(join(tmpdir(), 'codex-chromium-')); const sockets = [];
  let chrome, ipc, memory; let rounds = 0; const modelInputs = [];
  let queueMode = false, queueRounds = 0, releaseQueue; const queueInputs = [];
  const server = createServer(async (req, res) => {
    if (req.url === '/page') {
      res.setHeader('content-type', 'text/html');
      res.end('<!doctype html><title>Codex browser fixture</title><input id="fixture-input"><button id="fixture-button" onclick="document.body.dataset.clicks=String(Number(document.body.dataset.clicks||0)+1)">Fixture action</button>'); return;
    }
    if (req.url !== '/v1/responses') {res.writeHead(404); res.end(); return;}
    let body = ''; for await (const part of req) body += part; modelInputs.push(JSON.parse(body));
    if (queueMode) {
      queueInputs.push(modelInputs.at(-1)); const number = ++queueRounds;
      const item = {id: 'queue-answer-' + number, type: 'message', role: 'assistant', status: 'completed', content: [{type: 'output_text', text: 'Queue fixture answer ' + number, annotations: []}]};
      res.writeHead(200, {'content-type': 'text/event-stream'});
      res.write('data: ' + JSON.stringify({type: 'response.created', response: {id: 'queue-' + number, status: 'in_progress', output: []}}) + '\n\n');
      const finish = () => {
        for (const frame of [{type: 'response.output_item.added', output_index: 0, item}, {type: 'response.output_item.done', output_index: 0, item}, {type: 'response.completed', response: {id: 'queue-' + number, status: 'completed', output: [item]}}]) res.write('data: ' + JSON.stringify(frame) + '\n\n');
        res.end();
      };
      if (number === 1) releaseQueue = finish; else finish();
      return;
    }
    const action = [
      ['browser_snapshot', {}], ['browser_type', {selector: '#fixture-input', text: 'Codex typed once'}],
      ['browser_snapshot', {}], ['browser_click', {selector: '#fixture-button'}], ['browser_screenshot', {}],
    ][rounds++];
    const item = action ? {id: 'call_' + rounds, type: 'function_call', call_id: 'fixture_' + rounds, name: action[0], arguments: JSON.stringify(action[1])} :
      {id: 'answer', type: 'message', role: 'assistant', status: 'completed', content: [{type: 'output_text', text: 'Browser fixture finished.', annotations: []}]};
    res.writeHead(200, {'content-type': 'text/event-stream'});
    for (const frame of [
      {type: 'response.created', response: {id: 'response_' + rounds, status: 'in_progress', output: []}},
      {type: 'response.output_item.added', output_index: 0, item},
      {type: 'response.output_item.done', output_index: 0, item},
      {type: 'response.completed', response: {id: 'response_' + rounds, status: 'completed', output: [item]}},
    ]) res.write('data: ' + JSON.stringify(frame) + '\n\n');
    res.end();
  });
  t.after(async () => {
    for (const socket of sockets) socket.close();
    if (chrome?.pid && chrome.exitCode === null) {const exited = once(chrome, 'exit'); chrome.kill(); await exited;}
    await ipc?.close(); server.closeAllConnections(); await new Promise(resolve => server.close(resolve));
    await memory?.close();
    await rm(root, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const profiles = new ProfileStore(join(root, 'profiles.json'), {get: async () => undefined, put: async () => {}, delete: async () => {}});
  await profiles.upsert({id: 'fixture', name: 'Isolated fixture', kind: 'local', model: 'fixture-model', endpoint: base + '/v1'});
  await profiles.validated('fixture', 1, 'image'); // Qualification fixture; provider-probe pixel decoding has separate coverage.
  memory = await memoryServices(root);
  const host = new CodexHost({root: join(root, 'host'), memoryCall: memory.call, profiles, resolveProfile: id => profiles.resolve(id)});
  ipc = new CodexIpcServer(host, join(root, 'runtime.sock')); await ipc.listen();
  const extension = join(repo, 'apps/browser/extension');
  const manifest = JSON.parse(await readFile(join(extension, 'manifest.json')));
  const extensionId = createHash('sha256').update(Buffer.from(manifest.key, 'base64')).digest('hex').slice(0, 32).replace(/[0-9a-f]/g, char => String.fromCharCode(97 + parseInt(char, 16)));
  const profile = join(root, 'chromium'); await mkdir(join(profile, 'NativeMessagingHosts'), {recursive: true});
  const launcher = join(root, 'native-host');
  const env = {AUGMENTOR_CODEX_STATE: join(root, 'host'), AUGMENTOR_CODEX_SOCKET: ipc.socketPath, AUGMENTOR_CODEX_BROWSER_WORKSPACE: join(root, 'workspace'), AUGMENTOR_WORKSPACE_PROFILE: '', AUGMENTOR_SHARED_STATE: memory.state, AUGMENTOR_SHARED_DATA: memory.data};
  // JSON strings are valid JavaScript literals; executable path and argv never pass through a shell.
  await writeFile(launcher, '#!' + process.execPath + '\n' + `Object.assign(process.env, ${JSON.stringify(env)});import(${JSON.stringify('file://' + join(repo, 'apps/browser/native-host.mjs'))});\n`, {mode: 0o700});
  await writeFile(join(profile, 'NativeMessagingHosts/com.augmentor.agent.json'), JSON.stringify({name: 'com.augmentor.agent', description: 'Isolated Codex proof', path: launcher, type: 'stdio', allowed_origins: [`chrome-extension://${extensionId}/`]}));
  const isolatedEnv = Object.fromEntries(Object.entries(process.env).filter(([key]) => !/^(AUGMENTOR_|DSH_|PI_)/.test(key)));
  await mkdir(join(root, 'runtime'), {mode: 0o700});
  chrome = spawn(process.env.CHROMIUM_BIN ?? 'chromium', ['--headless=new', '--enable-unsafe-extension-debugging', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', '--user-data-dir=' + profile, '--load-extension=' + extension, '--disable-extensions-except=' + extension, base + '/page'], {env: {...isolatedEnv, HOME: root, XDG_CONFIG_HOME: join(root, 'config'), XDG_STATE_HOME: join(root, 'state'), XDG_DATA_HOME: join(root, 'data'), XDG_RUNTIME_DIR: join(root, 'runtime')}, stdio: 'ignore'});
  let port;
  for (let attempt = 0; attempt < 100; attempt++) {try {port = (await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]; break;} catch {await delay(50);}}
  assert.ok(port, 'Isolated Chromium started');
  const targets = () => fetch(`http://127.0.0.1:${port}/json`).then(response => response.json());
  const pageTarget = (await targets()).find(target => target.url === base + '/page'); assert.ok(pageTarget);
  const page = await cdp(pageTarget.webSocketDebuggerUrl); sockets.push(page);
  const created = await page.call('Target.createTarget', {url: `chrome-extension://${extensionId}/sidepanel.html`});
  let panelTarget;
  for (let attempt = 0; attempt < 100; attempt++) {panelTarget = (await targets()).find(target => target.id === created.targetId); if (panelTarget) break; await delay(50);}
  assert.ok(panelTarget); const panel = await cdp(panelTarget.webSocketDebuggerUrl); sockets.push(panel);
  // Target discovery can precede navigation into the extension document. Wait
  // for that context and its API before sending any mutating panel message.
  let panelReady = false, panelReadinessError;
  for (let attempt = 0; attempt < 100; attempt++) {
    try {
      panelReady = await panel.evaluate(`location.href === ${JSON.stringify(`chrome-extension://${extensionId}/sidepanel.html`)} && document.readyState === 'complete' && typeof globalThis.chrome?.runtime?.sendMessage === 'function' && Boolean(document.querySelector('#input'))`);
      if (panelReady) break;
    } catch (error) {panelReadinessError = error.message;}
    await delay(50);
  }
  assert.equal(panelReady, true, panelReadinessError ?? 'Extension document and messaging API became ready');
  const message = value => panel.evaluate(`chrome.runtime.sendMessage(${JSON.stringify(value)})`);
  assert.equal((await message({type: 'harness/select', harness: 'codex'})).ok, true);
  let status;
  for (let attempt = 0; attempt < 100; attempt++) {status = await message({type: 'connect'}); if (status.phase === 'ready') break; await delay(100);}
  assert.equal(status.phase, 'ready', JSON.stringify(status));
  assert.equal((await message({type:'log'})).capabilities.memory, true, 'Browser advertises the actual host memory capability');
  await page.call('Page.bringToFront');
  const denied = await panel.evaluate('chrome.tabs.captureVisibleTab(undefined, {format: "jpeg"}).then(() => "captured", error => error.message)');
  assert.match(denied, /activeTab|all_urls|permission/i, 'No screenshot grant before a toolbar action');
  const browserTarget = await fetch(`http://127.0.0.1:${port}/json/version`).then(response => response.json());
  const browserControl = await cdp(browserTarget.webSocketDebuggerUrl); sockets.push(browserControl);
  const tabTargets = await browserControl.call('Target.getTargets', {filter: [{type: 'tab', exclude: false}]});
  const workTab = tabTargets.targetInfos.find(target => target.url === base + '/page'); assert.ok(workTab);
  await browserControl.call('Extensions.triggerAction', {id: extensionId, targetId: workTab.targetId});
  const submitted = await message({type: 'prompt', text: 'Use the isolated fixture page: type the fixture text, then click its action once.'});
  assert.equal(submitted.ok, true, JSON.stringify(submitted));
  for (let attempt = 0; attempt < 200; attempt++) {status = await message({type: 'connect'}); if (rounds >= 6 && !status.running) break; await delay(50);}
  assert.equal(rounds, 6); assert.equal(status.running, false);
  assert.deepEqual(await page.evaluate('({text:document.querySelector("#fixture-input").value,clicks:document.body.dataset.clicks})'), {text: 'Codex typed once', clicks: '1'});
  let rendered = false;
  for (let attempt = 0; attempt < 20; attempt++) {rendered = await panel.evaluate('document.body.innerText.includes("Browser fixture finished.")'); if (rendered) break; await delay(50);}
  assert.equal(rendered, true, 'The loaded panel renders the final Codex reply');
  const toolOutputs = modelInputs.at(-1).input.filter(item => item.type === 'function_call_output');
  assert.equal(toolOutputs.length, 5);
  const image = toolOutputs.flatMap(item => Array.isArray(item.output) ? item.output : []).find(item => item.type === 'input_image');
  assert.ok(image?.image_url?.startsWith('data:image/jpeg;base64,'), 'Pinned Codex forwards the actual screenshot as image input');
  assert.ok(Buffer.from(image.image_url.split(',')[1], 'base64').length > 100, 'Actual Chromium JPEG pixels, not an image placeholder');
  assert.ok(toolOutputs.every(item => !JSON.stringify(item.output).includes('unknown outcome')));
  // Exercise actual loaded composer and row controls, rather than bypassing the panel.
  queueMode = true;
  assert.equal((await message({type: 'prompt', text: 'Hold for the Browser queue fixture.'})).accepted, true);
  async function panelUntil(expression, description) {
    for (let attempt = 0; attempt < 160; attempt++) {try {if (await panel.evaluate(expression)) return;} catch {} await delay(50);}
    throw Error('Browser queue timeout: ' + description + ' ' + await panel.evaluate("document.querySelector('#prompt-queue')?.innerText"));
  }
  await panelUntil('!document.querySelector("#stop").hidden && !document.querySelector("#send").hidden && !document.querySelector("#send").disabled', 'queue composer ready');
  async function enter(text) {
    await panel.evaluate(`(()=>{const input=document.querySelector('#input');input.value=${JSON.stringify(text)};input.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));return true})()`);
    await panelUntil(`Array.from(document.querySelectorAll('.queue-row')).some(row=>row.textContent.includes(${JSON.stringify(text)})&&row.querySelector('button')?.textContent==='Steer')`, 'queued row');
    return panel.evaluate(`Array.from(document.querySelectorAll('.queue-row')).find(row=>row.textContent.includes(${JSON.stringify(text)})).dataset.queueId`);
  }
  async function action(id, label) {
    const lookup=`Array.from(document.querySelectorAll('.queue-row')).find(row=>row.dataset.queueId===${JSON.stringify(id)})`;
    await panelUntil(`(()=>{const row=${lookup};return row&&Array.from(row.querySelectorAll('button')).some(b=>b.textContent===${JSON.stringify(label)}&&!b.disabled)})()`, 'row action enabled');
    await panel.evaluate(`(()=>{const row=${lookup};Array.from(row.querySelectorAll('button')).find(b=>b.textContent===${JSON.stringify(label)}).click();return true})()`);
  }
  const correction = await enter('BROWSER_QUEUE_CORRECTION');
  await action(correction, 'Steer');
  await panelUntil(`!Array.from(document.querySelectorAll('.queue-row')).some(row=>row.dataset.queueId===${JSON.stringify(correction)}&&row.querySelector('button')&&!row.querySelector('button').disabled)`, 'steering accepted');
  const removed = await enter('BROWSER_QUEUE_REMOVED'); await action(removed, '×');
  await panelUntil(`!Array.from(document.querySelectorAll('.queue-row')).some(row=>row.dataset.queueId===${JSON.stringify(removed)})`, 'removed row');
  const next = await enter('BROWSER_QUEUE_NEXT');
  await panel.call('Page.reload');
  await panelUntil(`document.readyState==='complete'&&Array.from(document.querySelectorAll('.queue-row')).some(row=>row.dataset.queueId===${JSON.stringify(next)})`, 'reload restores waiting row');
  if (process.env.AUGMENTOR_QUEUE_SCREENSHOT) await writeFile(process.env.AUGMENTOR_QUEUE_SCREENSHOT, Buffer.from((await panel.call('Page.captureScreenshot', {format:'png'})).data, 'base64'));
  assert.equal(typeof releaseQueue, 'function'); releaseQueue();
  await panelUntil('document.body.innerText.includes("Queue fixture answer 3") && document.querySelector("#prompt-queue").hidden', 'ordered completion');
  assert.equal(queueRounds, 3);
  assert.equal(queueInputs[1].input.filter(item=>item.role==='user'&&JSON.stringify(item.content).includes('BROWSER_QUEUE_CORRECTION')).length, 1);
  assert.doesNotMatch(JSON.stringify(queueInputs), /BROWSER_QUEUE_REMOVED/);
  assert.doesNotMatch(JSON.stringify(queueInputs[1].input), /BROWSER_QUEUE_NEXT/);
  assert.match(JSON.stringify(queueInputs[2].input), /BROWSER_QUEUE_NEXT/);
  const currentBrief = queueInputs[2].input.filter(item => item.role === 'user' && JSON.stringify(item.content).includes('external_augmentor_memory_data'));
  assert.match(JSON.stringify(currentBrief), /BROWSER_QUEUE_CORRECTION/, 'the next Browser turn receives committed continuity');
  assert.doesNotMatch(JSON.stringify(currentBrief), /BROWSER_QUEUE_REMOVED/);

  // Activate actual transcript controls and continue in each exact child.
  const sourceId=(await message({type:'connect'})).sessionId;
  await panelUntil('document.querySelector(".msg-branch")&&!document.querySelector("#send").disabled','Branch available');
  // Visible answer text precedes the native terminal notification. Snapshot only
  // after the authoritative ledger settles, so a late turn/end is not mistaken
  // for a mutation caused by Branch.
  let sourceSettled=false;
  for(let attempt=0;attempt<100;attempt++){
    const state=await host.dispatch('session.queue',{sessionId:sourceId});
    if(state.operations.length&&state.operations.every(op=>['completed','failed','interrupted','cancelled'].includes(op.status))){sourceSettled=true;break;}
    await delay(20);
  }
  assert.equal(sourceSettled,true,'source turn settled before immutable history snapshot');
  const sourceHistory=await host.dispatch('session.history',{sessionId:sourceId,maxMessages:100});
  await panel.evaluate('document.querySelector(".msg-branch").click()');
  let childId;
  for(let attempt=0;attempt<100;attempt++){
    const current=await message({type:'connect'});
    if(current.sessionId!==sourceId){childId=current.sessionId;break;}await delay(50);
  }
  assert.ok(childId,'Branch selected a child');
  await panelUntil('document.body.innerText.includes("Browser fixture finished.")&&!document.body.innerText.includes("Queue fixture answer 3")','exact branch display');
  assert.equal(queueRounds,3,'Branch does not invoke inference');
  assert.deepEqual(await host.dispatch('session.history',{sessionId:sourceId,maxMessages:100}),sourceHistory);
  await panel.evaluate(`(()=>{const input=document.querySelector('#input');input.value='BROWSER_BRANCH_CHILD';input.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));})()`);
  await panelUntil('document.body.innerText.includes("Queue fixture answer 4")&&!document.querySelector("#send").disabled','child response');
  assert.doesNotMatch(JSON.stringify(queueInputs[3].input),/BROWSER_QUEUE_NEXT|BROWSER_QUEUE_CORRECTION/);
  assert.equal(queueInputs[3].input.filter(item=>item.type==='function_call_output').length,5,'native tool outputs remain in child context');
  await panel.evaluate(`(()=>{document.querySelector('#input').value='BROWSER_EDIT_DRAFT';document.querySelector('.msg-edit').click();})()`);
  await panelUntil('document.querySelector("#input").value==="BROWSER_BRANCH_CHILD"','Edit loaded exact latest input');
  await panel.evaluate(`(()=>{const input=document.querySelector('#input');input.value='BROWSER_EDITED_CHILD';input.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));})()`);
  await panelUntil('document.body.innerText.includes("Queue fixture answer 5")&&document.querySelector("#input").value==="BROWSER_EDIT_DRAFT"','edited child response and original draft');
  const editedId=(await message({type:'connect'})).sessionId;
  assert.notEqual(editedId,childId);
  assert.match(JSON.stringify(queueInputs[4].input),/BROWSER_EDITED_CHILD/);
  assert.doesNotMatch(JSON.stringify(queueInputs[4].input),/BROWSER_BRANCH_CHILD|BROWSER_EDIT_DRAFT|BROWSER_QUEUE_NEXT/);
  await panel.call('Page.reload');
  await panelUntil('document.body.innerText.includes("BROWSER_EDITED_CHILD")&&document.body.innerText.includes("Queue fixture answer 5")','edited history after reload');
  assert.equal((await message({type:'connect'})).sessionId,editedId);
  assert.equal(queueRounds,5,'reload does not repeat edited submission');
  await host.release(editedId); await host.release(childId); await host.release(sourceId);
  const exported = (await memory.call('memory.dual.export', {session:'codex:' + sourceId})).events;
  const sourceRows = exported.filter(row => row.session === 'codex:' + sourceId);
  const publicSource = sourceHistory.events.map(row => row.event).filter(event => ['user/message','assistant/message'].includes(event.type)).map(event =>
    (event.type === 'user/message' ? event.data.content : event.data.message.content).filter(part => part.type === 'text').map(part => part.text).join('\n'));
  assert.deepEqual(sourceRows.map(row => row.content), publicSource, 'every completed public item captures once, including steering replies');
  assert.deepEqual(exported.filter(row => row.session === 'codex:' + childId).map(row => row.content), ['BROWSER_BRANCH_CHILD','Queue fixture answer 4']);
  assert.deepEqual(exported.filter(row => row.session === 'codex:' + editedId).map(row => row.content), ['BROWSER_EDITED_CHILD','Queue fixture answer 5']);
  assert.doesNotMatch(JSON.stringify(exported), /BROWSER_QUEUE_REMOVED|augmentor_memory_manifest|external_augmentor_memory_data|Codex typed once/);
  assert.equal(await panel.evaluate('document.body.innerText.includes("augmentor_memory_manifest")||document.body.innerText.includes("external_augmentor_memory_data")'), false);

  // Open the existing Settings page and activate its actual memory controls.
  const settingTarget = await page.call('Target.createTarget', {url:`chrome-extension://${extensionId}/settings.html#memory`});
  let settingInfo;
  for (let attempt=0;attempt<100;attempt++) {settingInfo=(await targets()).find(target=>target.id===settingTarget.targetId);if(settingInfo)break;await delay(50);}
  assert.ok(settingInfo);const settings=await cdp(settingInfo.webSocketDebuggerUrl);sockets.push(settings);
  async function memoryUntil(expression, label) {
    for (let attempt=0;attempt<160;attempt++) {try {if(await settings.evaluate(expression))return;}catch{}await delay(50);}
    throw Error('Browser memory settings timeout: '+label);
  }
  await memoryUntil('Array.from(document.querySelectorAll("summary")).some(node=>node.textContent.includes("manual setup and stored memories"))','existing settings section');
  await settings.evaluate('Array.from(document.querySelectorAll("summary")).find(node=>node.textContent.includes("manual setup and stored memories")).click()');
  await memoryUntil('document.body.innerText.includes("Automatic memory is on.")','shared-memory status');
  const clickMemory = label => settings.evaluate(`Array.from(document.querySelectorAll('button')).find(button=>button.textContent===${JSON.stringify(label)}).click()`);
  await clickMemory('Pause automatic memory');
  await memoryUntil('document.body.innerText.includes("Automatic memory is paused.")','pause acknowledgement');
  assert.equal((await memory.call('memory.dual.describe')).enabled, 0);
  await clickMemory('Resume automatic memory');
  await memoryUntil('document.body.innerText.includes("Automatic memory is on.")','resume acknowledgement');
  assert.equal((await memory.call('memory.dual.describe')).enabled, 1);
  assert.equal((await memory.call('memory.dual.describe')).events, exported.length, 'controls preserve the captured source journal');
});
