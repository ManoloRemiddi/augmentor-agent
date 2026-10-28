// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Reuse the actual original viewer/Host proof with identical assertions/deadlines.
delete process.env.AUGMENTOR_HARNESS_PROOF_NATIVE_OFFICE;
process.env.AUGMENTOR_HARNESS_PROOF_PROCESS_OFFICE='1';
await import('./harness-office-chromium.test.mjs');
