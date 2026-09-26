#!/usr/bin/env node
// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Qualify the actual release graph, including compatible incremental candidates.
import {readFileSync,existsSync} from 'node:fs'
import {resolve,dirname} from 'node:path'
const root=resolve(process.argv[2]||'.'),visited=new Set()
function check(file){if(visited.has(file))return;visited.add(file);const code=readFileSync(file,'utf8');for(const match of code.matchAll(/(?:from\s*|import\s*\(\s*|import\s*)['"](\.[^'"]+)['"]/g)){const target=resolve(dirname(file),match[1]);if(!existsSync(target))throw Error('Missing release asset: '+target);if(/\.(mjs|js)$/.test(target))check(target)}}
for(const name of ['sidepanel.js','settings.mjs'])check(resolve(root,'apps/browser/extension',name))
console.log('Browser asset graph verified: '+visited.size+' modules')
