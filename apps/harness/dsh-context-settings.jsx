// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useSyncExternalStore} from 'react';
import {Button} from '@deepseek-ai/dsh-client-ui-primitives';
import {createContextSettings} from './vendor/dsh-context/src/client/settings.ts';
import {makePluginConfigCard} from './vendor/dsh-context/src/client/components/settingsCard.tsx';
import {makeViewKit} from './vendor/dsh-context/src/client/viewkit.ts';
import {DICT_EN} from './vendor/dsh-context/src/client/i18nEn.ts';
import './vendor/dsh-context/src/client/styles/settings.css';
export const contextSettings=createContextSettings();
const dictionary={...DICT_EN,'settings.promptHint':'Literal text around the system prompt from the next conversational model request. Blank text disables the section. Each field supports up to 64 KiB UTF-8; saved requests keep their own recorded revision.'};
const Card=makePluginConfigCard(makeViewKit(key=>dictionary[key]??key));
const useContextSettings=(selector=x=>x)=>selector(useSyncExternalStore(contextSettings.store.subscribe,contextSettings.store.getSnapshot));
export function DshContextSettingsCard({preferences}){
 const state=useSyncExternalStore(preferences.subscribe,preferences.getSnapshot);
 return <><p className="lc-settings-note">Display defaults apply when the Context view opens. Placement selects the original Context tab, sidebar, or both. Fleet uses the saved parent job catalogue. Prefix and suffix apply literally from the next conversational model request; standalone improvement and summary requests have separate instructions.</p><Card useContextSettings={useContextSettings} set={contextSettings.set} supports={field=>state.writableFields.includes(field)}/>{state.error&&<p role="status">{state.error}</p>}<Button disabled={state.busy||!preferences.current()} onClick={()=>void preferences.load()}>Refresh Context preferences</Button></>;
}
