// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {build} from 'esbuild';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const here=path.dirname(fileURLToPath(import.meta.url));
const read=file=>readFileSync(path.join(here,file),'utf8');
const upstream='node_modules/@novnc/novnc/';
const notices=['Augmentor Remote — third-party notices\n\nnoVNC 1.6.0 is bundled from unmodified upstream ESM sources.\nSource: https://codeload.github.com/novnc/noVNC/tar.gz/refs/tags/v1.6.0\nAugmentor source: https://github.com/ManoloRemiddi/augmentor-agent\n'];
for(const name of ['LICENSE.txt','AUTHORS','docs/LICENSE.MPL-2.0','docs/LICENSE.BSD-3-Clause','docs/LICENSE.BSD-2-Clause','vendor/pako/LICENSE'])notices.push(name+'\n\n'+read(upstream+name));
notices.push('DES attribution\n\n'+read(upstream+'core/crypto/des.js').split('*/')[0]+'*/');
notices.push('ws '+JSON.parse(read('node_modules/ws/package.json')).version+' (server dependency)\n\n'+read('node_modules/ws/LICENSE'));
mkdirSync(path.join(here,'build'),{recursive:true});
writeFileSync(path.join(here,'build/third-party.txt'),notices.join('\n\n'));
await build({absWorkingDir:here,entryPoints:['web/app.js'],bundle:true,format:'esm',outfile:'build/app.js',
  banner:{js:'/*! Copyright © 2026 Manolo Remiddi. Includes noVNC 1.6.0 (MPL-2.0) and third-party code. Notices and exact source links: /third-party.txt */'}});
