// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useSyncExternalStore} from 'react';
import {Button} from '@deepseek-ai/dsh-client-ui-primitives';
import {createContextSettings} from './vendor/dsh-context/src/client/settings.ts';
import {makePluginConfigCard} from './vendor/dsh-context/src/client/components/settingsCard.tsx';
import {makeViewKit} from './vendor/dsh-context/src/client/viewkit.ts';
import {DICT_EN} from './vendor/dsh-context/src/client/i18nEn.ts';
import './vendor/dsh-context/src/client/styles/settings.css';
export const contextSettings=createContextSettings();
contextSettings.fleetTab=()=> 'hide';
const dictionary={...DICT_EN,'settings.promptHint':'Prompt wrapping is not connected to Pi; these fields cannot alter model input.'};
const Card=makePluginConfigCard(makeViewKit(key=>dictionary[key]??key));
const useContextSettings=(selector=x=>x)=>selector(useSyncExternalStore(contextSettings.store.subscribe,contextSettings.store.getSnapshot));
export function DshContextSettingsCard({preferences}){
 const state=useSyncExternalStore(preferences.subscribe,preferences.getSnapshot);
 return <><p className="lc-settings-note">Display defaults apply when the Context view opens. Placement selects the original Context tab, sidebar, or both. Fleet and prompt wrapping are not connected to Pi.</p><Card useContextSettings={useContextSettings} set={contextSettings.set} supports={field=>state.writableFields.includes(field)}/>{state.error&&<p role="status">{state.error}</p>}<Button disabled={state.busy||!preferences.current()} onClick={()=>void preferences.load()}>Refresh Context preferences</Button></>;
}
