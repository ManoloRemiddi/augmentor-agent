// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useEffect,useMemo,useSyncExternalStore} from 'react';
import {Button} from '@deepseek-ai/dsh-client-ui-primitives';
import {DeveloperToolsRow} from '@dsh-gui/ui-settings-general/src/client/DeveloperToolsRow.tsx';
import {WebSearchFreeCard} from './vendor/dsh-web-search-free/client.tsx';
import {DshSearchScope} from './dsh-search-scope.mjs';
/** Original supplier card and DSH enable row; private Pi settings are the seam. */
export function SearchSettings({controller}){
 const scope=useMemo(()=>new DshSearchScope(controller),[controller]);useEffect(()=>()=>scope.close(),[scope]);const s=useSyncExternalStore(scope.subscribe,scope.getSnapshot);
 const t=key=>({'developerTools.title':'Free Search tools','developerTools.description':'Original API-engine search and fetch for Native conversations. Configure keys in the card below. Historical keyless search is still being integrated.','developerTools.error':'Search settings could not be confirmed.'}[key]??key);
 return <div aria-label="Free Search settings"><DeveloperToolsRow t={t} useDeveloperTools={select=>select(s.accepted?.enabled??false)} setEnabled={enabled=>scope.enable(enabled)} disabled={!s.writable||s.busy}/>
 <WebSearchFreeCard scope={scope} legacyMigration={false}/>
 {s.error&&<p role="alert">{s.error}</p>}{s.accepted&&<p role="status">{s.accepted.pending?'Stored Search settings awaiting application.':s.accepted.enabled?'Free Search enabled.':'Free Search disabled.'} Applied to {s.accepted.appliedSessions} of {s.accepted.loadedSessions} loaded Native conversations.</p>}
 <Button disabled={!scope.current()||s.busy} onClick={()=>void scope.load()}>Refresh Search settings</Button>{s.accepted?.pending&&<Button disabled={!scope.current()||s.busy} onClick={()=>void scope.load(true)}>Apply stored Search settings</Button>}</div>;
}
