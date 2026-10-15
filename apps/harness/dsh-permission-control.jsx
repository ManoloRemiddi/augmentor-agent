// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React from 'react';
import {PermissionSelect} from '@dsh-gui/ui-permission-presets/src/client/PermissionSelect.tsx';
import {accessEn} from '@dsh-gui/ui-permission-presets/src/client/locales.ts';
import {Button} from '@deepseek-ai/dsh-client-ui-primitives';
export const permissionT=(key,args={})=>String(accessEn[key]??key).replace(/\{(\w+)\}/g,(_,k)=>String(args[k]??''));
export function CurrentPermissionControl({state,controller,locked}){
 if(!state.sessionId||!state.capabilities?.sessionPermissions)return null;
 const value=state.permission,scope={sessionId:state.sessionId,epoch:controller.epoch,revision:value?.revision};
 if(!value)return state.permissionError?<Button variant="ghost" disabled={locked||state.permissionBusy} title={state.permissionError} onClick={()=>void controller.refreshPermission(scope,{explicit:true})}>Refresh permission mode</Button>:null;
 return <PermissionSelect key={[scope.sessionId,scope.epoch,scope.revision,state.readOnly,state.permissionBusy].join(':')} locked={locked||state.readOnly||!value.canSelect||state.permissionBusy} useProjection={()=>({currentValue:value.currentValue})} usePermissionCatalog={selector=>selector({value:{options:value.options}})} select={preset=>controller.selectPermission(preset,scope).then(result=>result.accepted===true).catch(()=>false)} t={permissionT}/>;
}
