// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFileSync,lstatSync} from 'node:fs';
import {importDshProjects} from '../dist/runtime/src/dsh-project-batch.js';
import {recoverStateTransaction} from '../dist/runtime/src/profile-transaction.js';
process.umask(0o077);
const [command,file,state,...extra]=process.argv.slice(2);
if(command==='import'&&file&&state&&!extra.length){
 const stat=lstatSync(file);if(!stat.isFile()||stat.isSymbolicLink()||stat.size>1024*1024)throw Error('Choose a bounded regular private batch manifest.');
 const manifest=JSON.parse(readFileSync(file,'utf8'));if(manifest.schema!=='augmentor-dsh-project-batch-input/1'||!Array.isArray(manifest.projects))throw Error('Invalid project batch manifest.');
 console.log(JSON.stringify(await importDshProjects(manifest.projects,state),null,2));
}else if(['inspect','finish','rollback'].includes(command)&&file&&!state){console.log(JSON.stringify(recoverStateTransaction(file,command),null,2));}
else throw Error('Usage: node scripts/import-dsh-projects.mjs import PRIVATE_MANIFEST STATE | inspect STATE | finish STATE | rollback STATE. Stop the profile first. Existing chats are preserved; divergent sources are refused.');
