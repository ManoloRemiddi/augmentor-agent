// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {copyFileSync,cpSync,mkdirSync,readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const attachmentSelection=JSON.parse(readFileSync('packages/runtime/vendor/dsh-attachment/SOURCE.json','utf8'));
for(const row of attachmentSelection.files)if(createHash('sha256').update(readFileSync('packages/runtime/vendor/dsh-attachment/'+row.path)).digest('hex')!==row.sha256)throw Error('Public DSH attachment source changed: '+row.path);
mkdirSync('dist/protocol',{recursive:true});
copyFileSync('packages/protocol/schema.json','dist/protocol/schema.json');
cpSync('packages/protocol/fixtures','dist/protocol/fixtures',{recursive:true});
cpSync('packages/harness-ui/vendor','dist/harness-ui/vendor',{recursive:true});
copyFileSync('packages/harness-ui/src/queue-view.js','dist/harness-ui/src/queue-view.js');
copyFileSync('packages/runtime/vendor/pi/LICENSE','dist/runtime/vendor/pi/LICENSE');
copyFileSync('packages/runtime/vendor/pi/SOURCE.md','dist/runtime/vendor/pi/SOURCE.md');
cpSync('packages/runtime/vendor/adaptive-reasoning','dist/runtime/vendor/adaptive-reasoning',{recursive:true});
copyFileSync('packages/runtime/vendor/dsh-goal/LICENSE','dist/runtime/vendor/dsh-goal/LICENSE');
copyFileSync('packages/runtime/vendor/dsh-goal/SOURCE.md','dist/runtime/vendor/dsh-goal/SOURCE.md');
copyFileSync('packages/runtime/vendor/dsh-jobs/LICENSE','dist/runtime/vendor/dsh-jobs/LICENSE');
copyFileSync('packages/runtime/vendor/dsh-jobs/SOURCE.md','dist/runtime/vendor/dsh-jobs/SOURCE.md');

for(const name of ['LICENSE','SOURCE.json'])copyFileSync('packages/runtime/vendor/dsh-attachment/'+name,'dist/runtime/vendor/dsh-attachment/'+name);
