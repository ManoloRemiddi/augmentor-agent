// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {writeFile} from 'node:fs/promises';
import {managementOwner} from './fixtures/mcp-management-owner.mjs';
test('production Native Settings MCP entry runs explicit SDK commands and closes on stale controller state',{skip:process.platform!=='linux',timeout:90000},async t=>{
 const owner=await managementOwner(t);await owner.stop();const release=join(owner.root,'release-native-reload'),extension=join(owner.root,'authored-native-reload.mjs');
 await writeFile(extension,'import {existsSync} from "node:fs";import {setTimeout as delay} from "node:timers/promises";export default pi=>{pi.on("session_shutdown",async event=>{if(event.reason!=="reload")return;const deadline=Date.now()+15000;while(!existsSync('+JSON.stringify(release)+')&&Date.now()<deadline)await delay(10);if(!existsSync('+JSON.stringify(release)+'))throw Error("AUTHORED_NATIVE_RELOAD_RELEASE_TIMEOUT");});};');await writeFile(join(owner.config,'resources.json'),JSON.stringify({sources:[extension],skills:[]}));owner.env.AUGMENTOR_MCP_FIXTURE_RELEASE_RELOAD=release;await owner.start();await owner.create('native-manager');let native;
 t.after(async()=>{if(native?.exitCode===null&&native.signalCode===null){const exit=once(native,'exit');native.kill('SIGTERM');await exit;}});
 const python=process.env.AUGMENTOR_PYTHON??'python3';native=spawn(python,['-B',fileURLToPath(new URL('./fixtures/native-pi-mcp.py',import.meta.url))],{env:{...owner.env,AUGMENTOR_PYTHON:python,AUGMENTOR_PI_NO_AUTOSTART:'1',AUGMENTOR_DESKTOP_AUTOSTART:'0',AUGMENTOR_DESKTOP_KEY:'mcp-'+crypto.randomUUID(),AUGMENTOR_WINDOW_ID:'main',PYTHONPATH:join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT||'.'),'apps/native'),QT_QPA_PLATFORM:'offscreen'},stdio:['ignore','pipe','pipe']});
 let output='',errors='';native.stdout.on('data',data=>output+=data);native.stderr.on('data',data=>errors+=data);const [code]=await once(native,'exit');assert.equal(code,0,errors+output);assert(output.includes('native-pi-mcp'));assert.equal(owner.requests.length,0);assert.equal(owner.wire.stats.codeGrants,1);assert.equal(owner.wire.stats.pkceVerified,1);assert.equal(owner.wire.stats.tools,0);assert.deepEqual(owner.wire.errors,[]);
});
