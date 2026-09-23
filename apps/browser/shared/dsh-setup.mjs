// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {readFileSync,existsSync} from 'node:fs'
import {join} from 'node:path'
import {homedir} from 'node:os'
import {promptCall} from '../../../dist/prompt-library/src/client.js'
export function dshConfiguration(){const file=join(process.env.AUGMENTOR_SHARED_CONFIG??join(process.env.XDG_CONFIG_HOME??join(homedir(),'.config'),'augmentor'),'harnesses.json');return existsSync(file)?JSON.parse(readFileSync(file,'utf8')).dsh??{}:{}}
export const dshSetup=({action='describe',...params}={})=>{if(!['describe','check','install','save'].includes(action))throw Error('Unsupported DSH setup action');return promptCall('dsh.'+action,params)}
