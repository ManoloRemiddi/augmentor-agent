// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Display defaults and explicit literal prompt sections; agent ownership stays with Pi. */
export const CONTEXT_PREFERENCE_OPTIONS:Record<string,readonly string[]>={
 fleetTab:['show','hide'],defaultPlacement:['tab','sidebar','all'],defaultGranularity:['step','turn'],defaultTrendMode:['total','delta'],defaultDeltaBase:['step','turn'],
 defaultToolSort:['size','count','name'],defaultFileSort:['count','latest','path'],insightsEntry:['show','hide'],defaultDurationCurve:['show','hide'],
};
const defaults:Record<string,string>={defaultPlacement:'tab',defaultGranularity:'step',defaultTrendMode:'total',defaultDeltaBase:'step',defaultToolSort:'count',defaultFileSort:'count',insightsEntry:'show',defaultDurationCurve:'show',fleetTab:'hide',promptPrefix:'',promptSuffix:''};
export const CONTEXT_PROMPT_LIMIT=64*1024;
export const CONTEXT_PROMPT_FIELDS=['promptPrefix','promptSuffix'] as const;
export const CONTEXT_PREFERENCE_FIELDS=[...Object.keys(CONTEXT_PREFERENCE_OPTIONS),...CONTEXT_PROMPT_FIELDS];
const promptText=(value:unknown):value is string=>typeof value==='string'&&Buffer.byteLength(value,'utf8')<=CONTEXT_PROMPT_LIMIT;
export function contextPreferences(raw:unknown):Record<string,string>{
 const value={...defaults};if(raw&&typeof raw==='object'&&!Array.isArray(raw))for(const [field,options] of Object.entries(CONTEXT_PREFERENCE_OPTIONS)){const choice=(raw as Record<string,unknown>)[field];if(typeof choice==='string'&&options.includes(choice))value[field]=choice;}
 if(raw&&typeof raw==='object'&&!Array.isArray(raw))for(const field of CONTEXT_PROMPT_FIELDS){const text=(raw as Record<string,unknown>)[field];if(promptText(text))value[field]=text;}
 return value;
}
export function contextPreferenceChange(ops:unknown):{field:string;value:string}{
 if(!Array.isArray(ops)||ops.length!==1)throw Error('Choose one Context preference.');
 const op=ops[0];if(!op||op.op!=='set'||!Array.isArray(op.path)||op.path.length!==1||typeof op.path[0]!=='string'||typeof op.value!=='string')throw Error('This Context preference is not supported by the Pi adapter.');
 if((CONTEXT_PROMPT_FIELDS as readonly string[]).includes(op.path[0])){if(!promptText(op.value))throw Error('Context prompt text exceeds 64 KiB UTF-8.');}
 else if(!Object.hasOwn(CONTEXT_PREFERENCE_OPTIONS,op.path[0])||!CONTEXT_PREFERENCE_OPTIONS[op.path[0]].includes(op.value))throw Error('This Context preference is not supported by the Pi adapter.');
 return {field:op.path[0],value:op.value};
}
