// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Mount beside an isolated DSH shell provider; never changes process.env.
export const name='augmentor-preset-environment'
export const inject=['shell']
export function apply(ctx,{environment={}}={}){
 if(!environment||typeof environment!=='object'||Array.isArray(environment)||Object.entries(environment).some(([k,v])=>! /^[A-Z][A-Z0-9_]*$/.test(k)||typeof v!=='string'||k.startsWith('DSH_')))throw Error('Invalid preset shell environment')
 const resolve=ctx.shell.resolve
 ctx.shell.resolve=function(request){const spec=resolve.call(this,request);return {...spec,env:{...spec.env,...environment}}}
 ctx.effect(()=>()=>{ctx.shell.resolve=resolve})
}
