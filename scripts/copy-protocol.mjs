// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {copyFileSync,cpSync,mkdirSync} from 'node:fs';
mkdirSync('dist/protocol',{recursive:true});
copyFileSync('packages/protocol/schema.json','dist/protocol/schema.json');
cpSync('packages/protocol/fixtures','dist/protocol/fixtures',{recursive:true});
