// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {importDshProject} from '../dist/runtime/src/dsh-project-import.js';
const [source,state,sha256,provider,model,...extra]=process.argv.slice(2);
if(!source||!state||!sha256||!provider||!model||extra.length)throw Error('Usage: node scripts/import-dsh-project.mjs EXPORT NEW_STATE SHA256 PROVIDER MODEL. Offline pilot; destination must not exist.');
process.umask(0o077);
console.log(JSON.stringify(importDshProject(source,state,{sourceSha256:sha256,selection:{provider,model}}),null,2));
