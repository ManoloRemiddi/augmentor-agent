// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {copyFileSync,cpSync,mkdirSync} from 'node:fs';
mkdirSync('dist/protocol',{recursive:true});
copyFileSync('packages/protocol/schema.json','dist/protocol/schema.json');
cpSync('packages/protocol/fixtures','dist/protocol/fixtures',{recursive:true});
cpSync('packages/harness-ui/vendor','dist/harness-ui/vendor',{recursive:true});
copyFileSync('packages/harness-ui/src/queue-view.js','dist/harness-ui/src/queue-view.js');
copyFileSync('packages/runtime/vendor/pi/LICENSE','dist/runtime/vendor/pi/LICENSE');
copyFileSync('packages/runtime/vendor/pi/SOURCE.md','dist/runtime/vendor/pi/SOURCE.md');
