// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const presets=['read-only','workspace-write','danger-full-access'];
export function checkedSessionPermission(value){
 if(value?.available!==true||typeof value.canSelect!=='boolean'||!presets.includes(value.currentValue)||typeof value.revision!=='string'||!(value.revision==='initial'||/^[a-f0-9-]{36}$/.test(value.revision))||!Array.isArray(value.options)||value.options.length!==3||new Set(value.options.map(x=>x?.value)).size!==3||value.options.some(x=>!presets.includes(x?.value)||typeof x.name!=='string'||!x.name.length||x.name.length>100||typeof x.description!=='string'||x.description.length>1000))throw Error('The current permission mode is unavailable.');
 return structuredClone(value);
}
export function permissionMenuOptions(view,t){return view.options.map(row=>({id:row.value,value:row.value,label:row.name,detail:row.description,active:row.value===view.currentValue,...(row.value==='danger-full-access'?{confirmation:{title:t('confirm.title'),description:t('confirm.description'),acknowledgeLabel:t('confirm.acknowledge'),cancelLabel:t('confirm.cancel'),confirmLabel:t('confirm.enable')}}:{})}));}
