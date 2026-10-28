// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Test-only abrupt process termination after an actual filesystem publication.
import fs from 'node:fs';import {syncBuiltinESMExports} from 'node:module';import {basename,dirname,join} from 'node:path';
const sid=process.env.AUGMENTOR_BRANCH_PUBLICATION_KILL_ID,point=process.env.AUGMENTOR_BRANCH_PUBLICATION_KILL_POINT,state=process.env.AUGMENTOR_PI_STATE;
if(!sid||!['native','events','meta'].includes(point)||!state)throw Error('Branch publication crash fixture needs an isolated target.');
const original=fs.linkSync;
fs.linkSync=function(source,target){const result=original.apply(this,arguments),path=String(target);const matches=point==='native'?dirname(path)===join(state,'sessions',sid)&&basename(path).endsWith('.jsonl'):path===join(state,'sessions',sid+(point==='events'?'.events.jsonl':'.meta.json'));if(matches)process.kill(process.pid,'SIGKILL');return result;};
syncBuiltinESMExports();
