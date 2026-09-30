// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createInterface} from 'node:readline';
const send = value => process.stdout.write(JSON.stringify(value) + '\n');
createInterface({input: process.stdin}).on('line', line => {
  const r = JSON.parse(line);
  if (r.method === 'initialize') send({id: r.id, result: {userAgent: 'fixture'}});
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
