// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {copyFileSync,cpSync,mkdirSync,readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const attachmentSelection=JSON.parse(readFileSync('packages/runtime/vendor/dsh-attachment/SOURCE.json','utf8'));
const fontPreferenceRoot='packages/runtime/vendor/office-font-fallbacks';
const fontPreferenceSelection=JSON.parse(readFileSync(fontPreferenceRoot+'/SOURCE.json','utf8'));
for(const row of fontPreferenceSelection.files)if(createHash('sha256').update(readFileSync(fontPreferenceRoot+'/'+row.path)).digest('hex')!==row.sha256)throw Error('Native Office font preferences differ from public source: '+row.path);
cpSync(fontPreferenceRoot,'dist/runtime/vendor/office-font-fallbacks',{recursive:true});
copyFileSync('packages/runtime/src/office-native-linux.py','dist/runtime/src/office-native-linux.py');
copyFileSync('packages/runtime/src/office-scratch-linux.py','dist/runtime/src/office-scratch-linux.py');
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
const referenceSelection=JSON.parse(readFileSync('packages/runtime/vendor/dsh-file-reference/SOURCE.json','utf8'));
for(const row of referenceSelection.files)if(createHash('sha256').update(readFileSync('packages/runtime/vendor/dsh-file-reference/'+row.path)).digest('hex')!==row.sha256)throw Error('Public DSH file-reference source changed: '+row.path);
for(const name of ['LICENSE','SOURCE.json','SOURCE.md'])copyFileSync('packages/runtime/vendor/dsh-file-reference/'+name,'dist/runtime/vendor/dsh-file-reference/'+name);
const previewSelection=JSON.parse(readFileSync('packages/runtime/vendor/dsh-preview/SOURCE.json','utf8'));
for(const row of previewSelection.files)if(createHash('sha256').update(readFileSync('packages/runtime/vendor/dsh-preview/'+row.path)).digest('hex')!==row.sha256)throw Error('Public DSH file-preview source changed: '+row.path);
for(const name of ['LICENSE','SOURCE.json','SOURCE.md'])copyFileSync('packages/runtime/vendor/dsh-preview/'+name,'dist/runtime/vendor/dsh-preview/'+name);

const discoverySelection=JSON.parse(readFileSync('packages/runtime/vendor/dsh-model-discovery/SOURCE.json','utf8'));
for(const row of discoverySelection.files)if(createHash('sha256').update(readFileSync('packages/runtime/vendor/dsh-model-discovery/'+row.path)).digest('hex')!==row.sha256)throw Error('Public DSH model-discovery source changed: '+row.path);
for(const name of ['LICENSE','SOURCE.json'])copyFileSync('packages/runtime/vendor/dsh-model-discovery/'+name,'dist/runtime/vendor/dsh-model-discovery/'+name);

for(const name of ['dsh-plugin-wiki-tools','dsh-plugin-wiki-skills']){
 const source='packages/runtime/vendor/'+name;const selection=JSON.parse(readFileSync(source+'/SOURCE.json','utf8'));
 for(const row of selection.files)if(createHash('sha256').update(readFileSync(source+'/'+row.path)).digest('hex')!==row.sha256)throw Error('Public Wiki source changed: '+row.path);
 cpSync(source,'dist/runtime/vendor/'+name,{recursive:true});
}

const searchSource='packages/runtime/vendor/dsh-web-search-free';
const searchSelection=JSON.parse(readFileSync(searchSource+'/SOURCE.json','utf8'));
for(const row of searchSelection.files)if(createHash('sha256').update(readFileSync(searchSource+'/'+row.path)).digest('hex')!==row.sha256)throw Error('Public free search source changed: '+row.path);
cpSync(searchSource,'dist/runtime/vendor/dsh-web-search-free',{recursive:true});
for(const name of ['keyless-search','dsh-keyless-fetch']){
 const source='packages/runtime/vendor/'+name,selection=JSON.parse(readFileSync(source+'/SOURCE.json','utf8'));
 for(const row of selection.files)if(createHash('sha256').update(readFileSync(source+'/'+row.path)).digest('hex')!==row.sha256)throw Error('Public keyless source changed: '+name+'/'+row.path);
 cpSync(source,'dist/runtime/vendor/'+name,{recursive:true});
}

const exportSource='packages/runtime/vendor/dsh-session-log-export';
const exportSelection=JSON.parse(readFileSync(exportSource+'/SOURCE.json','utf8'));
for(const row of exportSelection.files)if(createHash('sha256').update(readFileSync(exportSource+'/'+row.path)).digest('hex')!==row.sha256)throw Error('Public DSH session-export source changed: '+row.path);
for(const name of ['LICENSE','SOURCE.json'])copyFileSync(exportSource+'/'+name,'dist/runtime/vendor/dsh-session-log-export/'+name);
