// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Disposable proof only. Node's forced process.exit path skips beforeExit.
import {writeFileSync} from 'node:fs'
export function apply(ctx,{path}){
 ctx.effect(()=>()=>{
  process.once('beforeExit',()=>{
   try{writeFileSync(path,JSON.stringify({pid:process.pid,exitCode:process.exitCode??0}),{flag:'wx',mode:0o600})}
   catch(error){if(error.code!=='EEXIST')throw error}
  })
 },'fixture: observe natural shutdown')
}
