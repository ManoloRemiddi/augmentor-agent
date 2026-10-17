// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
export interface OriginalWikiTool {name:string;description:string;parameters:Record<string,Record<string,unknown>>;execute(args:Record<string,unknown>):Promise<unknown>;output:{render(args:Record<string,unknown>,value:unknown):Array<{type:'text';text:string}>}}
export function createTools(vault:unknown,options?:{maxQueryResults?:number}):OriginalWikiTool[];
