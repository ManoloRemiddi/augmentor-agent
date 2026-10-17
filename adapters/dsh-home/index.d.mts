// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
export const READ_TOOL:string;
export const WRITE_TOOLS:Set<string>;
export function authority(name:string,args:Record<string,unknown>):'read'|'change';
export function homeIntentAcknowledged(value:unknown):boolean;
