// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createInterface} from 'node:readline';
import {spawn} from 'node:child_process';
import {appendFileSync} from 'node:fs';
const send = value => process.stdout.write(JSON.stringify(value) + '\n');
createInterface({input: process.stdin}).on('line', line => {
  const r = JSON.parse(line);
  if (r.method === 'initialize') send({id: r.id, result: {userAgent: 'fixture'}});
  else if (r.method === 'thread/start') send({id:r.id,result:{thread:{id:'fixture-thread'}}});
  else if (r.method === 'thread/resume') {
    if(process.env.AUGMENTOR_CODEX_CREDENTIAL==='synthetic-resume-failure')send({id:r.id,error:{code:-32602,message:'Synthetic resume rejection'}});
    else {
      if(process.env.AUGMENTOR_CODEX_CREDENTIAL==='synthetic-slow-resume')send({method:'synthetic/resuming',params:{}});
      setTimeout(()=>send({id:r.id,result:{thread:{id:r.params.threadId}}}),process.env.AUGMENTOR_CODEX_CREDENTIAL==='synthetic-slow-resume'?250:0);
    }
  }
  else if (r.method === 'credential-marker') send({id:r.id,result:{marker:process.env.AUGMENTOR_CODEX_CREDENTIAL,pid:process.pid}});
  else if (r.method === 'descendant') {
    const child = spawn(process.execPath, ['-e', "process.on('SIGTERM',()=>{});process.stdout.write('ready');setInterval(()=>{},1000)"], {stdio: ['ignore', 'pipe', 'ignore']});
    child.stdout.once('data', () => send({id: r.id, result: {pid: child.pid}}));
  }
  else if (r.method === 'observe-term') {
    process.on('SIGTERM', () => {appendFileSync(r.params.path, 'TERM\n'); setTimeout(() => process.exit(0), 100);});
    send({id: r.id, result: {}});
  }
  else if (r.method === 'echo') setTimeout(() => send({id: r.id, result: r.params}), r.params.delay ?? 0);
  else if (r.method === 'fail') send({id: r.id, error: {code: -1, message: 'Fixture rejection'}});
  else if (r.method === 'notify') {send({method: 'item/agentMessage/delta', params: {delta: 'hello'}}); send({id: r.id, result: {}});}
  else if (r.method === 'resolve') {send({method: 'serverRequest/resolved', params: {threadId: 'fixture', requestId: 'approval'}}); send({id: r.id, result: {}});}
  else if (r.method === 'ask') {send({id: 'approval', method: 'item/commandExecution/requestApproval', params: {}}); send({id: r.id, result: {}});}
  else if (r.id === 'approval') send({method: 'answer', params: r});
  else if (r.method === 'bad') process.stdout.write('not-json\n');
  else if (r.method === 'large') process.stdout.write('x'.repeat(3000));
  else if (r.method === 'crash') process.exit(2);
  // 'wait' intentionally never acknowledges; verifies no replay.
});
