// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {inspectNativeProfile,importNativeProfile} from '../dist/runtime/src/native-profile-import.js';
process.umask(0o077);
const [command,source,target,sha,...extra]=process.argv.slice(2);
if(command==='inspect'&&source&&!target)console.log(JSON.stringify(inspectNativeProfile(source),null,2));
else if(command==='import'&&source&&target&&sha&&!extra.length)console.log(JSON.stringify(await importNativeProfile(source,target,sha),null,2));
else throw Error('Usage: node scripts/import-native-profile.mjs inspect SOURCE_STATE | import SOURCE_STATE TARGET_STATE INSPECTED_SHA256. Stop both profiles first. Source is preserved; use import-dsh-projects.mjs inspect/finish/rollback for interrupted destination transactions.');
