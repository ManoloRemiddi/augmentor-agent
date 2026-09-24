// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Optional deployment-provided discovery snapshot; never grants device authority.
import {readFileSync,statSync} from 'node:fs';
import {join} from 'node:path';
export function readDiscovery(stateDir){
 if(!stateDir)return {devices:[],scanned_at:null};
 const file=join(stateDir,'discovered-devices.json');
 try{
  if(statSync(file).size>131072)throw Error('Discovery inventory too large');
  const data=JSON.parse(readFileSync(file,'utf8'));
  if(!Array.isArray(data.devices)||data.devices.length>128||!Number.isFinite(Date.parse(data.scanned_at)))throw Error('Invalid discovery inventory');
  const field=(value,max)=>typeof value==='string'?value.slice(0,max):'';
  return {scanned_at:data.scanned_at,devices:data.devices.map(d=>({name:field(d.name,200)||'Unidentified device',model:field(d.model,100),host:field(d.host,100),status:d.status==='unsupported'?'unsupported':'needs_setup'}))};
 }catch(error){if(error.code==='ENOENT')return {devices:[],scanned_at:null};throw error;}
}
