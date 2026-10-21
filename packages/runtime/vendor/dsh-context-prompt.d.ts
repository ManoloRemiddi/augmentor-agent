// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Typed seat for the separately transpiled, verbatim Apache-2.0 public module.
export interface PromptSection {name:string;order:number;text:string|((context:unknown)=>string);interpolate?:boolean}
export interface PromptRegistry {section(section:PromptSection):()=>void;getSectionOrder(name:string):number}
export function watchPromptInjection(ctx:{inject(dependencies:readonly string[],callback:(inner:{systemPrompt:PromptRegistry})=>void):void},config:{promptPrefix:{get():string};promptSuffix:{get():string}}):void;
