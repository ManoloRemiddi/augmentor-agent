// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {paths} from '../dist/runtime/src/storage.js';
import {provisionHarnessDefaults} from '../dist/runtime/src/installation-defaults.js';
if(process.argv.length!==2)throw Error('Choose the target profile with AUGMENTOR_PI_CONFIG. This command preserves existing choices and never restarts a runtime.');
console.log(JSON.stringify(provisionHarnessDefaults(paths().config)));
