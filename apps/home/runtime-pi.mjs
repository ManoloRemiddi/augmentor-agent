// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {Devices} from './devices.mjs';
import {PERSONA} from './persona.mjs';
import {createHomePiRuntime} from '../../dist/runtime/src/home.js';
export async function createRuntime(config,ledger){
 const devices=config.deviceMode==='selected'?new Devices(config,ledger.db):null;
 return createHomePiRuntime(config,ledger,devices,PERSONA);
}
