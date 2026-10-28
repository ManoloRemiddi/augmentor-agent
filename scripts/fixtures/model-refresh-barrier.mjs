// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Test-only scheduling of one public SDK refresh in an empty authored profile.
import {ModelRuntime} from '@earendil-works/pi-coding-agent';
import {existsSync,renameSync,writeFileSync,appendFileSync} from 'node:fs';
import {join} from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
const root=process.env.AUGMENTOR_HARNESS_PROOF_MODEL_REFRESH_ROOT;
if(!root)throw Error('An owned refresh barrier is required.');
const original=ModelRuntime.prototype.refresh;
const trace=stage=>appendFileSync(join(root,'trace.jsonl'),JSON.stringify({stage,time:Date.now()})+'\n',{mode:0o600});
ModelRuntime.prototype.refresh=async function(options={}){
 if(existsSync(join(root,'armed'))){
  renameSync(join(root,'armed'),join(root,'consumed'));trace('held');
  writeFileSync(join(root,'held'),'Public SDK refresh entered',{mode:0o600});
  try{while(!existsSync(join(root,'release'))){options.signal?.throwIfAborted();await delay(10);}}catch(error){trace('aborted');throw error;}trace('released');
 }
 return original.call(this,options);
};
