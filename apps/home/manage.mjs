// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Run inside the Home container; credentials and invite never enter argv/logs.
import {readFileSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
const [operation,role='owner']=process.argv.slice(2);
if(operation!=='invite'||!['owner','member','viewer'].includes(role))throw Error('Usage: node manage.mjs invite [owner|member|viewer]');
const token=readFileSync(process.env.HOME_AGENT_TOKEN_FILE,'utf8').trim();
const response=await fetch(`http://127.0.0.1:${process.env.PORT??8181}/clients/invite`,{method:'POST',redirect:'error',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({role}),signal:AbortSignal.timeout(5000)});
if(!response.ok)throw Error('Cannot create invitation; check Home health');
const {code,expires}=await response.json();
const path=join(process.env.HOME_STATE_DIR??'/state','pairing-code');
writeFileSync(path,code+'\n',{mode:0o600});
console.log(`Invitation saved privately to ${path}; valid until ${new Date(expires).toISOString()}. Open that file locally and enter the code in Home. It can be used once.`);
