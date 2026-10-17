// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {verifyAssets,assetInventory} from '../adapters/dsh-legacy-format/assets.mjs';
const [source,view,assets,...extra]=process.argv.slice(2);if(!source||!view||!assets||extra.length)throw Error('Usage: node scripts/verify-dsh-legacy-assets.mjs PINNED_PUBLIC_SOURCE PRIVATE_VIEW PRIVATE_ASSETS');
const run=spawnSync(process.execPath,[fileURLToPath(new URL('./verify-dsh-legacy-view.mjs',import.meta.url)),resolve(source),resolve(view)],{encoding:'utf8',timeout:180000,maxBuffer:1024*1024});if(run.status!==0)throw Error('Historical view recomputation refused');
const checked=await verifyAssets(resolve(view),resolve(assets));assert.deepEqual((await assetInventory(resolve(view))).inventory,checked.manifest.inventory);await verifyAssets(resolve(view),resolve(assets));
console.log(JSON.stringify({completeViewRecomputed:true,referencedAssetsVerified:checked.manifest.assets.length,objectsVerified:checked.objects.size,combinedExpandedBytes:checked.combinedExpandedBytes,currentHarnessImportCompatible:false,nativeTargetsCreated:0,modelRequests:0}));
