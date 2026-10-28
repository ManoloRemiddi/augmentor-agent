// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
if(process.platform==='linux'&&process.arch==='x64'&&process.env.AUGMENTOR_MANAGED_OFFICE_TEST==='1'){
 delete process.env.AUGMENTOR_HARNESS_PROOF_NATIVE_OFFICE;
 process.env.AUGMENTOR_HARNESS_PROOF_PROCESS_OFFICE='managed';
 await import('./harness-office-chromium.test.mjs');
}else test('MX managed Office original GUI requires an explicit actual user-manager qualification',{skip:true},()=>{});
