// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFileSync,lstatSync} from 'node:fs';
import {inspectSharedProfile,importSharedProfile} from '../dist/runtime/src/shared-profile-import.js';
import {inspectLegacySharedProfile,exportLegacySharedProfile} from '../dist/runtime/src/shared-profile-export.js';
process.umask(0o077);
const [command,file,...extra]=process.argv.slice(2);if(!file||extra.length)throw Error('Use inspect, import, inspect-legacy or export-legacy PRIVATE_MANIFEST. Stop all companion callers/services first.');
const stat=lstatSync(file);if(!stat.isFile()||stat.isSymbolicLink()||(stat.mode&0o077)||stat.size>65536)throw Error('Choose a bounded private regular shared-profile manifest.');
const value=JSON.parse(readFileSync(file,'utf8'));if(value.schema!=='augmentor-shared-profile-input/1')throw Error('Unsupported shared-profile manifest.');
if(command==='inspect')console.log(JSON.stringify(inspectSharedProfile(value.source),null,2));
else if(command==='import')console.log(JSON.stringify(await importSharedProfile(value.source,value.target,value.sourceSha256,{mapDefaultPerson:value.mapDefaultPerson}),null,2));
else if(command==='inspect-legacy')console.log(JSON.stringify(await inspectLegacySharedProfile(value.source),null,2));
else if(command==='export-legacy')console.log(JSON.stringify(await exportLegacySharedProfile(value.source,value.target,value.sourceSha256),null,2));
else throw Error('Use inspect, import, inspect-legacy or export-legacy. Interrupted target adoption uses import-dsh-projects.mjs inspect/finish/rollback against TARGET_DATA.');
