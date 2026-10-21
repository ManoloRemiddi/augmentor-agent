// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Types for the unmodified MIT policy.js distribution; not upstream source.
export type Tier = 'off'|'low'|'medium'|'high';
export interface Classification {tier:Tier;reason:string;family:string;textOnly:boolean}
export const TIERS: Tier[];
export function atLeast(tier:Tier,floor:Tier):Tier;
export function splitRequest(text:string):{instructions:string;hasSource:boolean;ambiguous:boolean};
export function instructionPart(text:string):string;
export function editingGuidance(family:string):string;
export function classify(text:string,options?:{hasMedia?:boolean;previousTier?:Tier}):Classification;
