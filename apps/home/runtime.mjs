// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Explicit backend selection preserves the existing Home API and legacy default.
export {PERSONA} from './persona.mjs';
export async function createRuntime(config,ledger){
 const harness=config.harness??'dsh';
 if(!['dsh','pi'].includes(harness))throw Error('Invalid Home harness');
 const runtime=await import(harness==='pi'?'./runtime-pi.mjs':'./runtime-dsh.mjs');
 return runtime.createRuntime(config,ledger);
}
