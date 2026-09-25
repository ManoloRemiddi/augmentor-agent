// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {ExtensionAPI} from '@earendil-works/pi-coding-agent';
import {definitions,homeTool} from './index.js';
export function homePackage(session:string){return (pi:ExtensionAPI)=>{
 for(const d of definitions)pi.registerTool({name:d.name,label:d.name,description:d.description,parameters:d.parameters as any,
  async execute(id,args,signal){const result=await homeTool(d.name,args,session,id,signal);return {content:[{type:'text',text:JSON.stringify(result)}],details:{}};}
 });
};}
