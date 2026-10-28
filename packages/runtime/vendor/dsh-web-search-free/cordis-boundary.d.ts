// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Type-only shape for the copied provider registration; no Cordis runtime/owner.
declare module '@deepseek-ai/cordis' { interface Context { [key:string]:any; inject(services:string[],callback:(context:Context)=>unknown):unknown } }
