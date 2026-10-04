#!/usr/bin/env node
// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFileSync} from 'node:fs'
import {join} from 'node:path'
import {homedir} from 'node:os'
import {fileURLToPath} from 'node:url'
import {profileDirectory} from '../services/workspaces/profiles.mjs'
import {installProfile,recoverInstall} from '../services/workspaces/install.mjs'
import {dshConfiguration} from '../apps/browser/shared/dsh-setup.mjs'
const source=process.argv[2],profilesDir=profileDirectory()
if(source==='--recover'){console.log(recoverInstall({profilesDir})?'Recovered interrupted installation':'No interrupted installation');process.exit(0)}
if(!source)throw Error('Usage: install-workspace-profile.mjs /absolute/profile.json | --recover')
const profile=installProfile(JSON.parse(readFileSync(source,'utf8')),{root:fileURLToPath(new URL('../',import.meta.url)),home:process.env.DSH_HOME||dshConfiguration().home||join(homedir(),'.dsh'),profilesDir})
console.log('Registered Augmentor workspace profile '+profile.id+'. Conversations are preserved; services were not restarted.')
