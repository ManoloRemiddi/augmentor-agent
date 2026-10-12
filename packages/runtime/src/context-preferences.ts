// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Display defaults only. They never alter model input or supplier/agent ownership. */
export const CONTEXT_PREFERENCE_OPTIONS:Record<string,readonly string[]>={
 defaultPlacement:['tab','sidebar','all'],defaultGranularity:['step','turn'],defaultTrendMode:['total','delta'],defaultDeltaBase:['step','turn'],
 defaultToolSort:['size','count','name'],defaultFileSort:['count','latest','path'],insightsEntry:['show','hide'],defaultDurationCurve:['show','hide'],
};
const defaults:Record<string,string>={defaultPlacement:'tab',defaultGranularity:'step',defaultTrendMode:'total',defaultDeltaBase:'step',defaultToolSort:'count',defaultFileSort:'count',insightsEntry:'show',defaultDurationCurve:'show',fleetTab:'hide',promptPrefix:'',promptSuffix:''};
export function contextPreferences(raw:unknown):Record<string,string>{
 const value={...defaults};if(raw&&typeof raw==='object'&&!Array.isArray(raw))for(const [field,options] of Object.entries(CONTEXT_PREFERENCE_OPTIONS)){const choice=(raw as Record<string,unknown>)[field];if(typeof choice==='string'&&options.includes(choice))value[field]=choice;}
 return value;
}
export function contextPreferenceChange(ops:unknown):{field:string;value:string}{
 if(!Array.isArray(ops)||ops.length!==1)throw Error('Choose one Context display preference.');
 const op=ops[0];if(!op||op.op!=='set'||!Array.isArray(op.path)||op.path.length!==1||typeof op.path[0]!=='string'||!Object.hasOwn(CONTEXT_PREFERENCE_OPTIONS,op.path[0])||typeof op.value!=='string'||!CONTEXT_PREFERENCE_OPTIONS[op.path[0]].includes(op.value))throw Error('This Context preference is not supported by the Pi adapter.');
 return {field:op.path[0],value:op.value};
}
