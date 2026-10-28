// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {importDshProject} from '../dist/runtime/src/dsh-project-import.js';
import {lstatSync,readFileSync} from 'node:fs';
const [source,state,sha256,provider,model,...extra]=process.argv.slice(2);
if(!source||!state||!sha256||!provider||!model||extra.length&&!(extra.length===2&&extra[0]==='--session-selections'))throw Error('Usage: node scripts/import-dsh-project.mjs EXPORT NEW_STATE SHA256 PROVIDER MODEL [--session-selections PRIVATE_JSON]. Offline project import; destination must not exist.');
process.umask(0o077);
let sessionSelections;if(extra.length){const info=lstatSync(extra[1]);if(!info.isFile()||info.isSymbolicLink()||info.size>1024*1024)throw Error('Session model choices must be a bounded regular JSON file.');sessionSelections=JSON.parse(readFileSync(extra[1],'utf8'));}
console.log(JSON.stringify(await importDshProject(source,state,{sourceSha256:sha256,selection:{provider,model},...(sessionSelections===undefined?{}:{sessionSelections})}),null,2));
