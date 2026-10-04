// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Loaded only by explicit disposable Node qualification, never product startup.
import {writeFileSync} from 'node:fs'
process.once('beforeExit',()=>writeFileSync(process.env.AUGMENTOR_TEST_EXIT_OBSERVER,String(process.pid)))
