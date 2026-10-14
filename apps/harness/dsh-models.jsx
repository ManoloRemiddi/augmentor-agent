// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useEffect,useMemo,useSyncExternalStore} from 'react';
import {ModelsSection} from '@dsh-gui/ui-settings-models/src/client/ModelsSection.tsx';
import {en} from '@dsh-gui/ui-settings-models/src/client/locales.ts';
import {Button} from '@deepseek-ai/dsh-client-ui-primitives';
import {DshModelScope,modelSchema} from './dsh-model-scope.mjs';
import {DshModelAccounts} from './dsh-model-accounts.jsx';
const copy={...en,intro:'Configure Pi providers and model catalogs. API keys are write-only; existing provider details are preserved.',contextWindowPlaceholder:'Uses the effective Pi model default',maxTokensPlaceholder:'Uses the effective Pi model default',modelsEmpty:'This custom catalog has no models. Add model IDs to make them available.',keyEnvLocked:'Command, environment expression or OAuth account (manage through Pi)',advancedHint:'Other provider and model fields remain in the private Pi models.json profile.',deleteDescription:'Deleting {provider} removes its model profile and any API key in that profile. Stored Pi account credentials are kept.',readOnly:'Connect with operator access to edit model settings.'};
const t=key=>copy[key]??key;
export function OriginalModels({controller,children}){
 const scope=useMemo(()=>new DshModelScope(controller),[controller]);
 useEffect(()=>()=>scope.close(),[scope]);
 const useSnapshot=selector=>selector(useSyncExternalStore(scope.subscribe,scope.getSnapshot));
 return <><ModelsSection controller={scope} useSnapshot={useSnapshot} operations={scope.operations} schema={modelSchema} t={t} renderSlot={(name,owner,options={})=>options.fallback??null}/><DshModelAccounts scope={scope}/><div className="augmentor-extension"><Button disabled={!scope.current()} onClick={()=>void scope.refresh()}>Refresh model settings</Button>{children}</div></>;
}
